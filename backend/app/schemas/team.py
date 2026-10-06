"""
schemas/team.py — Pydantic request and response schemas for teams.

TeamMemberOut    one member inside a team (user_id + name + email)
TeamOut          one team with its members (used for GET /activities/{id}/teams)
TeamHistoryOut   team entry in a user's history (includes activity info)
FormationLogOut  one formation log entry
TeamMemberPatch  PATCH /teams/{id}/members body
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Team member ───────────────────────────────────────────────────────────────

class TeamMemberOut(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str

    model_config = {"from_attributes": True}


# ── Team ──────────────────────────────────────────────────────────────────────

class TeamOut(BaseModel):
    """
    One team as returned by GET /activities/{id}/teams.
    `formation_run` lets the frontend know which run produced this team.
    """
    id: uuid.UUID
    activity_id: uuid.UUID
    team_number: int
    formation_run: int
    members: list[TeamMemberOut] = []

    model_config = {"from_attributes": True}


# ── Team history (student view) ───────────────────────────────────────────────

class TeamHistoryOut(BaseModel):
    """
    One team entry in GET /users/me/teams.
    Includes enough activity info for the student to identify the event.
    """
    team_id: uuid.UUID
    team_number: int
    activity_id: uuid.UUID
    activity_name: str
    event_at: datetime
    members: list[TeamMemberOut] = []

    model_config = {"from_attributes": True}


# ── Formation log ─────────────────────────────────────────────────────────────

class FormationLogOut(BaseModel):
    """
    One formation log entry as returned by GET /activities/{id}/teams.
    Mirrors the FormationLog DB model; used by admin activity detail page.
    """
    id: uuid.UUID
    activity_id: uuid.UUID
    run_number: int
    triggered_by: uuid.UUID | None
    score: int
    repeat_pairs: int
    saturation: float
    random_seed: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Patch body ────────────────────────────────────────────────────────────────

class TeamMemberPatch(BaseModel):
    """
    PATCH /teams/{team_id}/members
    Replaces the entire member list of a team.
    Provide the full desired list of user_ids.
    """
    user_ids: list[uuid.UUID] = Field(..., min_length=1)
