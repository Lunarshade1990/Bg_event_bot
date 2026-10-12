from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.dependencies.db import get_db
from backend.app.schemas.game import GameRead
from backend.app.schemas.game_randomizer import (
    GameRandomizerCategoryCreate,
    GameRandomizerCategoryRead,
    GameRandomizerCategoryUpdate,
    GameRandomizerDrawRead,
    GameRandomizerDrawRequest,
    GameRandomizerGameRead,
    GameRandomizerOptionsCreate,
    GameRandomizerOptionUpdate,
)
from backend.app.services import game_randomizers as randomizer_service

router = APIRouter(prefix="/randomizers", tags=["randomizers"])


def _raise_randomizer_error(exc: Exception) -> None:
    if isinstance(exc, randomizer_service.RandomizerUserNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, randomizer_service.RandomizerBggUsernameRequiredError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if isinstance(exc, randomizer_service.RandomizerGameNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, randomizer_service.RandomizerCategoryNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, randomizer_service.RandomizerCategoryConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, randomizer_service.RandomizerInvalidDrawError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("/games", response_model=list[GameRead])
def list_randomizer_games(
    db: Annotated[Session, Depends(get_db)],
    telegram_id: int = Query(..., ge=1),
    title: str | None = Query(default=None, max_length=500),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[GameRead]:
    try:
        games = randomizer_service.list_games(
            db,
            telegram_id=telegram_id,
            title=title,
            limit=limit,
            offset=offset,
        )
    except (
        randomizer_service.RandomizerUserNotFoundError,
        randomizer_service.RandomizerBggUsernameRequiredError,
    ) as exc:
        _raise_randomizer_error(exc)
    return [GameRead.model_validate(game) for game in games]


@router.get("/{game_id}", response_model=GameRandomizerGameRead)
def get_randomizer(
    game_id: int,
    db: Annotated[Session, Depends(get_db)],
    telegram_id: int = Query(..., ge=1),
) -> GameRandomizerGameRead:
    try:
        game, categories = randomizer_service.get_randomizer(
            db,
            telegram_id=telegram_id,
            game_id=game_id,
        )
    except (
        randomizer_service.RandomizerUserNotFoundError,
        randomizer_service.RandomizerBggUsernameRequiredError,
        randomizer_service.RandomizerGameNotFoundError,
    ) as exc:
        _raise_randomizer_error(exc)
    return GameRandomizerGameRead(
        game=GameRead.model_validate(game),
        categories=[GameRandomizerCategoryRead.model_validate(item) for item in categories],
    )


@router.post(
    "/{game_id}/categories",
    response_model=GameRandomizerCategoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    game_id: int,
    payload: GameRandomizerCategoryCreate,
    db: Annotated[Session, Depends(get_db)],
    telegram_id: int = Query(..., ge=1),
) -> GameRandomizerCategoryRead:
    try:
        category = randomizer_service.create_category(
            db,
            telegram_id=telegram_id,
            game_id=game_id,
            name=payload.name,
            draw_count=payload.draw_count,
        )
    except (
        randomizer_service.RandomizerUserNotFoundError,
        randomizer_service.RandomizerBggUsernameRequiredError,
        randomizer_service.RandomizerGameNotFoundError,
        randomizer_service.RandomizerCategoryConflictError,
    ) as exc:
        _raise_randomizer_error(exc)
    return GameRandomizerCategoryRead.model_validate(category)


@router.patch(
    "/{game_id}/categories/{category_id}",
    response_model=GameRandomizerCategoryRead,
)
def update_category(
    game_id: int,
    category_id: int,
    payload: GameRandomizerCategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    telegram_id: int = Query(..., ge=1),
) -> GameRandomizerCategoryRead:
    try:
        category = randomizer_service.update_category(
            db,
            telegram_id=telegram_id,
            game_id=game_id,
            category_id=category_id,
            name=payload.name,
            update_draw_count=payload.update_draw_count,
            draw_count=payload.draw_count,
        )
    except (
        randomizer_service.RandomizerUserNotFoundError,
        randomizer_service.RandomizerBggUsernameRequiredError,
        randomizer_service.RandomizerCategoryNotFoundError,
        randomizer_service.RandomizerCategoryConflictError,
    ) as exc:
        _raise_randomizer_error(exc)
    return GameRandomizerCategoryRead.model_validate(category)


@router.delete(
    "/{game_id}/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_category(
    game_id: int,
    category_id: int,
    db: Annotated[Session, Depends(get_db)],
    telegram_id: int = Query(..., ge=1),
) -> Response:
    try:
        randomizer_service.delete_category(
            db,
            telegram_id=telegram_id,
            game_id=game_id,
            category_id=category_id,
        )
    except (
        randomizer_service.RandomizerUserNotFoundError,
        randomizer_service.RandomizerBggUsernameRequiredError,
        randomizer_service.RandomizerCategoryNotFoundError,
    ) as exc:
        _raise_randomizer_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{game_id}/categories/{category_id}/options",
    response_model=GameRandomizerCategoryRead,
)
def add_options(
    game_id: int,
    category_id: int,
    payload: GameRandomizerOptionsCreate,
    db: Annotated[Session, Depends(get_db)],
    telegram_id: int = Query(..., ge=1),
) -> GameRandomizerCategoryRead:
    try:
        category = randomizer_service.add_options(
            db,
            telegram_id=telegram_id,
            game_id=game_id,
            category_id=category_id,
            values=payload.values,
        )
    except (
        randomizer_service.RandomizerUserNotFoundError,
        randomizer_service.RandomizerBggUsernameRequiredError,
        randomizer_service.RandomizerCategoryNotFoundError,
    ) as exc:
        _raise_randomizer_error(exc)
    return GameRandomizerCategoryRead.model_validate(category)


@router.patch(
    "/{game_id}/categories/{category_id}/options/{option_id}",
    response_model=GameRandomizerCategoryRead,
)
def update_option(
    game_id: int,
    category_id: int,
    option_id: int,
    payload: GameRandomizerOptionUpdate,
    db: Annotated[Session, Depends(get_db)],
    telegram_id: int = Query(..., ge=1),
) -> GameRandomizerCategoryRead:
    try:
        category = randomizer_service.update_option(
            db,
            telegram_id=telegram_id,
            game_id=game_id,
            category_id=category_id,
            option_id=option_id,
            value=payload.value,
        )
    except (
        randomizer_service.RandomizerUserNotFoundError,
        randomizer_service.RandomizerBggUsernameRequiredError,
        randomizer_service.RandomizerCategoryNotFoundError,
    ) as exc:
        _raise_randomizer_error(exc)
    return GameRandomizerCategoryRead.model_validate(category)


@router.delete(
    "/{game_id}/categories/{category_id}/options/{option_id}",
    response_model=GameRandomizerCategoryRead,
)
def delete_option(
    game_id: int,
    category_id: int,
    option_id: int,
    db: Annotated[Session, Depends(get_db)],
    telegram_id: int = Query(..., ge=1),
) -> GameRandomizerCategoryRead:
    try:
        category = randomizer_service.delete_option(
            db,
            telegram_id=telegram_id,
            game_id=game_id,
            category_id=category_id,
            option_id=option_id,
        )
    except (
        randomizer_service.RandomizerUserNotFoundError,
        randomizer_service.RandomizerBggUsernameRequiredError,
        randomizer_service.RandomizerCategoryNotFoundError,
    ) as exc:
        _raise_randomizer_error(exc)
    return GameRandomizerCategoryRead.model_validate(category)


@router.post("/{game_id}/draw", response_model=GameRandomizerDrawRead)
def draw(
    game_id: int,
    payload: GameRandomizerDrawRequest,
    db: Annotated[Session, Depends(get_db)],
    telegram_id: int = Query(..., ge=1),
) -> GameRandomizerDrawRead:
    try:
        game, categories = randomizer_service.draw(
            db,
            telegram_id=telegram_id,
            game_id=game_id,
            category_ids=payload.category_ids,
            player_count=payload.player_count,
        )
    except (
        randomizer_service.RandomizerUserNotFoundError,
        randomizer_service.RandomizerBggUsernameRequiredError,
        randomizer_service.RandomizerGameNotFoundError,
        randomizer_service.RandomizerCategoryNotFoundError,
        randomizer_service.RandomizerInvalidDrawError,
    ) as exc:
        _raise_randomizer_error(exc)
    return GameRandomizerDrawRead(
        game=GameRead.model_validate(game),
        categories=categories,
    )
