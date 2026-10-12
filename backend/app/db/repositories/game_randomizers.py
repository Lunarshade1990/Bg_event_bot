from sqlalchemy import desc, exists, func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.db.models.enums import GameType
from backend.app.db.models.game import Game
from backend.app.db.models.game_randomizer_category import GameRandomizerCategory
from backend.app.db.models.game_randomizer_option import GameRandomizerOption
from backend.app.db.models.user import User
from backend.app.db.models.user_game import UserGame


def list_randomizer_games(
    db: Session,
    *,
    bgg_username: str,
    title: str | None,
    limit: int,
    offset: int,
) -> list[Game]:
    profile_owns_game = exists(
        select(UserGame.id)
        .join(User, User.id == UserGame.user_id)
        .where(
            UserGame.game_id == Game.id,
            func.lower(func.trim(User.bgg_username)) == bgg_username,
        )
    )
    stmt = (
        select(Game)
        .where(Game.game_type == GameType.BASE)
        .order_by(desc(profile_owns_game), Game.title.asc())
    )
    if title:
        stmt = stmt.where(Game.title.ilike(f"%{title.strip()}%"))
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def get_categories(
    db: Session,
    *,
    bgg_username: str,
    game_id: int,
) -> list[GameRandomizerCategory]:
    stmt = (
        select(GameRandomizerCategory)
        .options(selectinload(GameRandomizerCategory.options))
        .where(
            GameRandomizerCategory.bgg_username == bgg_username,
            GameRandomizerCategory.game_id == game_id,
        )
        .order_by(GameRandomizerCategory.id.asc())
    )
    return list(db.scalars(stmt).all())


def get_category(
    db: Session,
    *,
    bgg_username: str,
    game_id: int,
    category_id: int,
) -> GameRandomizerCategory | None:
    stmt = (
        select(GameRandomizerCategory)
        .options(selectinload(GameRandomizerCategory.options))
        .where(
            GameRandomizerCategory.id == category_id,
            GameRandomizerCategory.bgg_username == bgg_username,
            GameRandomizerCategory.game_id == game_id,
        )
    )
    return db.scalar(stmt)


def get_option(
    db: Session,
    *,
    category_id: int,
    option_id: int,
) -> GameRandomizerOption | None:
    stmt = select(GameRandomizerOption).where(
        GameRandomizerOption.id == option_id,
        GameRandomizerOption.category_id == category_id,
    )
    return db.scalar(stmt)


def get_category_by_name(
    db: Session,
    *,
    bgg_username: str,
    game_id: int,
    name: str,
) -> GameRandomizerCategory | None:
    stmt = select(GameRandomizerCategory).where(
        GameRandomizerCategory.bgg_username == bgg_username,
        GameRandomizerCategory.game_id == game_id,
        func.lower(GameRandomizerCategory.name) == name.lower(),
    )
    return db.scalar(stmt)


def get_game(db: Session, game_id: int) -> Game | None:
    return db.get(Game, game_id)
