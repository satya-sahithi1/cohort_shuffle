"""
schemas/activity.py — Pydantic request and response schemas for activities.

Design:
  - ActivityCreate: what the frontend POSTs when creating an activity.
  - ActivityUpdate: PATCH payload, all fields optional.
  - ActivityLockSchema: one lock constraint (in/out).
  - ActivityOut: what the API returns — matches the frontend Activity type.

We use `from_attributes = True` (Pydantic v2) so these schemas can be
instantiated directly from SQLAlchemy ORM objects.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ── Lock schemas ──────────────────────────────────────────────────────────────

class ActivityLockIn(BaseModel):
    """One lock constraint sent by the admin in the create/update payload."""
    user_a_id: uuid.UUID
    user_b_id: uuid.UUID
    constraint_type: Literal["together", "apart"]

    @model_validator(mode="after")
    def users_must_differ(self) -> "ActivityLockIn":
        if self.user_a_id == self.user_b_id:
            raise ValueError("user_a_id and user_b_id must be different users")
        return self


class ActivityLockOut(BaseModel):
    """Lock constraint as returned by the API."""
    id: uuid.UUID
    user_a_id: uuid.UUID
    user_a_name: str = ""          # resolved by the router from the join
    user_b_id: uuid.UUID
    user_b_name: str = ""
    constraint_type: Literal["together", "apart"]

    model_config = {"from_attributes": True}


# ── Activity schemas ──────────────────────────────────────────────────────────

class ActivityCreate(BaseModel):
    """
    POST /cohorts/{cohort_id}/activities

    All required fields are enforced here.
    deadline_at must be before event_at.
    team_size must be at least 2.
    """
    name: str = Field(..., min_length=1, max_length=255)
    team_size: int = Field(..., ge=2)
    duration: str = Field(..., min_length=1, max_length=100)
    event_at: datetime
    deadline_at: datetime
    participant_cap: int | None = Field(default=None, ge=2)
    locks: list[ActivityLockIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def deadline_before_event(self) -> "ActivityCreate":
        if self.deadline_at >= self.event_at:
            raise ValueError("deadline_at must be before event_at")
        return self


class ActivityUpdate(BaseModel):
    """
    PATCH /activities/{id}

    All fields optional — only send what's changing.
    Locks, if provided, replace the whole set (not a partial update).
    """
    name: str | None = Field(default=None, min_length=1, max_length=255)
    team_size: int | None = Field(default=None, ge=2)
    duration: str | None = Field(default=None, min_length=1, max_length=100)
    event_at: datetime | None = None
    deadline_at: datetime | None = None
    participant_cap: int | None = Field(default=None, ge=2)
    # When provided (even as []), replaces all locks
    locks: list[ActivityLockIn] | None = None


class ActivityOut(BaseModel):
    """
    Activity as returned by GET and POST responses.
    Matches the frontend `Activity` TypeScript type.
    """
    id: uuid.UUID
    cohort_id: uuid.UUID
    name: str
    team_size: int
    duration: str
    event_at: datetime
    deadline_at: datetime
    participant_cap: int | None
    status: Literal["open", "closed", "formed"]
    registration_count: int = 0
    locks: list[ActivityLockOut] = []
    created_at: datetime
    formation_run_count: int

    model_config = {"from_attributes": True}
