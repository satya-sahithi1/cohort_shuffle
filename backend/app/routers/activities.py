"""
routers/activities.py — Activity endpoints.

POST   /cohorts/{cohort_id}/activities       create activity (admin)
GET    /cohorts/{cohort_id}/activities       list activities (any cohort member)
GET    /activities/{activity_id}             activity detail (any cohort member)
PATCH  /activities/{activity_id}             edit activity (admin)

The cohort-scoped routes live on a router with prefix="/cohorts".
The activity-scoped routes live on a router with prefix="/activities".
Both are registered in main.py.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUser, DbSession, get_current_user
from app.models.activity import Activity, ActivityLock
from app.models.cohort import Cohort, CohortMember
from app.schemas.activity import ActivityCreate, ActivityLockOut, ActivityOut, ActivityUpdate
from app.services import activity_service, registration_service
# Two routers — one nested under /cohorts, one standalone under /activities
cohort_router = APIRouter()
activity_router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_cohort_or_404(db: AsyncSession, cohort_id: uuid.UUID) -> Cohort:
    result = await db.execute(select(Cohort).where(Cohort.id == cohort_id))
    cohort = result.scalar_one_or_none()
    if cohort is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")
    return cohort


async def _require_member(
    db: AsyncSession, cohort_id: uuid.UUID, user_id: uuid.UUID
) -> CohortMember:
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


async def _require_admin(
    db: AsyncSession, cohort_id: uuid.UUID, user_id: uuid.UUID
) -> CohortMember:
    member = await _require_member(db, cohort_id, user_id)
    if member.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return member


async def _get_activity_or_404(
    db: AsyncSession, activity_id: uuid.UUID
) -> Activity:
    activity = await activity_service.get_activity(db, activity_id)
    if activity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )
    return activity


def _build_activity_out(activity: Activity, registration_count: int) -> ActivityOut:
    """Convert an Activity ORM object to the ActivityOut response schema."""
    locks_out = [
        ActivityLockOut(
            id=lock.id,
            user_a_id=lock.user_a,
            user_b_id=lock.user_b,
            constraint_type=lock.constraint_type,
        )
        for lock in activity.locks
    ]
    return ActivityOut(
        id=activity.id,
        cohort_id=activity.cohort_id,
        name=activity.name,
        team_size=activity.team_size,
        duration=activity.duration,
        event_at=activity.event_at,
        deadline_at=activity.deadline_at,
        participant_cap=activity.participant_cap,
        status=activity.status,
        registration_count=registration_count,
        locks=locks_out,
        created_at=activity.created_at,
        formation_run_count=activity.formation_run_count,
    )


# ── POST /cohorts/{cohort_id}/activities ─────────────────────────────────────

@cohort_router.post(
    "/{cohort_id}/activities",
    response_model=ActivityOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new activity",
)
async def create_activity(
    cohort_id: uuid.UUID,
    body: ActivityCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Admin creates a new activity for a cohort. Immediately visible to all members."""
    await _get_cohort_or_404(db, cohort_id)
    await _require_admin(db, cohort_id, current_user.id)

    activity = await activity_service.create_activity(db, cohort_id, body)
    count = await registration_service.get_registration_count(db, activity.id)

    # Schedule the deadline job now that we have the activity id
    from app.main import schedule_deadline_job  # local import avoids circular
    schedule_deadline_job(activity.id, activity.deadline_at)

    return _build_activity_out(activity, count)


# ── GET /cohorts/{cohort_id}/activities ───────────────────────────────────────

@cohort_router.get(
    "/{cohort_id}/activities",
    response_model=list[ActivityOut],
    summary="List all activities in a cohort",
)
async def list_activities(
    cohort_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """Any cohort member can list activities."""
    await _get_cohort_or_404(db, cohort_id)
    await _require_member(db, cohort_id, current_user.id)

    activities = await activity_service.list_activities(db, cohort_id)

    result = []
    for a in activities:
        count = await registration_service.get_registration_count(db, a.id)
        result.append(_build_activity_out(a, count))
    return result


# ── GET /activities/{activity_id} ─────────────────────────────────────────────

@activity_router.get(
    "/{activity_id}",
    response_model=ActivityOut,
    summary="Get activity details",
)
async def get_activity(
    activity_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """Any cohort member can view an activity."""
    activity = await _get_activity_or_404(db, activity_id)
    # Verify the user is a member of the activity's cohort
    await _require_member(db, activity.cohort_id, current_user.id)

    count = await registration_service.get_registration_count(db, activity_id)
    return _build_activity_out(activity, count)


# ── PATCH /activities/{activity_id} ───────────────────────────────────────────

@activity_router.patch(
    "/{activity_id}",
    response_model=ActivityOut,
    summary="Edit an activity",
)
async def update_activity(
    activity_id: uuid.UUID,
    body: ActivityUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Admin edits an activity. Only allowed while status is 'open'."""
    activity = await _get_activity_or_404(db, activity_id)
    await _require_admin(db, activity.cohort_id, current_user.id)

    if activity.status == "formed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot edit an activity after teams have been formed.",
        )

    updated = await activity_service.update_activity(db, activity, body)
    count = await registration_service.get_registration_count(db, updated.id)
    return _build_activity_out(updated, count)
