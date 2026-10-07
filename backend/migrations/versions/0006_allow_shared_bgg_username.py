"""Allow multiple users to share a BGG username.

Revision ID: 0006_allow_shared_bgg_username
Revises: 0005_add_telegram_chat_members
Create Date: 2026-10-07 00:00:00
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "0006_allow_shared_bgg_username"
down_revision = "0005_add_telegram_chat_members"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(op.f("uq_users_bgg_username"), "users", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(op.f("uq_users_bgg_username"), "users", ["bgg_username"])