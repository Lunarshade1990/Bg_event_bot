"""Add persistent game suggestions to meetups.

Revision ID: 0007_add_meetup_game_suggestions
Revises: 0006_allow_shared_bgg_username
Create Date: 2026-10-11 00:00:00
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0007_add_meetup_game_suggestions"
down_revision = "0006_allow_shared_bgg_username"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meetup_game_suggestions",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("meetup_id", sa.BigInteger(), nullable=False),
        sa.Column("proposer_user_id", sa.BigInteger(), nullable=False),
        sa.Column("collection_owner_user_id", sa.BigInteger(), nullable=False),
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["collection_owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["meetup_id"], ["meetups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "meetup_id",
            "proposer_user_id",
            "game_id",
            name="uq_meetup_game_suggestions_meetup_proposer_game",
        ),
    )


def downgrade() -> None:
    op.drop_table("meetup_game_suggestions")
