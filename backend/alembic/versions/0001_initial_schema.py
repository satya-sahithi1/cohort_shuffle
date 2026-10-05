"""Initial schema — all 9 tables.

Creates:
  Enums  : activity_status, cohort_role, lock_constraint_type
  Tables : users, cohorts, cohort_members, activities, activity_locks,
           registrations, teams, team_members, formation_logs

Revision ID: 0001
Revises    : (none — this is the first migration)
Create Date: 2026-10-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ── Revision identifiers ──────────────────────────────────────────────────────
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _enum(name: str) -> sa.String:
    """
    Return a column type that uses an already-existing PostgreSQL enum by name.
    We use postgresql.ENUM with create_type=False AND schema-qualify the name
    so SQLAlchemy never emits a CREATE TYPE statement.
    """
    return postgresql.ENUM(name=name, create_type=False)


# ── Upgrade ───────────────────────────────────────────────────────────────────

def upgrade() -> None:

    # ── Enums — created once with raw SQL ─────────────────────────────────
    # We own the lifecycle entirely. Columns reference these by name only
    # via _enum() which sets create_type=False so SQLAlchemy never
    # tries to CREATE TYPE again.
    op.execute(
        "CREATE TYPE activity_status AS ENUM "
        "('open', 'closed', 'forming', 'formed')"
    )
    op.execute(
        "CREATE TYPE cohort_role AS ENUM ('admin', 'student')"
    )
    op.execute(
        "CREATE TYPE lock_constraint_type AS ENUM ('together', 'apart')"
    )

    # ── 1. users ──────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.Text(), unique=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        # nullable — Google id added later when OAuth is wired up
        sa.Column("google_id", sa.Text(), unique=True, nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
    )

    # ── 2. cohorts ────────────────────────────────────────────────────────
    op.create_table(
        "cohorts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "admin_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("allowed_domain", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_cohorts_admin_id", "cohorts", ["admin_id"])

    # ── 3. cohort_members ─────────────────────────────────────────────────
    op.create_table(
        "cohort_members",
        sa.Column(
            "cohort_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cohorts.id", ondelete="CASCADE"),
            primary_key=True, nullable=False,
        ),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True, nullable=False,
        ),
        sa.Column("role", _enum("cohort_role"), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "joined_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_cohort_members_user_id", "cohort_members", ["user_id"])

    # ── 4. activities ─────────────────────────────────────────────────────
    op.create_table(
        "activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "cohort_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cohorts.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("team_size", sa.Integer(), nullable=False),
        sa.Column("duration", sa.Text(), nullable=False),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("participant_cap", sa.Integer(), nullable=True),
        sa.Column(
            "status", _enum("activity_status"),
            nullable=False, server_default="open",
        ),
        sa.Column("formation_run_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_activities_cohort_id", "activities", ["cohort_id"])
    op.create_index("ix_activities_status", "activities", ["status"])
    op.create_index("ix_activities_deadline_at", "activities", ["deadline_at"])

    # ── 5. activity_locks ─────────────────────────────────────────────────
    op.create_table(
        "activity_locks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "activity_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("activities.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "user_a", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "user_b", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("constraint_type", _enum("lock_constraint_type"), nullable=False),
    )
    op.create_index("ix_activity_locks_activity_id", "activity_locks", ["activity_id"])

    # ── 6. registrations ─────────────────────────────────────────────────
    op.create_table(
        "registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "activity_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("activities.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "registered_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("activity_id", "user_id", name="uq_registration"),
    )
    op.create_index("ix_registrations_activity_id", "registrations", ["activity_id"])
    op.create_index("ix_registrations_user_id", "registrations", ["user_id"])

    # ── 7. teams ─────────────────────────────────────────────────────────
    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "activity_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("activities.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("team_number", sa.Integer(), nullable=False),
        sa.Column("formation_run", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_teams_activity_id", "teams", ["activity_id"])
    op.create_index("ix_teams_activity_run", "teams", ["activity_id", "formation_run"])

    # ── 8. team_members ───────────────────────────────────────────────────
    op.create_table(
        "team_members",
        sa.Column(
            "team_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("teams.id", ondelete="CASCADE"),
            primary_key=True, nullable=False,
        ),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True, nullable=False,
        ),
    )
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"])

    # ── 9. formation_logs ─────────────────────────────────────────────────
    op.create_table(
        "formation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "activity_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("activities.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("run_number", sa.Integer(), nullable=False),
        sa.Column(
            "triggered_by", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("repeat_pairs", sa.Integer(), nullable=False),
        sa.Column("saturation", sa.Float(), nullable=False),
        # random_seed stored so any formation run can be reproduced exactly
        sa.Column("random_seed", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_formation_logs_activity_id", "formation_logs", ["activity_id"])


# ── Downgrade ─────────────────────────────────────────────────────────────────

def downgrade() -> None:
    # Drop tables in reverse FK dependency order
    op.drop_table("formation_logs")
    op.drop_table("team_members")
    op.drop_table("teams")
    op.drop_table("registrations")
    op.drop_table("activity_locks")
    op.drop_table("activities")
    op.drop_table("cohort_members")
    op.drop_table("cohorts")
    op.drop_table("users")

    # Drop enums after all tables that reference them are gone
    op.execute("DROP TYPE IF EXISTS lock_constraint_type")
    op.execute("DROP TYPE IF EXISTS cohort_role")
    op.execute("DROP TYPE IF EXISTS activity_status")
