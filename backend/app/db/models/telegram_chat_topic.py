from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Identity, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.telegram_chat_member import TelegramChatMember


class TelegramChatTopic(TimestampMixin, Base):
    __tablename__ = "telegram_chat_topics"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    telegram_thread_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    members: Mapped[list["TelegramChatMember"]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
    )
