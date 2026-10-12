from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Identity, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin
from backend.app.db.models.game_randomizer_category import GameRandomizerCategory


class GameRandomizerOption(TimestampMixin, Base):
    __tablename__ = "game_randomizer_options"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    category_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("game_randomizer_categories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    value: Mapped[str] = mapped_column(String(500), nullable=False)

    category: Mapped[GameRandomizerCategory] = relationship(back_populates="options")
