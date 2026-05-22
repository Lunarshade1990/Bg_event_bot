from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin
from backend.app.db.models.enums import MeetupStatus, enum_values

if TYPE_CHECKING:
    from backend.app.db.models.meetup_game import MeetupGame
    from backend.app.db.models.meetup_participant import MeetupParticipant
    from backend.app.db.models.user import User


class Meetup(TimestampMixin, Base):
    __tablename__ = "meetups"
    __table_args__ = (CheckConstraint("capacity_total >= 1", name="capacity_total_positive"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    creator_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[str] = mapped_column(Text, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    capacity_total: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[MeetupStatus] = mapped_column(
        Enum(MeetupStatus, name="meetup_status", values_callable=enum_values),
        default=MeetupStatus.PLANNED,
        nullable=False,
    )

    creator: Mapped["User"] = relationship(back_populates="created_meetups")
    meetup_games: Mapped[list["MeetupGame"]] = relationship(
        back_populates="meetup",
        cascade="all, delete-orphan",
    )
    participants: Mapped[list["MeetupParticipant"]] = relationship(
        back_populates="meetup",
        cascade="all, delete-orphan",
    )
