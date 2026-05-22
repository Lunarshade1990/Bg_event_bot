from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.db.models.enums import GameType
from backend.app.dependencies.db import get_db
from backend.app.schemas.game import GameOwnerRead, GameRead
from backend.app.services import games as game_service

router = APIRouter(prefix="/games", tags=["games"])


@router.get("", response_model=list[GameRead])
def list_games(
    db: Session = Depends(get_db),
    title: str | None = Query(default=None),
    owner_id: int | None = Query(default=None, ge=1),
    players_count: int | None = Query(default=None, ge=1),
    max_play_time_minutes: int | None = Query(default=None, ge=1),
    game_type: GameType | None = Query(default=None),
    has_campaign: bool | None = Query(default=None),
    available_only: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[GameRead]:
    games = game_service.list_games(
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
    return [GameRead.model_validate(game) for game in games]


@router.get("/{game_id}", response_model=GameRead)
def get_game(game_id: int, db: Session = Depends(get_db)) -> GameRead:
    game = game_service.get_game(db, game_id)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found.")
    return GameRead.model_validate(game)


@router.get("/{game_id}/owners", response_model=list[GameOwnerRead])
def get_game_owners(game_id: int, db: Session = Depends(get_db)) -> list[GameOwnerRead]:
    game = game_service.get_game(db, game_id)
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found.")

    owners = game_service.get_game_owners(db, game_id)
    return [GameOwnerRead.model_validate(owner) for owner in owners]
