"""
models/user.py — User ORM model.

A user is anyone who has signed in via Google OAuth.
The google_id is the stable identifier we get from Google.
email is used for domain-restriction checks on cohorts.
is_archived is set when a user leaves; we never hard-delete because
their records remain part of other students' team history.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    google_id: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────
    cohort_memberships: Mapped[list["CohortMember"]] = relationship(  # noqa: F821
        "CohortMember", back_populates="user", lazy="select"
    )
    registrations: Mapped[list["Registration"]] = relationship(  # noqa: F821
        "Registration", back_populates="user", lazy="select"
    )
    team_memberships: Mapped[list["TeamMember"]] = relationship(  # noqa: F821
        "TeamMember", back_populates="user", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
