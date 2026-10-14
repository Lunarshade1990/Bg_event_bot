from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Identity, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.game import Game
    from backend.app.db.models.meetup import Meetup
    from backend.app.db.models.user import User


class MeetupGameVote(TimestampMixin, Base):
    __tablename__ = "meetup_game_votes"
    __table_args__ = (
        UniqueConstraint(
            "meetup_id",
            "game_id",
            "user_id",
            name="uq_meetup_game_votes_meetup_game_user",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    meetup_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("meetups.id", ondelete="CASCADE"),
        nullable=False,
    )
    game_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    meetup: Mapped[Meetup] = relationship(back_populates="game_votes")
    game: Mapped[Game] = relationship()
    user: Mapped[User] = relationship(back_populates="meetup_game_votes")
