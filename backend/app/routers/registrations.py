"""
routers/registrations.py — Registration endpoints.

POST   /activities/{activity_id}/register      student registers
DELETE /activities/{activity_id}/register      student unregisters
GET    /activities/{activity_id}/register      check own registration status
GET    /activities/{activity_id}/registrations list all registrations (admin only)
"""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models.activity import Activity
from app.models.cohort import CohortMember
from app.schemas.registration import MyRegistrationOut, RegistrationOut
from app.services import registration_service

router = APIRouter()


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )
    return activity


async def _require_member(db, cohort_id: uuid.UUID, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(CohortMember).where(
            CohortMember.cohort_id == cohort_id,
            CohortMember.user_id == user_id,
            CohortMember.is_archived == False,  # noqa: E712
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this cohort.",
        )


async def _require_admin(db, cohort_id: uuid.UUID, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(CohortMember).where(
            CohortMember.cohort_id == cohort_id,
            CohortMember.user_id == user_id,
            CohortMember.is_archived == False,  # noqa: E712
        )
    )
    member = result.scalar_one_or_none()
    if member is None or member.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )


# ── POST /activities/{activity_id}/register ───────────────────────────────────

@router.post(
    "/{activity_id}/register",
    status_code=status.HTTP_201_CREATED,
    response_model=MyRegistrationOut,
    summary="Register for an activity",
)
async def register(
    activity_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Student registers for an activity.
    Enforces: activity must be open, deadline not passed, not already
    registered, cap not reached.
    If the cap is hit, the activity automatically transitions to 'closed'.
    """
    activity = await _get_activity_or_404(db, activity_id)
    await _require_member(db, activity.cohort_id, current_user.id)

    try:
        reg = await registration_service.register(db, activity, current_user.id)
    except registration_service.RegistrationError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        )

    return MyRegistrationOut(registered=True, registered_at=reg.registered_at)


# ── DELETE /activities/{activity_id}/register ─────────────────────────────────

@router.delete(
    "/{activity_id}/register",
    status_code=status.HTTP_200_OK,
    response_model=MyRegistrationOut,
    summary="Unregister from an activity",
)
async def unregister(
    activity_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Student withdraws their registration.
    Only allowed before the deadline.
    If the activity was closed due to hitting the cap, it re-opens.
    """
    activity = await _get_activity_or_404(db, activity_id)
    await _require_member(db, activity.cohort_id, current_user.id)

    try:
        await registration_service.unregister(db, activity, current_user.id)
    except registration_service.RegistrationError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(e)
        )

    return MyRegistrationOut(registered=False)


# ── GET /activities/{activity_id}/register ────────────────────────────────────

@router.get(
    "/{activity_id}/register",
    response_model=MyRegistrationOut,
    summary="Check own registration status",
)
async def my_registration(
    activity_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """Returns whether the current user is registered for the activity."""
    activity = await _get_activity_or_404(db, activity_id)
    await _require_member(db, activity.cohort_id, current_user.id)

    reg = await registration_service.get_my_registration(
        db, activity_id, current_user.id
    )
    return MyRegistrationOut(
        registered=reg is not None,
        registered_at=reg.registered_at if reg else None,
    )


# ── GET /activities/{activity_id}/registrations ───────────────────────────────

@router.get(
    "/{activity_id}/registrations",
    response_model=list[RegistrationOut],
    summary="List registered students (admin only)",
)
async def list_registrations(
    activity_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """Admin only: full list of registered students with names and timestamps."""
    activity = await _get_activity_or_404(db, activity_id)
    await _require_admin(db, activity.cohort_id, current_user.id)

    return await registration_service.list_registrations(db, activity_id)
