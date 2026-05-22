from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from backend.app.db.models.game import Game
from backend.app.db.models.user import User
from backend.app.db.models.user_game import UserGame
from backend.app.db.models.enums import GameType


def _apply_game_filters(
    stmt: Select[tuple[Game]],
    *,
    title: str | None,
    owner_id: int | None,
    players_count: int | None,
    max_play_time_minutes: int | None,
    game_type: GameType | None,
    has_campaign: bool | None,
    available_only: bool | None,
) -> Select[tuple[Game]]:
    needs_user_games_join = owner_id is not None or available_only is True

    if needs_user_games_join:
        stmt = stmt.join(UserGame, UserGame.game_id == Game.id)

    if title:
        stmt = stmt.where(Game.title.ilike(f"%{title.strip()}%"))

    if owner_id is not None:
        stmt = stmt.where(UserGame.user_id == owner_id)

    if players_count is not None:
        stmt = stmt.where(Game.min_players <= players_count, Game.max_players >= players_count)

    if max_play_time_minutes is not None:
        stmt = stmt.where(Game.play_time_minutes.is_not(None))
        stmt = stmt.where(Game.play_time_minutes <= max_play_time_minutes)

    if game_type is not None:
        stmt = stmt.where(Game.game_type == game_type)

    if has_campaign is not None:
        stmt = stmt.where(Game.has_campaign.is_(has_campaign))

    if available_only is True:
        stmt = stmt.where(UserGame.is_available_for_meetups.is_(True))

    return stmt


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
) -> list[Game]:
    stmt = select(Game)
    stmt = _apply_game_filters(
        stmt,
        title=title,
        owner_id=owner_id,
        players_count=players_count,
        max_play_time_minutes=max_play_time_minutes,
        game_type=game_type,
        has_campaign=has_campaign,
        available_only=available_only,
    )
    stmt = stmt.order_by(Game.title.asc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).unique())


def get_game_by_id(db: Session, game_id: int) -> Game | None:
    return db.get(Game, game_id)


def get_game_by_bgg_id(db: Session, bgg_id: int) -> Game | None:
    stmt = select(Game).where(Game.bgg_id == bgg_id)
    return db.scalar(stmt)


def list_game_owners(db: Session, game_id: int) -> list[dict]:
    stmt = (
        select(
            User.id.label("user_id"),
            User.display_name,
            User.username,
            User.bgg_username,
            UserGame.is_available_for_meetups,
            UserGame.comment,
        )
        .join(UserGame, UserGame.user_id == User.id)
        .where(UserGame.game_id == game_id)
        .order_by(User.display_name.asc())
    )
    return [dict(row._mapping) for row in db.execute(stmt)]
