from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Identity,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.game_randomizer_option import GameRandomizerOption


class GameRandomizerCategory(TimestampMixin, Base):
    __tablename__ = "game_randomizer_categories"
    __table_args__ = (
        CheckConstraint(
            "draw_count IS NULL OR draw_count > 0",
            name="draw_count_positive",
        ),
        UniqueConstraint(
            "bgg_username",
            "game_id",
            "name",
            name="uq_game_randomizer_categories_bgg_game_name",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    bgg_username: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    game_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("games.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # NULL means the draw count is equal to the number of players.
    draw_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    options: Mapped[list[GameRandomizerOption]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="GameRandomizerOption.id",
    )
