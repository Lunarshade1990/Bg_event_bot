"""Add persistent votes to proposed meetup games.

Revision ID: 0009_add_meetup_game_votes
Revises: 0008_add_game_randomizers
Create Date: 2026-10-14 00:00:00
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0009_add_meetup_game_votes"
down_revision = "0008_add_game_randomizers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meetup_game_votes",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("meetup_id", sa.BigInteger(), nullable=False),
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
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
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["meetup_id"], ["meetups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "meetup_id",
            "game_id",
            "user_id",
            name="uq_meetup_game_votes_meetup_game_user",
        ),
    )


def downgrade() -> None:
    op.drop_table("meetup_game_votes")
