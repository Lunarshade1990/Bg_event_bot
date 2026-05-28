from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Identity, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.app.db.models.telegram_chat_topic import TelegramChatTopic
    from backend.app.db.models.user import User


class TelegramChatMember(TimestampMixin, Base):
    __tablename__ = "telegram_chat_members"
    __table_args__ = (
        UniqueConstraint(
            "telegram_chat_id",
            "user_id",
            name="uq_telegram_chat_members_telegram_chat_id_user_id",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("telegram_chat_topics.telegram_chat_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    chat: Mapped["TelegramChatTopic"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="telegram_chat_memberships")
