"""Add telegram chat topics table.

Revision ID: 0004_add_telegram_chat_topics
Revises: 0003_add_meetup_telegram_fields
Create Date: 2026-05-27 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0004_add_telegram_chat_topics"
down_revision = "0003_add_meetup_telegram_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_chat_topics",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_thread_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_telegram_chat_topics")),
        sa.UniqueConstraint("telegram_chat_id", name=op.f("uq_telegram_chat_topics_telegram_chat_id")),
    )
    op.create_index(
        op.f("ix_telegram_chat_topics_telegram_chat_id"),
        "telegram_chat_topics",
        ["telegram_chat_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("telegram_chat_topics")
