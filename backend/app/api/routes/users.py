from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.dependencies.db import get_db
from backend.app.schemas.user import UserRead, UserSummaryRead, UserTelegramSyncRequest
from backend.app.services import users as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserSummaryRead])
def list_users(
    db: Session = Depends(get_db),
    has_games: bool = Query(default=True),
    exclude_user_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[UserSummaryRead]:
    if not has_games:
        return []
    users = user_service.list_users_with_games(
        db,
        exclude_user_id=exclude_user_id,
        limit=limit,
        offset=offset,
    )
    return [UserSummaryRead.model_validate(user) for user in users]


@router.post("/telegram", response_model=UserRead, status_code=status.HTTP_200_OK)
def sync_telegram_user(
    payload: UserTelegramSyncRequest,
    db: Session = Depends(get_db),
) -> UserRead:
    try:
        user = user_service.sync_telegram_user(db, payload)
    except user_service.BggUsernameAlreadyBoundError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserRead:
    user = user_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return UserRead.model_validate(user)


@router.get("/by-telegram/{telegram_id}", response_model=UserRead)
def get_user_by_telegram_id(telegram_id: int, db: Session = Depends(get_db)) -> UserRead:
    user = user_service.get_user_by_telegram_id(db, telegram_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return UserRead.model_validate(user)
