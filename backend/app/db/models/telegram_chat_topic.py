from __future__ import annotations

from sqlalchemy import BigInteger, Identity
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin


class TelegramChatTopic(TimestampMixin, Base):
    __tablename__ = "telegram_chat_topics"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    telegram_thread_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
