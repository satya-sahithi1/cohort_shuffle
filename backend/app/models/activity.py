"""
models/activity.py — Activity and ActivityLock ORM models.

An Activity is a single event posted by an admin.
Status transitions:
  open → closed  (deadline passes, or cap is reached)
  closed → formed (formation runs successfully)

formation_run_count increments each time formation runs (supports re-runs).

ActivityLock pins two students relative to each other before formation.
The admin sets these; they are constraints the algorithm must respect.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cohort_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cohorts.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    team_size: Mapped[int] = mapped_column(Integer, nullable=False)
    # Human-readable duration, e.g. "2 hours"
    duration: Mapped[str] = mapped_column(Text, nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # null = no cap; when set, registration closes the moment it's reached
    participant_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("open", "closed", "forming", "formed", name="activity_status"),
        default="open",
        nullable=False,
    )
    formation_run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────
    cohort: Mapped["Cohort"] = relationship(  # noqa: F821
        "Cohort", back_populates="activities"
    )
    locks: Mapped[list["ActivityLock"]] = relationship(
        "ActivityLock",
        back_populates="activity",
        cascade="all, delete-orphan",
        lazy="select",
    )
    registrations: Mapped[list["Registration"]] = relationship(  # noqa: F821
        "Registration",
        back_populates="activity",
        cascade="all, delete-orphan",
        lazy="select",
    )
    teams: Mapped[list["Team"]] = relationship(  # noqa: F821
        "Team",
        back_populates="activity",
        cascade="all, delete-orphan",
        lazy="select",
    )
    formation_logs: Mapped[list["FormationLog"]] = relationship(  # noqa: F821
        "FormationLog",
        back_populates="activity",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Activity id={self.id} name={self.name!r} status={self.status!r}>"


class ActivityLock(Base):
    __tablename__ = "activity_locks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activities.id"), nullable=False
    )
    user_a: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    user_b: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    constraint_type: Mapped[str] = mapped_column(
        Enum("together", "apart", name="lock_constraint_type"), nullable=False
    )

    # ── Relationships ──────────────────────────────────────────────────────
    activity: Mapped["Activity"] = relationship("Activity", back_populates="locks")

    def __repr__(self) -> str:
        return (
            f"<ActivityLock id={self.id} "
            f"type={self.constraint_type!r} "
            f"a={self.user_a} b={self.user_b}>"
        )
