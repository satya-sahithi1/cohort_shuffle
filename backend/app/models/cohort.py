"""
models/cohort.py — Cohort and CohortMember ORM models.

A Cohort is a class/batch/group. All activities and team history are
scoped to a cohort — two cohorts never share data.

CohortMember is the join table between users and cohorts.
role is 'admin' or 'student' within this cohort (not global).
is_archived lets us deactivate a member without deleting their history.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Cohort(Base):
    __tablename__ = "cohorts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    # Optional email domain restriction, e.g. "students.university.edu"
    # null = any Google account can join
    allowed_domain: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────
    members: Mapped[list["CohortMember"]] = relationship(
        "CohortMember", back_populates="cohort", lazy="select"
    )
    activities: Mapped[list["Activity"]] = relationship(  # noqa: F821
        "Activity", back_populates="cohort", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Cohort id={self.id} name={self.name!r}>"


class CohortMember(Base):
    __tablename__ = "cohort_members"

    cohort_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cohorts.id"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    role: Mapped[str] = mapped_column(
        Enum("admin", "student", name="cohort_role"), nullable=False
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────
    cohort: Mapped["Cohort"] = relationship("Cohort", back_populates="members")
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="cohort_memberships"
    )

    def __repr__(self) -> str:
        return f"<CohortMember cohort={self.cohort_id} user={self.user_id} role={self.role!r}>"
