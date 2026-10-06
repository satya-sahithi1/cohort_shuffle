"""
schemas/cohort.py — Pydantic request and response schemas for cohorts.

CohortCreate        POST /cohorts
CohortOut           response for cohort endpoints (includes caller's role)
MemberOut           one member row in GET /cohorts/{id}/members
MemberAdd           POST /cohorts/{id}/members body
MemberPatch         PATCH /cohorts/{id}/members/{uid} body
JoinLinkOut         token returned to admin so they can share it
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Cohort ────────────────────────────────────────────────────────────────────

class CohortCreate(BaseModel):
    """POST /cohorts — admin creates a new cohort."""
    name: str = Field(..., min_length=1, max_length=255)
    # Optional email-domain restriction, e.g. "university.edu"
    # null / omitted = any Google account may join
    allowed_domain: str | None = Field(default=None, max_length=255)


class CohortOut(BaseModel):
    """
    Cohort as returned by the API.
    `role` is the calling user's role in this cohort — used by the frontend
    to decide whether to show admin controls.
    """
    id: uuid.UUID
    name: str
    allowed_domain: str | None
    role: Literal["admin", "student"]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Members ───────────────────────────────────────────────────────────────────

class MemberOut(BaseModel):
    """
    One member as returned by GET /cohorts/{id}/members.
    Includes resolved user fields (name, email) from the User table.
    Matches the frontend CohortMember type.
    """
    user_id: uuid.UUID
    name: str
    email: str
    role: Literal["admin", "student"]
    is_archived: bool
    joined_at: datetime

    model_config = {"from_attributes": True}


class MemberAdd(BaseModel):
    """
    POST /cohorts/{id}/members — admin adds a student by email.
    If the user doesn't exist yet, they'll be created on first sign-in.
    """
    email: str = Field(..., min_length=1, max_length=255)
    role: Literal["admin", "student"] = "student"


class MemberPatch(BaseModel):
    """
    PATCH /cohorts/{id}/members/{uid} — archive/unarchive or change role.
    All fields optional — only send what's changing.
    """
    is_archived: bool | None = None
    role: Literal["admin", "student"] | None = None


# ── Join link ─────────────────────────────────────────────────────────────────

class JoinLinkOut(BaseModel):
    """Response for GET /cohorts/{id}/join-link (admin only)."""
    token: str
    url: str
