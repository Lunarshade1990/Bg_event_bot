import random

from sqlalchemy.orm import Session

from backend.app.db.models.game import Game
from backend.app.db.models.game_randomizer_category import GameRandomizerCategory
from backend.app.db.models.game_randomizer_option import GameRandomizerOption
from backend.app.db.repositories import game_randomizers as randomizer_repository
from backend.app.db.repositories import users as user_repository
from backend.app.schemas.game_randomizer import GameRandomizerDrawCategory


class RandomizerUserNotFoundError(Exception):
    pass


class RandomizerBggUsernameRequiredError(Exception):
    pass


class RandomizerGameNotFoundError(Exception):
    pass


class RandomizerCategoryNotFoundError(Exception):
    pass


class RandomizerCategoryConflictError(Exception):
    pass


class RandomizerInvalidDrawError(Exception):
    pass


def _resolve_bgg_username(db: Session, telegram_id: int) -> str:
    user = user_repository.get_user_by_telegram_id(db, telegram_id)
    if user is None:
        raise RandomizerUserNotFoundError("User not found.")
    bgg_username = (user.bgg_username or "").strip().lower()
    if not bgg_username:
        raise RandomizerBggUsernameRequiredError("Set a BGG username in your profile first.")
    return bgg_username


def list_games(
    db: Session,
    *,
    telegram_id: int,
    title: str | None,
    limit: int,
    offset: int,
) -> list[Game]:
    bgg_username = _resolve_bgg_username(db, telegram_id)
    return randomizer_repository.list_randomizer_games(
        db,
        bgg_username=bgg_username,
        title=title,
        limit=limit,
        offset=offset,
    )


def get_randomizer(
    db: Session,
    *,
    telegram_id: int,
    game_id: int,
) -> tuple[Game, list[GameRandomizerCategory]]:
    bgg_username = _resolve_bgg_username(db, telegram_id)
    game = randomizer_repository.get_game(db, game_id)
    if game is None:
        raise RandomizerGameNotFoundError("Game not found.")
    return game, randomizer_repository.get_categories(
        db,
        bgg_username=bgg_username,
        game_id=game_id,
    )


def create_category(
    db: Session,
    *,
    telegram_id: int,
    game_id: int,
    name: str,
    draw_count: int | None,
) -> GameRandomizerCategory:
    bgg_username = _resolve_bgg_username(db, telegram_id)
    _require_game(db, game_id)
    if randomizer_repository.get_category_by_name(
        db,
        bgg_username=bgg_username,
        game_id=game_id,
        name=name,
    ):
        raise RandomizerCategoryConflictError("A field with this name already exists.")
    category = GameRandomizerCategory(
        bgg_username=bgg_username,
        game_id=game_id,
        name=name,
        draw_count=draw_count,
    )
    db.add(category)
    db.commit()
    return _get_category(db, bgg_username, game_id, category.id)


def update_category(
    db: Session,
    *,
    telegram_id: int,
    game_id: int,
    category_id: int,
    name: str | None,
    update_draw_count: bool,
    draw_count: int | None,
) -> GameRandomizerCategory:
    bgg_username = _resolve_bgg_username(db, telegram_id)
    category = _get_category(db, bgg_username, game_id, category_id)
    if name is not None and name.lower() != category.name.lower():
        if randomizer_repository.get_category_by_name(
            db,
            bgg_username=bgg_username,
            game_id=game_id,
            name=name,
        ):
            raise RandomizerCategoryConflictError("A field with this name already exists.")
        category.name = name
    if update_draw_count:
        category.draw_count = draw_count
    db.commit()
    return _get_category(db, bgg_username, game_id, category_id)


def delete_category(
    db: Session,
    *,
    telegram_id: int,
    game_id: int,
    category_id: int,
) -> None:
    bgg_username = _resolve_bgg_username(db, telegram_id)
    category = _get_category(db, bgg_username, game_id, category_id)
    db.delete(category)
    db.commit()


def add_options(
    db: Session,
    *,
    telegram_id: int,
    game_id: int,
    category_id: int,
    values: list[str],
) -> GameRandomizerCategory:
    bgg_username = _resolve_bgg_username(db, telegram_id)
    category = _get_category(db, bgg_username, game_id, category_id)
    category.options.extend(GameRandomizerOption(value=value) for value in values)
    db.commit()
    return _get_category(db, bgg_username, game_id, category_id)


def update_option(
    db: Session,
    *,
    telegram_id: int,
    game_id: int,
    category_id: int,
    option_id: int,
    value: str,
) -> GameRandomizerCategory:
    bgg_username = _resolve_bgg_username(db, telegram_id)
    _get_category(db, bgg_username, game_id, category_id)
    option = randomizer_repository.get_option(
        db,
        category_id=category_id,
        option_id=option_id,
    )
    if option is None:
        raise RandomizerCategoryNotFoundError("Option not found.")
    option.value = value
    db.commit()
    return _get_category(db, bgg_username, game_id, category_id)


def delete_option(
    db: Session,
    *,
    telegram_id: int,
    game_id: int,
    category_id: int,
    option_id: int,
) -> GameRandomizerCategory:
    bgg_username = _resolve_bgg_username(db, telegram_id)
    _get_category(db, bgg_username, game_id, category_id)
    option = randomizer_repository.get_option(
        db,
        category_id=category_id,
        option_id=option_id,
    )
    if option is None:
        raise RandomizerCategoryNotFoundError("Option not found.")
    db.delete(option)
    db.commit()
    return _get_category(db, bgg_username, game_id, category_id)


def draw(
    db: Session,
    *,
    telegram_id: int,
    game_id: int,
    category_ids: list[int],
    player_count: int | None,
) -> tuple[Game, list[GameRandomizerDrawCategory]]:
    bgg_username = _resolve_bgg_username(db, telegram_id)
    game = randomizer_repository.get_game(db, game_id)
    if game is None:
        raise RandomizerGameNotFoundError("Game not found.")
    if len(set(category_ids)) != len(category_ids):
        raise RandomizerInvalidDrawError("Duplicate categories are not allowed.")

    categories = randomizer_repository.get_categories(
        db,
        bgg_username=bgg_username,
        game_id=game_id,
    )
    categories_by_id = {category.id: category for category in categories}
    if any(category_id not in categories_by_id for category_id in category_ids):
        raise RandomizerCategoryNotFoundError("One or more fields do not belong to this game.")

    results: list[GameRandomizerDrawCategory] = []
    for category_id in category_ids:
        category = categories_by_id[category_id]
        if category.draw_count is None and player_count is None:
            raise RandomizerInvalidDrawError(
                f"Player count is required for the “{category.name}” field."
            )
        requested_count = category.draw_count or player_count
        if requested_count is None:
            raise RandomizerInvalidDrawError("Could not determine the draw count.")
        options = category.options
        available_count = len(options)
        shortage = max(requested_count - available_count, 0)
        selected = (
            [option.value for option in random.sample(options, requested_count)]
            if shortage == 0
            else []
        )
        results.append(
            GameRandomizerDrawCategory(
                category_id=category.id,
                category_name=category.name,
                requested_count=requested_count,
                available_count=available_count,
                selected=selected,
                shortage=shortage,
            )
        )
    return game, results


def _require_game(db: Session, game_id: int) -> Game:
    game = randomizer_repository.get_game(db, game_id)
    if game is None:
        raise RandomizerGameNotFoundError("Game not found.")
    return game


def _get_category(
    db: Session,
    bgg_username: str,
    game_id: int,
    category_id: int,
) -> GameRandomizerCategory:
    category = randomizer_repository.get_category(
        db,
        bgg_username=bgg_username,
        game_id=game_id,
        category_id=category_id,
    )
    if category is None:
        raise RandomizerCategoryNotFoundError("Field not found.")
    return category
