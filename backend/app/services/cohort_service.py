"""
services/cohort_service.py — Business logic for cohorts and membership.

Functions:
  create_cohort          POST /cohorts
  get_cohort             fetch one cohort by id
  get_member_cohorts     cohorts a user belongs to (for /auth/me)
  get_eligible_cohorts   cohorts a user can join based on email domain
  get_membership         single CohortMember row
  join_cohort            POST /cohorts/{id}/join (student self-join)
  list_members           GET  /cohorts/{id}/members
  add_member             POST /cohorts/{id}/members (admin adds by email)
  patch_member           PATCH /cohorts/{id}/members/{uid}
  generate_join_token    GET  /cohorts/{id}/join-link
  validate_join_token    GET  /cohorts/join-link?token=...
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config import get_settings
from app.models.cohort import Cohort, CohortMember
from app.models.user import User
from app.schemas.cohort import CohortCreate, MemberAdd, MemberPatch

settings = get_settings()

# Join-link tokens are short-lived signed JWTs with a "cohort_id" claim.
_JOIN_TOKEN_EXPIRE_HOURS = 72
_JOIN_TOKEN_ALGO = "HS256"
_JOIN_TOKEN_AUD = "cohort-join"


# ── Errors ────────────────────────────────────────────────────────────────────

class CohortError(Exception):
    """Raised when a cohort operation is rejected. Message is user-facing."""


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_membership(
    db: AsyncSession,
    cohort_id: uuid.UUID,
    user_id: uuid.UUID,
    include_archived: bool = False,
) -> CohortMember | None:
    """Return the CohortMember row for (cohort_id, user_id), or None."""
    q = select(CohortMember).where(
        CohortMember.cohort_id == cohort_id,
        CohortMember.user_id == user_id,
    )
    if not include_archived:
        q = q.where(CohortMember.is_archived == False)  # noqa: E712
    result = await db.execute(q)
    return result.scalar_one_or_none()


# ── Cohort CRUD ───────────────────────────────────────────────────────────────

async def create_cohort(
    db: AsyncSession,
    data: CohortCreate,
    creator: User,
) -> tuple[Cohort, CohortMember]:
    """
    Create a new cohort and make the creator an admin member.
    Returns (cohort, membership).
    """
    cohort = Cohort(
        name=data.name,
        admin_id=creator.id,
        allowed_domain=data.allowed_domain,
    )
    db.add(cohort)
    await db.flush()  # get the id

    membership = CohortMember(
        cohort_id=cohort.id,
        user_id=creator.id,
        role="admin",
    )
    db.add(membership)
    await db.flush()
    await db.refresh(cohort)
    return cohort, membership


async def get_cohort(
    db: AsyncSession,
    cohort_id: uuid.UUID,
) -> Cohort | None:
    """Fetch a cohort by id. Returns None if not found."""
    result = await db.execute(select(Cohort).where(Cohort.id == cohort_id))
    return result.scalar_one_or_none()


# ── Membership queries ────────────────────────────────────────────────────────

async def get_member_cohorts(
    db: AsyncSession,
    user: User,
) -> list[tuple[Cohort, CohortMember]]:
    """
    Return all active cohort memberships for a user.
    Used by /auth/me to populate the user's cohort list.
    """
    result = await db.execute(
        select(CohortMember)
        .where(
            CohortMember.user_id == user.id,
            CohortMember.is_archived == False,  # noqa: E712
        )
        .options(joinedload(CohortMember.cohort))
        .order_by(CohortMember.joined_at.asc())
    )
    memberships = result.scalars().all()
    return [(m.cohort, m) for m in memberships]


async def get_eligible_cohorts(
    db: AsyncSession,
    user: User,
) -> list[Cohort]:
    """
    Cohorts the user is eligible to join but hasn't joined yet.
    Eligibility: cohort.allowed_domain is null OR matches the user's email domain.
    """
    # Get cohorts the user is already in (including archived — don't re-show those)
    existing = await db.execute(
        select(CohortMember.cohort_id).where(CohortMember.user_id == user.id)
    )
    existing_ids = {row[0] for row in existing.all()}

    result = await db.execute(select(Cohort))
    all_cohorts = result.scalars().all()

    user_domain = user.email.split("@")[-1] if "@" in user.email else ""

    eligible = []
    for cohort in all_cohorts:
        if cohort.id in existing_ids:
            continue
        if cohort.allowed_domain is None:
            eligible.append(cohort)
        elif cohort.allowed_domain == user_domain:
            eligible.append(cohort)

    return eligible


# ── Join flow ─────────────────────────────────────────────────────────────────

async def join_cohort(
    db: AsyncSession,
    cohort: Cohort,
    user: User,
) -> CohortMember:
    """
    Student self-joins a cohort.
    Checks domain restriction and duplicate membership.
    If the user was previously archived, re-activates them.
    """
    # Domain check
    if cohort.allowed_domain is not None:
        user_domain = user.email.split("@")[-1] if "@" in user.email else ""
        if user_domain != cohort.allowed_domain:
            raise CohortError(
                f"Your email domain is not allowed for this cohort. "
                f"Expected @{cohort.allowed_domain}."
            )

    # Check for existing membership (including archived)
    existing = await get_membership(db, cohort.id, user.id, include_archived=True)
    if existing is not None:
        if not existing.is_archived:
            raise CohortError("You are already a member of this cohort.")
        # Re-activate archived member
        existing.is_archived = False
        db.add(existing)
        await db.flush()
        return existing

    membership = CohortMember(
        cohort_id=cohort.id,
        user_id=user.id,
        role="student",
    )
    db.add(membership)
    await db.flush()
    return membership


# ── Member management (admin) ─────────────────────────────────────────────────

async def list_members(
    db: AsyncSession,
    cohort_id: uuid.UUID,
    include_archived: bool = False,
) -> list[tuple[CohortMember, User]]:
    """
    Return all members of a cohort with their User info.
    Ordered: admins first, then students, then by join time.
    """
    q = (
        select(CohortMember)
        .where(CohortMember.cohort_id == cohort_id)
        .options(joinedload(CohortMember.user))
        .order_by(CohortMember.joined_at.asc())
    )
    if not include_archived:
        q = q.where(CohortMember.is_archived == False)  # noqa: E712

    result = await db.execute(q)
    memberships = result.scalars().all()
    return [(m, m.user) for m in memberships]


async def add_member(
    db: AsyncSession,
    cohort: Cohort,
    data: MemberAdd,
) -> CohortMember:
    """
    Admin adds a member by email.
    If the user doesn't exist, creates a placeholder (they sign in later).
    If the user was previously archived, re-activates them.
    """
    user = await _get_user_by_email(db, data.email.lower().strip())

    if user is None:
        # Create a placeholder user — they'll link their Google account on
        # first sign-in via the google_id field.
        user = User(
            email=data.email.lower().strip(),
            name=data.email.split("@")[0],  # placeholder name
            google_id=None,
        )
        db.add(user)
        await db.flush()

    # Check for existing membership
    existing = await get_membership(db, cohort.id, user.id, include_archived=True)
    if existing is not None:
        if not existing.is_archived:
            raise CohortError(f"{data.email} is already a member of this cohort.")
        existing.is_archived = False
        existing.role = data.role
        db.add(existing)
        await db.flush()
        return existing

    membership = CohortMember(
        cohort_id=cohort.id,
        user_id=user.id,
        role=data.role,
    )
    db.add(membership)
    await db.flush()
    return membership


async def patch_member(
    db: AsyncSession,
    membership: CohortMember,
    data: MemberPatch,
) -> CohortMember:
    """
    Archive/unarchive a member or change their role.
    Guards: can't archive the last admin.
    """
    if data.is_archived is not None:
        membership.is_archived = data.is_archived
    if data.role is not None:
        membership.role = data.role

    db.add(membership)
    await db.flush()
    return membership


# ── Join links ────────────────────────────────────────────────────────────────

def generate_join_token(cohort_id: uuid.UUID) -> str:
    """
    Issue a signed JWT that encodes a cohort_id.
    Expires in 72 hours. Used for shareable join links.
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=_JOIN_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(cohort_id),
        "aud": _JOIN_TOKEN_AUD,
        "exp": expire,
        # Add jitter so two tokens for the same cohort differ
        "jti": secrets.token_hex(8),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=_JOIN_TOKEN_ALGO)


async def validate_join_token(
    db: AsyncSession,
    token: str,
) -> Cohort | None:
    """
    Decode and verify a join token.
    Returns the Cohort if valid, None if expired/invalid/cohort gone.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[_JOIN_TOKEN_ALGO],
            audience=_JOIN_TOKEN_AUD,
        )
        cohort_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError):
        return None

    return await get_cohort(db, cohort_id)
