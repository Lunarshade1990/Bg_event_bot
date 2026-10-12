"""Add BGG-profile game randomizers.

Revision ID: 0008_add_game_randomizers
Revises: 0007_add_meetup_game_suggestions
Create Date: 2026-10-12 00:00:00
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0008_add_game_randomizers"
down_revision = "0007_add_meetup_game_suggestions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_randomizer_categories",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("bgg_username", sa.String(length=255), nullable=False),
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("draw_count", sa.Integer(), nullable=True),
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
        sa.CheckConstraint(
            "draw_count IS NULL OR draw_count > 0",
            name=op.f("ck_game_randomizer_categories_draw_count_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            name=op.f("fk_game_randomizer_categories_game_id_games"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_game_randomizer_categories"),
        ),
        sa.UniqueConstraint(
            "bgg_username",
            "game_id",
            "name",
            name="uq_game_randomizer_categories_bgg_game_name",
        ),
    )
    op.create_index(
        op.f("ix_game_randomizer_categories_bgg_username"),
        "game_randomizer_categories",
        ["bgg_username"],
        unique=False,
    )
    op.create_index(
        op.f("ix_game_randomizer_categories_game_id"),
        "game_randomizer_categories",
        ["game_id"],
        unique=False,
    )
    op.create_table(
        "game_randomizer_options",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("value", sa.String(length=500), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["game_randomizer_categories.id"],
            name=op.f("fk_game_randomizer_options_category_id_game_randomizer_categories"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_game_randomizer_options")),
    )
    op.create_index(
        op.f("ix_game_randomizer_options_category_id"),
        "game_randomizer_options",
        ["category_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_game_randomizer_options_category_id"), table_name="game_randomizer_options"
    )
    op.drop_table("game_randomizer_options")
    op.drop_index(
        op.f("ix_game_randomizer_categories_game_id"), table_name="game_randomizer_categories"
    )
    op.drop_index(
        op.f("ix_game_randomizer_categories_bgg_username"),
        table_name="game_randomizer_categories",
    )
    op.drop_table("game_randomizer_categories")
