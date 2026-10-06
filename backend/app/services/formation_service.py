"""
services/formation_service.py — Team formation business logic.

Entry points:
  run(db, activity_id, triggered_by)
      Full formation pipeline:
        1. Idempotency guard — set status='forming' atomically
        2. Load registered students
        3. Build pair history from all previous team_members rows
        4. Build Lock objects from activity_locks
        5. Call algorithm engine.form_teams()
        6. Persist teams + team_members in one transaction
        7. Write FormationLog
        8. Update activity status → 'formed'

  get_teams(db, activity_id)
      Fetch teams for the latest formation run of an activity.

  get_user_team_history(db, user_id)
      All activities the user was placed in a team, newest first.

  patch_team_members(db, team_id, user_ids)
      Replace the members of a team (manual admin edit).

The formation service is the only code that calls the algorithm;
routers never import algorithm/ directly.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from itertools import combinations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.algorithm.engine import Lock, form_teams
from app.algorithm.scorer import PairHistory
from app.models.activity import Activity
from app.models.registration import Registration
from app.models.team import FormationLog, Team, TeamMember
from app.models.user import User


# ── Errors ────────────────────────────────────────────────────────────────────

class FormationError(Exception):
    """Raised when formation cannot proceed. Message is user-facing."""


# ── Main formation pipeline ───────────────────────────────────────────────────

async def run(
    db: AsyncSession,
    activity_id: uuid.UUID,
    triggered_by: uuid.UUID | None = None,
) -> FormationLog:
    """
    Run team formation for an activity.

    Args:
        db:           async DB session (caller must NOT commit — we commit here)
        activity_id:  UUID of the activity to form teams for
        triggered_by: UUID of the admin who triggered it manually; None = scheduler

    Returns the FormationLog row that was written.

    Raises FormationError if:
      - activity not found
      - activity is already forming/formed
      - no registrations
      - algorithm returns unsatisfied locks (reported to caller)
    """
    # ── 1. Load activity and idempotency guard ────────────────────────────
    result = await db.execute(
        select(Activity)
        .where(Activity.id == activity_id)
        .options(selectinload(Activity.locks))
    )
    activity = result.scalar_one_or_none()
    if activity is None:
        raise FormationError(f"Activity {activity_id} not found.")

    if activity.status == "forming":
        raise FormationError("Formation is already in progress for this activity.")
    if activity.status == "formed":
        # Re-run is allowed — teams from the previous run stay in DB tagged
        # with their run number; a new set is written.
        pass
    if activity.status == "open":
        # Shouldn't normally happen (deadline job closes first), but be safe.
        activity.status = "closed"

    # Atomically claim the 'forming' slot so concurrent calls are blocked
    activity.status = "forming"
    db.add(activity)
    await db.flush()

    try:
        log = await _do_formation(db, activity, triggered_by)
    except Exception:
        # Roll back status to 'closed' so the admin can retry
        activity.status = "closed"
        db.add(activity)
        await db.flush()
        raise

    return log


async def _do_formation(
    db: AsyncSession,
    activity: Activity,
    triggered_by: uuid.UUID | None,
) -> FormationLog:
    """Inner formation logic — called with activity already in 'forming' state."""

    activity_id = activity.id

    # ── 2. Load registered students ───────────────────────────────────────
    reg_result = await db.execute(
        select(Registration)
        .where(Registration.activity_id == activity_id)
        .options(joinedload(Registration.user))
    )
    registrations = reg_result.scalars().all()

    if not registrations:
        raise FormationError("No students are registered for this activity.")

    student_ids = [str(r.user_id) for r in registrations]

    # ── 3. Build pair history from all previous team_members ──────────────
    history = await _build_pair_history(db, activity_id, student_ids)

    # ── 4. Build Lock objects from activity_locks ─────────────────────────
    algo_locks: list[Lock] = [
        Lock(
            student_a=str(lock.user_a),
            student_b=str(lock.user_b),
            constraint_type=lock.constraint_type,
        )
        for lock in activity.locks
    ]

    # ── 5. Run the algorithm ──────────────────────────────────────────────
    result = form_teams(
        students=student_ids,
        team_size=activity.team_size,
        history=history,
        locks=algo_locks,
        time_limit=2.0,
    )

    if not result.teams and result.unsatisfied_locks:
        activity.status = "closed"
        raise FormationError(
            "Formation aborted: lock constraints cannot be satisfied. "
            "Please review the activity locks and try again."
        )

    # ── 6. Determine run number ───────────────────────────────────────────
    run_number = activity.formation_run_count + 1
    activity.formation_run_count = run_number

    # ── 7. Write teams + team_members ────────────────────────────────────
    for team_number, team_student_ids in enumerate(result.teams, start=1):
        team = Team(
            activity_id=activity_id,
            team_number=team_number,
            formation_run=run_number,
        )
        db.add(team)
        await db.flush()  # get team.id

        for sid in team_student_ids:
            db.add(TeamMember(
                team_id=team.id,
                user_id=uuid.UUID(sid),
            ))

    await db.flush()

    # ── 8. Write FormationLog ────────────────────────────────────────────
    log = FormationLog(
        activity_id=activity_id,
        run_number=run_number,
        triggered_by=triggered_by,
        score=int(result.score),
        repeat_pairs=result.repeat_pairs,
        saturation=result.saturation,
        random_seed=result.random_seed,
    )
    db.add(log)
    await db.flush()

    # ── 9. Update activity status → 'formed' ─────────────────────────────
    activity.status = "formed"
    db.add(activity)
    await db.commit()

    await db.refresh(log)
    return log


# ── Pair history builder ──────────────────────────────────────────────────────

async def _build_pair_history(
    db: AsyncSession,
    current_activity_id: uuid.UUID,
    student_ids: list[str],
) -> PairHistory:
    """
    Build a sparse PairHistory dict from all previous TeamMember records
    for this cohort's activities.

    Excludes teams from the current activity (in case this is a re-run)
    so we don't count the about-to-be-replaced run in the history.

    History entry: (a, b) → (count, days_since_last)
    """
    student_set = set(student_ids)

    # Load teams for the same cohort activity — join through activities table
    # to scope by cohort. We exclude the current activity for re-run safety.
    stmt = (
        select(Team)
        .join(Activity, Team.activity_id == Activity.id)
        .where(
            Team.activity_id != current_activity_id,
            Activity.cohort_id == select(Activity.cohort_id)
            .where(Activity.id == current_activity_id)
            .scalar_subquery(),
        )
        .options(
            selectinload(Team.members),
            joinedload(Team.activity),
        )
    )
    result = await db.execute(stmt)
    past_teams = result.scalars().all()

    now = datetime.now(timezone.utc)
    history: PairHistory = {}

    for team in past_teams:
        members_in_team = [str(m.user_id) for m in team.members if str(m.user_id) in student_set]
        if len(members_in_team) < 2:
            continue

        event_at = team.activity.event_at
        if event_at.tzinfo is None:
            event_at = event_at.replace(tzinfo=timezone.utc)
        days_ago = max(0, int((now - event_at).days))

        for a, b in combinations(sorted(members_in_team), 2):
            key = (a, b)
            if key in history:
                old_count, old_days = history[key]
                # keep the most recent days_ago (smaller = more recent)
                history[key] = (old_count + 1, min(old_days, days_ago))
            else:
                history[key] = (1, days_ago)

    return history


# ── Read helpers ──────────────────────────────────────────────────────────────

async def get_teams(
    db: AsyncSession,
    activity_id: uuid.UUID,
) -> list[Team]:
    """
    Fetch teams for the latest formation run of an activity.
    Includes members with their User info.
    """
    # Get the current run number from the activity
    act_result = await db.execute(
        select(Activity.formation_run_count).where(Activity.id == activity_id)
    )
    run_count = act_result.scalar_one_or_none()
    if run_count is None or run_count == 0:
        return []

    result = await db.execute(
        select(Team)
        .where(
            Team.activity_id == activity_id,
            Team.formation_run == run_count,
        )
        .options(
            selectinload(Team.members).joinedload(TeamMember.user)
        )
        .order_by(Team.team_number.asc())
    )
    return list(result.scalars().all())


async def get_formation_logs(
    db: AsyncSession,
    activity_id: uuid.UUID,
) -> list[FormationLog]:
    """Return all formation logs for an activity, newest first."""
    result = await db.execute(
        select(FormationLog)
        .where(FormationLog.activity_id == activity_id)
        .order_by(FormationLog.created_at.desc())
    )
    return list(result.scalars().all())


async def get_user_team_history(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[Team]:
    """
    All teams the user was placed in, newest activity first.
    Includes teammates and activity info.
    """
    result = await db.execute(
        select(Team)
        .join(TeamMember, Team.id == TeamMember.team_id)
        .where(TeamMember.user_id == user_id)
        .options(
            selectinload(Team.members).joinedload(TeamMember.user),
            joinedload(Team.activity),
        )
        .order_by(Team.activity_id)  # will re-sort in Python by event_at
    )
    teams = list(result.scalars().unique().all())
    # Sort by activity event_at descending
    teams.sort(
        key=lambda t: t.activity.event_at if t.activity.event_at else datetime.min,
        reverse=True,
    )
    return teams


async def get_team_by_id(
    db: AsyncSession,
    team_id: uuid.UUID,
) -> Team | None:
    """Fetch a single team by id, with members and their users loaded."""
    result = await db.execute(
        select(Team)
        .where(Team.id == team_id)
        .options(
            selectinload(Team.members).joinedload(TeamMember.user),
            joinedload(Team.activity),
        )
    )
    return result.scalar_one_or_none()


# ── Admin team edit ───────────────────────────────────────────────────────────

async def patch_team_members(
    db: AsyncSession,
    team: Team,
    new_user_ids: list[uuid.UUID],
) -> Team:
    """
    Replace the members of a team with the provided list.
    Does not touch other teams in the same activity.

    Caller is responsible for commit().
    """
    # Delete existing members
    for member in list(team.members):
        await db.delete(member)
    await db.flush()

    # Insert new members
    for uid in new_user_ids:
        db.add(TeamMember(team_id=team.id, user_id=uid))
    await db.flush()

    # Reload
    result = await db.execute(
        select(Team)
        .where(Team.id == team.id)
        .options(
            selectinload(Team.members).joinedload(TeamMember.user)
        )
    )
    return result.scalar_one()
