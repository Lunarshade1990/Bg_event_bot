from dataclasses import dataclass

from boardgamegeek.api import BGGRestrictCollectionTo
from boardgamegeek.exceptions import BGGApiError, BGGError
from sqlalchemy.orm import Session

from backend.app.clients.bgg import get_bgg_client, iter_owned_collection_items
from backend.app.db.models.enums import CampaignSource, GameType, ImportJobStatus, OwnershipSource
from backend.app.db.models.game import Game
from backend.app.db.repositories import games as game_repository
from backend.app.db.repositories import imports as import_repository
from backend.app.db.repositories import users as user_repository
from backend.app.schemas.import_job import BggCollectionImportResult


class BggImportError(RuntimeError):
    """Raised when collection import cannot be completed."""


@dataclass
class ImportCounters:
    processed_games: int = 0
    created_games: int = 0
    updated_games: int = 0
    linked_games: int = 0


def _normalize_game_type(subtype: str) -> GameType:
    if subtype == BGGRestrictCollectionTo.BOARD_GAME_EXTENSION:
        return GameType.EXPANSION
    return GameType.BASE


def _extract_has_campaign(game_details) -> tuple[bool, CampaignSource]:
    mechanics = getattr(game_details, "mechanics", []) or []
    return "Campaign Game" in mechanics, CampaignSource.BGG


def _extract_expands_bgg_ids(game_details) -> list[int]:
    expands = getattr(game_details, "expands", []) or []
    expand_ids: list[int] = []

    for expanded_game in expands:
        expanded_game_id = getattr(expanded_game, "id", None)
        if expanded_game_id is None:
            continue
        expand_ids.append(int(expanded_game_id))

    return list(dict.fromkeys(expand_ids))


def _upsert_game_from_bgg(
    db: Session,
    *,
    subtype: str,
    collection_item,
    game_details,
) -> tuple[Game, bool, bool]:
    game = game_repository.get_game_by_bgg_id(db, collection_item.id)
    created = False
    updated = False

    title = getattr(game_details, "name", None) or getattr(collection_item, "name", None)
    if not title:
        raise BggImportError(f"BGG game {collection_item.id} does not have a title.")

    min_players = getattr(game_details, "min_players", None) or 1
    max_players = getattr(game_details, "max_players", None) or min_players
    play_time = (
        getattr(game_details, "playing_time", None)
        or getattr(game_details, "max_playing_time", None)
        or getattr(game_details, "min_playing_time", None)
    )
    image_url = getattr(game_details, "image", None) or getattr(game_details, "thumbnail", None)
    designers = getattr(game_details, "designers", []) or []
    author = ", ".join(designers) if designers else None
    has_campaign, campaign_source = _extract_has_campaign(game_details)
    expands_bgg_ids = _extract_expands_bgg_ids(game_details)
    mechanics = list(getattr(game_details, "mechanics", []) or [])
    normalized_type = _normalize_game_type(subtype)

    if game is None:
        game = Game(
            bgg_id=collection_item.id,
            title=title,
            original_title=title,
            author=author,
            min_players=min_players,
            max_players=max_players,
            play_time_minutes=play_time,
            image_url=image_url,
            game_type=normalized_type,
            has_campaign=has_campaign,
            campaign_source=campaign_source,
            bgg_expands_ids_cached=expands_bgg_ids,
            bgg_raw_mechanics_cached=mechanics,
        )
        db.add(game)
        db.flush()
        return game, True, False

    changes = {
        "title": title,
        "original_title": title,
        "author": author,
        "min_players": min_players,
        "max_players": max_players,
        "play_time_minutes": play_time,
        "image_url": image_url,
        "game_type": normalized_type,
        "bgg_expands_ids_cached": expands_bgg_ids,
        "bgg_raw_mechanics_cached": mechanics,
    }

    for field_name, value in changes.items():
        if getattr(game, field_name) != value:
            setattr(game, field_name, value)
            updated = True

    if game.campaign_source != CampaignSource.ADMIN_MANUAL:
        if game.has_campaign != has_campaign:
            game.has_campaign = has_campaign
            updated = True
        if game.campaign_source != campaign_source:
            game.campaign_source = campaign_source
            updated = True

    if updated:
        db.flush()

    return game, created, updated


def import_bgg_collection(
    db: Session,
    *,
    telegram_id: int,
    bgg_username: str | None = None,
) -> BggCollectionImportResult:
    user = user_repository.get_user_by_telegram_id(db, telegram_id)
    if user is None:
        raise BggImportError("User is not registered in the application yet.")

    resolved_bgg_username = (bgg_username or user.bgg_username or "").strip()
    if not resolved_bgg_username:
        raise BggImportError("BGG username is required for import.")

    #TODO Request user confirmation
    # existing = user_repository.get_user_by_bgg_username(db, resolved_bgg_username)
    # if existing is not None and existing.id != user.id:
    #     raise BggImportError("This BGG username is already linked to another user.")

    if user.bgg_username != resolved_bgg_username:
        import_repository.update_user_bgg_username(
            db,
            user=user,
            bgg_username=resolved_bgg_username,
        )

    job = import_repository.create_import_job(
        db,
        user_id=user.id,
        bgg_username=resolved_bgg_username,
    )
    import_repository.mark_import_job_in_progress(db, job)
    db.commit()
    db.refresh(job)

    counters = ImportCounters()
    client = get_bgg_client()
    synced_game_ids: set[int] = set()

    try:
        for subtype, item in iter_owned_collection_items(
            client,
            bgg_username=resolved_bgg_username,
        ):
            details = client.game(game_id=item.id)
            game, created, updated = _upsert_game_from_bgg(
                db,
                subtype=subtype,
                collection_item=item,
                game_details=details,
            )
            counters.processed_games += 1
            counters.created_games += int(created)
            counters.updated_games += int(updated)
            synced_game_ids.add(game.id)

            user_game = import_repository.get_user_game(db, user_id=user.id, game_id=game.id)
            if user_game is None:
                import_repository.create_user_game(
                    db,
                    user_id=user.id,
                    game_id=game.id,
                    source=OwnershipSource.BGG_IMPORT,
                )
                counters.linked_games += 1

        import_repository.delete_missing_bgg_import_user_games(
            db,
            user_id=user.id,
            present_game_ids=synced_game_ids,
        )
        collection_games_count = import_repository.count_user_games(db, user_id=user.id)

        import_repository.mark_import_job_completed(
            db,
            job,
            imported_count=counters.processed_games,
        )
        db.commit()
        db.refresh(job)
    except (BGGApiError, BGGError, BggImportError) as exc:
        db.rollback()
        job = db.get(type(job), job.id)
        if job is not None:
            import_repository.mark_import_job_failed(db, job, error_message=str(exc))
            db.commit()
        raise BggImportError(str(exc)) from exc

    return BggCollectionImportResult(
        job_id=job.id,
        user_id=user.id,
        bgg_username=resolved_bgg_username,
        status=ImportJobStatus.COMPLETED,
        collection_games_count=collection_games_count,
        processed_games=counters.processed_games,
        created_games=counters.created_games,
        updated_games=counters.updated_games,
        linked_games=counters.linked_games,
    )
