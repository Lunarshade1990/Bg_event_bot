from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Identity, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.game import Game
    from backend.app.db.models.meetup import Meetup
    from backend.app.db.models.user import User


class MeetupGameSuggestion(TimestampMixin, Base):
    __tablename__ = "meetup_game_suggestions"
    __table_args__ = (
        UniqueConstraint(
            "meetup_id",
            "proposer_user_id",
            "game_id",
            name="uq_meetup_game_suggestions_meetup_proposer_game",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    meetup_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("meetups.id", ondelete="CASCADE"),
        nullable=False,
    )
    proposer_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    collection_owner_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    game_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("games.id", ondelete="RESTRICT"),
        nullable=False,
    )

    meetup: Mapped[Meetup] = relationship(back_populates="game_suggestions")
    proposer: Mapped[User] = relationship(foreign_keys=[proposer_user_id])
    collection_owner: Mapped[User] = relationship(foreign_keys=[collection_owner_user_id])
    game: Mapped[Game] = relationship()
