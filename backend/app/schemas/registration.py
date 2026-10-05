"""
schemas/registration.py — Pydantic schemas for registrations.

RegistrationOut is used by GET /activities/{id}/registrations (admin).
It includes the user's name and email, resolved via a join.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class RegistrationOut(BaseModel):
    """
    One registration record as returned to the admin.
    Matches the frontend `Registration` TypeScript type.
    """
    id: uuid.UUID
    activity_id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    user_email: str
    registered_at: datetime

    model_config = {"from_attributes": True}


class MyRegistrationOut(BaseModel):
    """Minimal response for the student's own registration check."""
    registered: bool
    registered_at: datetime | None = None
