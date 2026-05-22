"""Create initial database schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-01 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


game_type_enum = sa.Enum("base", "expansion", name="game_type")
campaign_source_enum = sa.Enum("unknown", "bgg", "admin_manual", name="campaign_source")
ownership_source_enum = sa.Enum("bgg_import", "manual", name="ownership_source")
meetup_status_enum = sa.Enum("planned", "cancelled", "completed", name="meetup_status")
participant_status_enum = sa.Enum("joined", "cancelled", name="participant_status")
import_job_status_enum = sa.Enum(
    "pending",
    "in_progress",
    "completed",
    "failed",
    name="import_job_status",
)
game_type_column_enum = postgresql.ENUM("base", "expansion", name="game_type", create_type=False)
campaign_source_column_enum = postgresql.ENUM(
    "unknown",
    "bgg",
    "admin_manual",
    name="campaign_source",
    create_type=False,
)
ownership_source_column_enum = postgresql.ENUM(
    "bgg_import",
    "manual",
    name="ownership_source",
    create_type=False,
)
meetup_status_column_enum = postgresql.ENUM(
    "planned",
    "cancelled",
    "completed",
    name="meetup_status",
    create_type=False,
)
participant_status_column_enum = postgresql.ENUM(
    "joined",
    "cancelled",
    name="participant_status",
    create_type=False,
)
import_job_status_column_enum = postgresql.ENUM(
    "pending",
    "in_progress",
    "completed",
    "failed",
    name="import_job_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    game_type_enum.create(bind, checkfirst=True)
    campaign_source_enum.create(bind, checkfirst=True)
    ownership_source_enum.create(bind, checkfirst=True)
    meetup_status_enum.create(bind, checkfirst=True)
    participant_status_enum.create(bind, checkfirst=True)
    import_job_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("bgg_username", sa.String(length=255), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("bgg_username", name=op.f("uq_users_bgg_username")),
        sa.UniqueConstraint("telegram_id", name=op.f("uq_users_telegram_id")),
    )
    op.create_index(op.f("ix_users_telegram_id"), "users", ["telegram_id"], unique=False)

    op.create_table(
        "games",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("bgg_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("original_title", sa.String(length=500), nullable=True),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("min_players", sa.Integer(), nullable=False),
        sa.Column("max_players", sa.Integer(), nullable=False),
        sa.Column("play_time_minutes", sa.Integer(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("game_type", game_type_column_enum, nullable=False),
        sa.Column("has_campaign", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "campaign_source",
            campaign_source_column_enum,
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("bgg_raw_mechanics_cached", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("max_players > 0", name=op.f("ck_games_max_players_positive")),
        sa.CheckConstraint("min_players <= max_players", name=op.f("ck_games_players_range_valid")),
        sa.CheckConstraint("min_players > 0", name=op.f("ck_games_min_players_positive")),
        sa.CheckConstraint(
            "play_time_minutes IS NULL OR play_time_minutes > 0",
            name=op.f("ck_games_play_time_minutes_positive"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_games")),
        sa.UniqueConstraint("bgg_id", name=op.f("uq_games_bgg_id")),
    )
    op.create_index(op.f("ix_games_bgg_id"), "games", ["bgg_id"], unique=False)

    op.create_table(
        "meetups",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("creator_user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.Text(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("capacity_total", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            meetup_status_column_enum,
            nullable=False,
            server_default="planned",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("capacity_total >= 1", name=op.f("ck_meetups_capacity_total_positive")),
        sa.ForeignKeyConstraint(
            ["creator_user_id"],
            ["users.id"],
            name=op.f("fk_meetups_creator_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meetups")),
    )

    op.create_table(
        "bgg_import_jobs",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("bgg_username", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            import_job_status_column_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("imported_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("imported_count >= 0", name=op.f("ck_bgg_import_jobs_imported_count_non_negative")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_bgg_import_jobs_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bgg_import_jobs")),
    )

    op.create_table(
        "user_games",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("source", ownership_source_column_enum, nullable=False),
        sa.Column("is_available_for_meetups", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            name=op.f("fk_user_games_game_id_games"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_games_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_games")),
        sa.UniqueConstraint("user_id", "game_id", name="uq_user_games_user_id_game_id"),
    )

    op.create_table(
        "meetup_games",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("meetup_id", sa.BigInteger(), nullable=False),
        sa.Column("game_id", sa.BigInteger(), nullable=False),
        sa.Column("added_by_user_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["added_by_user_id"],
            ["users.id"],
            name=op.f("fk_meetup_games_added_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            name=op.f("fk_meetup_games_game_id_games"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["meetup_id"],
            ["meetups.id"],
            name=op.f("fk_meetup_games_meetup_id_meetups"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meetup_games")),
        sa.UniqueConstraint("meetup_id", "game_id", name="uq_meetup_games_meetup_id_game_id"),
    )

    op.create_table(
        "meetup_participants",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("meetup_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            participant_status_column_enum,
            nullable=False,
            server_default="joined",
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["meetup_id"],
            ["meetups.id"],
            name=op.f("fk_meetup_participants_meetup_id_meetups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_meetup_participants_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meetup_participants")),
        sa.UniqueConstraint("meetup_id", "user_id", name="uq_meetup_participants_meetup_id_user_id"),
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_table("meetup_participants")
    op.drop_table("meetup_games")
    op.drop_table("user_games")
    op.drop_table("bgg_import_jobs")
    op.drop_table("meetups")
    op.drop_index(op.f("ix_games_bgg_id"), table_name="games")
    op.drop_table("games")
    op.drop_index(op.f("ix_users_telegram_id"), table_name="users")
    op.drop_table("users")

    import_job_status_enum.drop(bind, checkfirst=True)
    participant_status_enum.drop(bind, checkfirst=True)
    meetup_status_enum.drop(bind, checkfirst=True)
    ownership_source_enum.drop(bind, checkfirst=True)
    campaign_source_enum.drop(bind, checkfirst=True)
    game_type_enum.drop(bind, checkfirst=True)
