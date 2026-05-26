from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.dependencies.db import get_db
from backend.app.schemas.meetup import (
    MeetupCreateRequest,
    MeetupDeleteRequest,
    MeetupJoinRequest,
    MeetupLeaveRequest,
    MeetupRead,
    MeetupTelegramMessageRequest,
)
from backend.app.schemas.telegram_chat_topic import (
    TelegramChatTopicCreateRequest,
    TelegramChatTopicRead,
)
from backend.app.services import meetups as meetup_service
from backend.app.services import telegram_chat_topics as telegram_chat_topic_service

router = APIRouter(prefix="/meetups", tags=["meetups"])


@router.post("", response_model=MeetupRead, status_code=status.HTTP_201_CREATED)
def create_meetup(payload: MeetupCreateRequest, db: Session = Depends(get_db)) -> MeetupRead:
    try:
        return meetup_service.create_meetup(db, payload)
    except meetup_service.MeetupNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("", response_model=list[MeetupRead])
def list_meetups(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    telegram_chat_id: int | None = Query(default=None),
) -> list[MeetupRead]:
    return meetup_service.list_meetups(
        db,
        telegram_chat_id=telegram_chat_id,
        limit=limit,
        offset=offset,
    )


@router.get("/telegram-topics/{telegram_chat_id}", response_model=TelegramChatTopicRead)
def get_telegram_chat_topic(
    telegram_chat_id: int,
    db: Session = Depends(get_db),
) -> TelegramChatTopicRead:
    telegram_topic = telegram_chat_topic_service.get_telegram_chat_topic(db, telegram_chat_id)
    if telegram_topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Telegram topic not found.")
    return telegram_topic


@router.post(
    "/telegram-topics",
    response_model=TelegramChatTopicRead,
    status_code=status.HTTP_201_CREATED,
)
def upsert_telegram_chat_topic(
    payload: TelegramChatTopicCreateRequest,
    db: Session = Depends(get_db),
) -> TelegramChatTopicRead:
    return telegram_chat_topic_service.upsert_telegram_chat_topic(db, payload)


@router.get("/{meetup_id}", response_model=MeetupRead)
def get_meetup(meetup_id: int, db: Session = Depends(get_db)) -> MeetupRead:
    meetup = meetup_service.get_meetup(db, meetup_id)
    if meetup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meetup not found.")
    return meetup


@router.post("/{meetup_id}/join", response_model=MeetupRead)
def join_meetup(
    meetup_id: int,
    payload: MeetupJoinRequest,
    db: Session = Depends(get_db),
) -> MeetupRead:
    try:
        return meetup_service.join_meetup(db, meetup_id, payload.user_id)
    except meetup_service.MeetupNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except meetup_service.MeetupNotJoinableError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except meetup_service.MeetupAlreadyJoinedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except meetup_service.MeetupCapacityFullError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{meetup_id}/leave", response_model=MeetupRead)
def leave_meetup(
    meetup_id: int,
    payload: MeetupLeaveRequest,
    db: Session = Depends(get_db),
) -> MeetupRead:
    try:
        return meetup_service.leave_meetup(db, meetup_id, payload.user_id)
    except meetup_service.MeetupNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{meetup_id}/telegram-message", response_model=MeetupRead)
def set_telegram_message_id(
    meetup_id: int,
    payload: MeetupTelegramMessageRequest,
    db: Session = Depends(get_db),
) -> MeetupRead:
    try:
        return meetup_service.set_telegram_message_id(db, meetup_id, payload.telegram_message_id)
    except meetup_service.MeetupNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{meetup_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meetup(
    meetup_id: int,
    payload: MeetupDeleteRequest,
    db: Session = Depends(get_db),
) -> None:
    try:
        meetup_service.delete_meetup(db, meetup_id, payload.requesting_user_id)
    except meetup_service.MeetupNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except meetup_service.MeetupForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
