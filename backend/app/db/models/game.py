from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Enum, Identity, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin
from backend.app.db.models.enums import CampaignSource, GameType, enum_values

if TYPE_CHECKING:
    from backend.app.db.models.meetup_game import MeetupGame
    from backend.app.db.models.user_game import UserGame


class Game(TimestampMixin, Base):
    __tablename__ = "games"
    __table_args__ = (
        CheckConstraint("min_players > 0", name="min_players_positive"),
        CheckConstraint("max_players > 0", name="max_players_positive"),
        CheckConstraint("min_players <= max_players", name="players_range_valid"),
        CheckConstraint(
            "play_time_minutes IS NULL OR play_time_minutes > 0",
            name="play_time_minutes_positive",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    bgg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_players: Mapped[int] = mapped_column(Integer, nullable=False)
    max_players: Mapped[int] = mapped_column(Integer, nullable=False)
    play_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    game_type: Mapped[GameType] = mapped_column(
        Enum(GameType, name="game_type", values_callable=enum_values),
        nullable=False,
    )
    has_campaign: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    campaign_source: Mapped[CampaignSource] = mapped_column(
        Enum(CampaignSource, name="campaign_source", values_callable=enum_values),
        default=CampaignSource.UNKNOWN,
        nullable=False,
    )
    bgg_raw_mechanics_cached: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)

    user_games: Mapped[list["UserGame"]] = relationship(back_populates="game")
    meetup_games: Mapped[list["MeetupGame"]] = relationship(back_populates="game")
