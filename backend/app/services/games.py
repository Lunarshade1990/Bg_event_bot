from sqlalchemy.orm import Session

from backend.app.db.models.enums import GameType
from backend.app.db.repositories import games as game_repository


def list_games(
    db: Session,
    *,
    title: str | None = None,
    owner_id: int | None = None,
    players_count: int | None = None,
    max_play_time_minutes: int | None = None,
    game_type: GameType | None = None,
    has_campaign: bool | None = None,
    available_only: bool | None = None,
    limit: int = 20,
    offset: int = 0,
):
    return game_repository.list_games(
        db,
        title=title,
        owner_id=owner_id,
        players_count=players_count,
        max_play_time_minutes=max_play_time_minutes,
        game_type=game_type,
        has_campaign=has_campaign,
        available_only=available_only,
        limit=limit,
        offset=offset,
    )


def get_game(db: Session, game_id: int):
    return game_repository.get_game_by_id(db, game_id)


def get_game_owners(db: Session, game_id: int) -> list[dict]:
    return game_repository.list_game_owners(db, game_id)
