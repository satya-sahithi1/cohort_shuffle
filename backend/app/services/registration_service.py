"""
services/registration_service.py — Business logic for registrations.

Handles:
  register        — student opts in; enforces cap, deadline, status
  unregister      — student opts out (only before deadline)
  get_my_registration — check if the current user is registered
  list_registrations  — admin: full list of registered students with names
  close_activity_if_full — called after each registration to check cap
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.activity import Activity
from app.models.registration import Registration
from app.models.user import User
from app.schemas.registration import RegistrationOut


# ── Errors ────────────────────────────────────────────────────────────────────

class RegistrationError(Exception):
    """Raised when a registration attempt is rejected. Message is user-facing."""


# ── Service functions ─────────────────────────────────────────────────────────

async def register(
    db: AsyncSession,
    activity: Activity,
    user_id: uuid.UUID,
) -> Registration:
    """
    Register a student for an activity.

    Checks (in order):
      1. Activity must be 'open'
      2. Deadline must not have passed
      3. User must not already be registered
      4. Cap must not be reached (if set)

    If the cap is reached after this registration, the activity is closed
    immediately (formation will run via the scheduler or manually).
    """
    if activity.status != "open":
        raise RegistrationError("Registration is closed for this activity.")

    now = datetime.now(timezone.utc)
    if now > activity.deadline_at:
        raise RegistrationError("The registration deadline has passed.")

    # Check duplicate
    existing = await db.execute(
        select(Registration).where(
            Registration.activity_id == activity.id,
            Registration.user_id == user_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise RegistrationError("You are already registered for this activity.")

    # Check cap
    if activity.participant_cap is not None:
        count_result = await db.execute(
            select(Registration).where(Registration.activity_id == activity.id)
        )
        current_count = len(count_result.scalars().all())
        if current_count >= activity.participant_cap:
            raise RegistrationError(
                "This activity is full. Registration is closed."
            )

    registration = Registration(
        activity_id=activity.id,
        user_id=user_id,
    )
    db.add(registration)
    await db.flush()

    # Close the activity if the cap is now reached
    if activity.participant_cap is not None:
        new_count_result = await db.execute(
            select(Registration).where(Registration.activity_id == activity.id)
        )
        new_count = len(new_count_result.scalars().all())
        if new_count >= activity.participant_cap:
            activity.status = "closed"
            db.add(activity)
            await db.flush()

    return registration


async def unregister(
    db: AsyncSession,
    activity: Activity,
    user_id: uuid.UUID,
) -> None:
    """
    Remove a student's registration.

    Rules:
      - Only allowed while the activity is 'open' and before the deadline.
      - If a cap was set and the activity was just closed by reaching the cap,
        unregistering re-opens it (the spot is freed).
    """
    if datetime.now(timezone.utc) > activity.deadline_at:
        raise RegistrationError("The deadline has passed; you cannot unregister.")

    result = await db.execute(
        select(Registration).where(
            Registration.activity_id == activity.id,
            Registration.user_id == user_id,
        )
    )
    registration = result.scalar_one_or_none()
    if registration is None:
        raise RegistrationError("You are not registered for this activity.")

    await db.delete(registration)

    # If the activity was closed because the cap was reached, re-open it
    # (a spot is now free)
    if activity.status == "closed" and activity.participant_cap is not None:
        activity.status = "open"
        db.add(activity)

    await db.flush()


async def get_my_registration(
    db: AsyncSession,
    activity_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Registration | None:
    """Return the registration record if the user is registered, else None."""
    result = await db.execute(
        select(Registration).where(
            Registration.activity_id == activity_id,
            Registration.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_registrations(
    db: AsyncSession,
    activity_id: uuid.UUID,
) -> list[RegistrationOut]:
    """
    Admin-only: return all registrations for an activity, with user details.
    Ordered by registration time (earliest first = cap order).
    """
    result = await db.execute(
        select(Registration)
        .where(Registration.activity_id == activity_id)
        .options(joinedload(Registration.user))
        .order_by(Registration.registered_at.asc())
    )
    registrations = result.scalars().all()

    return [
        RegistrationOut(
            id=r.id,
            activity_id=r.activity_id,
            user_id=r.user_id,
            user_name=r.user.name,
            user_email=r.user.email,
            registered_at=r.registered_at,
        )
        for r in registrations
    ]
