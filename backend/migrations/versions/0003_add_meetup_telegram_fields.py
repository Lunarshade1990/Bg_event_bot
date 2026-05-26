"""Add telegram binding fields to meetups.

Revision ID: 0003_add_meetup_telegram_fields
Revises: 0002_add_bgg_expands_ids_cached
Create Date: 2026-05-26 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_add_meetup_telegram_fields"
down_revision = "0002_add_bgg_expands_ids_cached"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meetups", sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True))
    op.add_column("meetups", sa.Column("telegram_thread_id", sa.BigInteger(), nullable=True))
    op.add_column("meetups", sa.Column("telegram_message_id", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("meetups", "telegram_message_id")
    op.drop_column("meetups", "telegram_thread_id")
    op.drop_column("meetups", "telegram_chat_id")

