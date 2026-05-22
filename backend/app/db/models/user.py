from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Identity, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.bgg_import_job import BggImportJob
    from backend.app.db.models.meetup import Meetup
    from backend.app.db.models.meetup_game import MeetupGame
    from backend.app.db.models.meetup_participant import MeetupParticipant
    from backend.app.db.models.user_game import UserGame


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bgg_username: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user_games: Mapped[list["UserGame"]] = relationship(back_populates="user")
    created_meetups: Mapped[list["Meetup"]] = relationship(back_populates="creator")
    meetup_games_added: Mapped[list["MeetupGame"]] = relationship(back_populates="added_by_user")
    meetup_participations: Mapped[list["MeetupParticipant"]] = relationship(back_populates="user")
    bgg_import_jobs: Mapped[list["BggImportJob"]] = relationship(back_populates="user")
