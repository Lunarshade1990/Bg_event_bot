"""Add telegram chat members.

Revision ID: 0005_add_telegram_chat_members
Revises: 0004_add_telegram_chat_topics
Create Date: 2026-05-28 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0005_add_telegram_chat_members"
down_revision = "0004_add_telegram_chat_topics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("telegram_chat_topics", sa.Column("title", sa.String(length=255), nullable=True))
    op.create_table(
        "telegram_chat_members",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["telegram_chat_id"],
            ["telegram_chat_topics.telegram_chat_id"],
            name=op.f("fk_telegram_chat_members_telegram_chat_id_telegram_chat_topics"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_telegram_chat_members_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_telegram_chat_members")),
        sa.UniqueConstraint(
            "telegram_chat_id",
            "user_id",
            name="uq_telegram_chat_members_telegram_chat_id_user_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("telegram_chat_members")
    op.drop_column("telegram_chat_topics", "title")
