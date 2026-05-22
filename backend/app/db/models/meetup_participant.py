from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum, ForeignKey, Identity, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin
from backend.app.db.models.enums import ParticipantStatus, enum_values

if TYPE_CHECKING:
    from backend.app.db.models.meetup import Meetup
    from backend.app.db.models.user import User


class MeetupParticipant(TimestampMixin, Base):
    __tablename__ = "meetup_participants"
    __table_args__ = (
        UniqueConstraint("meetup_id", "user_id", name="uq_meetup_participants_meetup_id_user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    meetup_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("meetups.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[ParticipantStatus] = mapped_column(
        Enum(ParticipantStatus, name="participant_status", values_callable=enum_values),
        default=ParticipantStatus.JOINED,
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    meetup: Mapped["Meetup"] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship(back_populates="meetup_participations")
