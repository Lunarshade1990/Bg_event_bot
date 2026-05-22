from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, Identity, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin
from backend.app.db.models.enums import OwnershipSource, enum_values

if TYPE_CHECKING:
    from backend.app.db.models.game import Game
    from backend.app.db.models.user import User


class UserGame(TimestampMixin, Base):
    __tablename__ = "user_games"
    __table_args__ = (UniqueConstraint("user_id", "game_id", name="uq_user_games_user_id_game_id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    game_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[OwnershipSource] = mapped_column(
        Enum(OwnershipSource, name="ownership_source", values_callable=enum_values),
        nullable=False,
    )
    is_available_for_meetups: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="user_games")
    game: Mapped["Game"] = relationship(back_populates="user_games")
