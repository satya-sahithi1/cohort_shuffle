"""
services/activity_service.py — Business logic for activities.

All DB access for activity CRUD lives here.
Routers call these functions; they never touch the DB directly.

Functions:
  create_activity   — creates activity + its locks in one transaction
  get_activity      — fetch one activity by id
  list_activities   — fetch all activities for a cohort
  update_activity   — patch an activity (and optionally replace its locks)
  get_registration_count — how many students are registered
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity import Activity, ActivityLock
from app.models.registration import Registration
from app.schemas.activity import ActivityCreate, ActivityUpdate


# ── Helpers ───────────────────────────────────────────────────────────────────

def _apply_deadline_rule(event_at: datetime, deadline_at: datetime) -> datetime:
    """
    Spec §4.1: if the gap between now and event_at is ≤ 20 minutes,
    auto-fix deadline to event_at − 2 minutes (backend enforcement).
    Otherwise use the deadline_at the client sent.
    """
    now = datetime.now(timezone.utc)
    gap_minutes = (event_at - now).total_seconds() / 60
    if gap_minutes <= 20:
        return datetime(
            event_at.year, event_at.month, event_at.day,
            event_at.hour, event_at.minute - 2, event_at.second,
            tzinfo=event_at.tzinfo,
        ) if event_at.minute >= 2 else event_at.replace(second=0, microsecond=0)
    return deadline_at


# ── Service functions ─────────────────────────────────────────────────────────

async def create_activity(
    db: AsyncSession,
    cohort_id: uuid.UUID,
    data: ActivityCreate,
) -> Activity:
    """
    Create a new activity and its lock constraints in a single transaction.
    The activity is immediately visible to all cohort members.
    """
    enforced_deadline = _apply_deadline_rule(data.event_at, data.deadline_at)

    activity = Activity(
        cohort_id=cohort_id,
        name=data.name,
        team_size=data.team_size,
        duration=data.duration,
        event_at=data.event_at,
        deadline_at=enforced_deadline,
        participant_cap=data.participant_cap,
        status="open",
    )
    db.add(activity)
    await db.flush()  # get the id before creating locks

    for lock_in in data.locks:
        db.add(ActivityLock(
            activity_id=activity.id,
            user_a=lock_in.user_a_id,
            user_b=lock_in.user_b_id,
            constraint_type=lock_in.constraint_type,
        ))

    await db.flush()
    # Reload with locks for the response
    return await _load_with_locks(db, activity.id)


async def get_activity(
    db: AsyncSession,
    activity_id: uuid.UUID,
) -> Activity | None:
    """Fetch one activity by id, including its locks. Returns None if not found."""
    return await _load_with_locks(db, activity_id)


async def list_activities(
    db: AsyncSession,
    cohort_id: uuid.UUID,
) -> list[Activity]:
    """
    All activities for a cohort, most recently created first.
    Includes locks eagerly loaded to avoid N+1 queries.
    """
    result = await db.execute(
        select(Activity)
        .where(Activity.cohort_id == cohort_id)
        .options(selectinload(Activity.locks))
        .order_by(Activity.created_at.desc())
    )
    return list(result.scalars().all())


async def update_activity(
    db: AsyncSession,
    activity: Activity,
    data: ActivityUpdate,
) -> Activity:
    """
    Apply a partial update to an activity.
    If `data.locks` is not None, it replaces the entire lock set atomically.
    Only admins should call this; the router enforces that.
    """
    if data.name is not None:
        activity.name = data.name
    if data.team_size is not None:
        activity.team_size = data.team_size
    if data.duration is not None:
        activity.duration = data.duration
    if data.event_at is not None:
        activity.event_at = data.event_at
    if data.deadline_at is not None:
        activity.deadline_at = _apply_deadline_rule(
            activity.event_at, data.deadline_at
        )
    if data.participant_cap is not None:
        activity.participant_cap = data.participant_cap

    # Replace locks if the caller provided them (even as an empty list)
    if data.locks is not None:
        for old_lock in list(activity.locks):
            await db.delete(old_lock)
        await db.flush()
        for lock_in in data.locks:
            db.add(ActivityLock(
                activity_id=activity.id,
                user_a=lock_in.user_a_id,
                user_b=lock_in.user_b_id,
                constraint_type=lock_in.constraint_type,
            ))

    db.add(activity)
    await db.flush()
    return await _load_with_locks(db, activity.id)


async def get_registration_count(
    db: AsyncSession,
    activity_id: uuid.UUID,
) -> int:
    """Count how many students are registered for an activity."""
    result = await db.execute(
        select(func.count(Registration.id)).where(
            Registration.activity_id == activity_id
        )
    )
    return result.scalar_one()


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _load_with_locks(
    db: AsyncSession, activity_id: uuid.UUID
) -> Activity | None:
    result = await db.execute(
        select(Activity)
        .where(Activity.id == activity_id)
        .options(selectinload(Activity.locks))
    )
    return result.scalar_one_or_none()
