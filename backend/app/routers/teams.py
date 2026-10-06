"""
routers/teams.py — Team endpoints.

POST  /activities/{activity_id}/form-teams   trigger formation (admin)
GET   /activities/{activity_id}/teams        get teams + logs for an activity
GET   /users/me/teams                        student's full team history
PATCH /teams/{team_id}/members               replace team members (admin)

Three routers are exported:
  activity_teams_router  — mounted at /activities  (form-teams, get teams)
  users_router           — mounted at /users        (me/teams)
  teams_router           — mounted at /teams        (PATCH members)
"""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models.activity import Activity
from app.models.cohort import CohortMember
from app.schemas.team import (
    FormationLogOut,
    TeamHistoryOut,
    TeamMemberOut,
    TeamMemberPatch,
    TeamOut,
)
from app.services import formation_service

activity_teams_router = APIRouter()
teams_router = APIRouter()
users_router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_activity_or_404(db, activity_id: uuid.UUID) -> Activity:
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Activity)
        .where(Activity.id == activity_id)
        .options(selectinload(Activity.locks))
    )
    activity = result.scalar_one_or_none()
    if activity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    return activity


async def _require_member(db, cohort_id: uuid.UUID, user_id: uuid.UUID) -> CohortMember:
    result = await db.execute(
        select(CohortMember).where(
            CohortMember.cohort_id == cohort_id,
            CohortMember.user_id == user_id,
            CohortMember.is_archived == False,  # noqa: E712
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this cohort.",
        )
    return member


async def _require_admin(db, cohort_id: uuid.UUID, user_id: uuid.UUID) -> CohortMember:
    member = await _require_member(db, cohort_id, user_id)
    if member.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return member


# ── Response builders ─────────────────────────────────────────────────────────

def _build_team_out(team) -> TeamOut:
    return TeamOut(
        id=team.id,
        activity_id=team.activity_id,
        team_number=team.team_number,
        formation_run=team.formation_run,
        members=[
            TeamMemberOut(
                user_id=m.user_id,
                name=m.user.name,
                email=m.user.email,
            )
            for m in team.members
        ],
    )


def _build_history_out(team) -> TeamHistoryOut:
    return TeamHistoryOut(
        team_id=team.id,
        team_number=team.team_number,
        activity_id=team.activity_id,
        activity_name=team.activity.name,
        event_at=team.activity.event_at,
        members=[
            TeamMemberOut(
                user_id=m.user_id,
                name=m.user.name,
                email=m.user.email,
            )
            for m in team.members
        ],
    )


# ── POST /activities/{activity_id}/form-teams ─────────────────────────────────

@activity_teams_router.post(
    "/{activity_id}/form-teams",
    response_model=list[TeamOut],
    status_code=status.HTTP_201_CREATED,
    summary="Trigger team formation (admin)",
)
async def form_teams(
    activity_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Admin manually triggers team formation for an activity.
    The activity must be in 'closed' or 'formed' (re-run) status.
    Returns the newly formed teams.
    """
    activity = await _get_activity_or_404(db, activity_id)
    await _require_admin(db, activity.cohort_id, current_user.id)

    if activity.status == "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Close registration before forming teams (activity is still open).",
        )
    if activity.status == "forming":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Formation is already in progress.",
        )

    try:
        await formation_service.run(db, activity_id, triggered_by=current_user.id)
    except formation_service.FormationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    teams = await formation_service.get_teams(db, activity_id)
    return [_build_team_out(t) for t in teams]


# ── GET /activities/{activity_id}/teams ───────────────────────────────────────

class TeamsResponse:
    """Combined response: teams + formation logs."""
    pass


from pydantic import BaseModel


class ActivityTeamsOut(BaseModel):
    """Full team formation result for an activity."""
    teams: list[TeamOut]
    logs: list[FormationLogOut]


@activity_teams_router.get(
    "/{activity_id}/teams",
    response_model=ActivityTeamsOut,
    summary="Get teams and formation logs for an activity",
)
async def get_activity_teams(
    activity_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Any cohort member can view the formed teams.
    Returns the latest run's teams + all formation logs.
    Activity must be 'formed'.
    """
    activity = await _get_activity_or_404(db, activity_id)
    await _require_member(db, activity.cohort_id, current_user.id)

    if activity.status != "formed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Teams are not yet formed. Activity status is '{activity.status}'.",
        )

    teams = await formation_service.get_teams(db, activity_id)
    logs = await formation_service.get_formation_logs(db, activity_id)

    return ActivityTeamsOut(
        teams=[_build_team_out(t) for t in teams],
        logs=[FormationLogOut.model_validate(log) for log in logs],
    )


# ── GET /users/me/teams ───────────────────────────────────────────────────────

@users_router.get(
    "/me/teams",
    response_model=list[TeamHistoryOut],
    summary="My full team history",
    tags=["users"],
)
async def my_team_history(
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Returns all activities the current user was placed in a team for,
    newest activity first.
    """
    teams = await formation_service.get_user_team_history(db, current_user.id)
    return [_build_history_out(t) for t in teams]


# ── PATCH /teams/{team_id}/members ────────────────────────────────────────────

@teams_router.patch(
    "/{team_id}/members",
    response_model=TeamOut,
    summary="Replace team members (admin)",
)
async def patch_team_members(
    team_id: uuid.UUID,
    body: TeamMemberPatch,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Admin replaces the full member list of a team.
    Use this for manual adjustments after formation.
    All provided user_ids must be registered members of the cohort.
    """
    team = await formation_service.get_team_by_id(db, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    await _require_admin(db, team.activity.cohort_id, current_user.id)

    # Verify all provided user_ids are cohort members
    for uid in body.user_ids:
        result = await db.execute(
            select(CohortMember).where(
                CohortMember.cohort_id == team.activity.cohort_id,
                CohortMember.user_id == uid,
                CohortMember.is_archived == False,  # noqa: E712
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {uid} is not an active member of this cohort.",
            )

    updated_team = await formation_service.patch_team_members(db, team, body.user_ids)
    await db.commit()
    return _build_team_out(updated_team)
