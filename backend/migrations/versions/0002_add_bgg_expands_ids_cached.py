"""Add cached BGG base-expansion relations to games.

Revision ID: 0002_add_bgg_expands_ids_cached
Revises: 0001_initial_schema
Create Date: 2026-05-26 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_add_bgg_expands_ids_cached"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("games", sa.Column("bgg_expands_ids_cached", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("games", "bgg_expands_ids_cached")
