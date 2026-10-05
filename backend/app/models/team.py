"""
models/team.py — Team, TeamMember, and FormationLog ORM models.

A Team belongs to one Activity. formation_run links it to a specific run
so re-runs don't mix old and new teams — only the latest run's teams are shown.

TeamMember is the many-to-many join between teams and users.
All team history is derived from this table — no separate pair history table.

FormationLog records each time formation ran: who triggered it, the score,
how many repeat pairs there were, and the saturation fraction.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activities.id"), nullable=False
    )
    # Sequential number within the activity, e.g. 1, 2, 3
    team_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Which formation run produced this team (increments on re-run)
    formation_run: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # ── Relationships ──────────────────────────────────────────────────────
    activity: Mapped["Activity"] = relationship(  # noqa: F821
        "Activity", back_populates="teams"
    )
    members: Mapped[list["TeamMember"]] = relationship(
        "TeamMember",
        back_populates="team",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Team id={self.id} activity={self.activity_id} number={self.team_number}>"


class TeamMember(Base):
    __tablename__ = "team_members"

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )

    # ── Relationships ──────────────────────────────────────────────────────
    team: Mapped["Team"] = relationship("Team", back_populates="members")
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="team_memberships"
    )

    def __repr__(self) -> str:
        return f"<TeamMember team={self.team_id} user={self.user_id}>"


class FormationLog(Base):
    __tablename__ = "formation_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activities.id"), nullable=False
    )
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # null = triggered automatically by the scheduler
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    # Lower score = fewer repeats = better
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    repeat_pairs: Mapped[int] = mapped_column(Integer, nullable=False)
    # fraction of possible pairs that have already worked together
    saturation: Mapped[float] = mapped_column(Float, nullable=False)
    # seed used for this run — stored so the result can be reproduced exactly
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────
    activity: Mapped["Activity"] = relationship(  # noqa: F821
        "Activity", back_populates="formation_logs"
    )

    def __repr__(self) -> str:
        return (
            f"<FormationLog activity={self.activity_id} "
            f"run={self.run_number} score={self.score}>"
        )
