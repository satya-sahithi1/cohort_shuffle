"""
models/registration.py — Registration ORM model.

A registration records that a specific user has opted in to a specific
activity. Only registered users are included in team formation.

The UNIQUE constraint on (activity_id, user_id) prevents double-registration
at the DB level — no race condition can produce duplicates.

registered_at is used for cap enforcement: when a cap is set, registrations
are accepted in timestamp order and the cap'th registration closes the activity.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (UniqueConstraint("activity_id", "user_id", name="uq_registration"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    activity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activities.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────────────
    activity: Mapped["Activity"] = relationship(  # noqa: F821
        "Activity", back_populates="registrations"
    )
    user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="registrations"
    )

    def __repr__(self) -> str:
        return f"<Registration activity={self.activity_id} user={self.user_id}>"
