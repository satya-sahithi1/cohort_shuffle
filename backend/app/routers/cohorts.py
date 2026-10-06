"""
routers/cohorts.py — Cohort endpoints.

POST   /cohorts                            create cohort (any auth'd user becomes admin)
GET    /cohorts/eligible                   cohorts the caller can join
GET    /cohorts/join-link?token=...        resolve a join token → cohort info
GET    /cohorts/{cohort_id}                cohort details
GET    /cohorts/{cohort_id}/members        list members (any member)
POST   /cohorts/{cohort_id}/members        add member by email (admin)
PATCH  /cohorts/{cohort_id}/members/{uid}  archive/unarchive/role-change (admin)
POST   /cohorts/{cohort_id}/join           self-join via domain eligibility
GET    /cohorts/{cohort_id}/join-link      generate a shareable join link (admin)

Note: the two routes without a cohort_id path param (eligible, join-link?token)
must be declared BEFORE /{cohort_id} to avoid FastAPI matching "eligible" or
"join-link" as a UUID and returning a 422.
"""

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import CurrentUser, DbSession
from app.models.cohort import CohortMember
from app.schemas.cohort import (
    CohortCreate,
    CohortOut,
    JoinLinkOut,
    MemberAdd,
    MemberOut,
    MemberPatch,
)
from app.services import cohort_service

router = APIRouter()
settings = get_settings()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_cohort_or_404(db: AsyncSession, cohort_id: uuid.UUID):
    cohort = await cohort_service.get_cohort(db, cohort_id)
    if cohort is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")
    return cohort


async def _require_member(
    db: AsyncSession, cohort_id: uuid.UUID, user_id: uuid.UUID
) -> CohortMember:
    m = await cohort_service.get_membership(db, cohort_id, user_id)
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this cohort.",
        )
    return m


async def _require_admin(
    db: AsyncSession, cohort_id: uuid.UUID, user_id: uuid.UUID
) -> CohortMember:
    m = await _require_member(db, cohort_id, user_id)
    if m.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for this cohort.",
        )
    return m


def _cohort_out(cohort, role: str) -> CohortOut:
    return CohortOut(
        id=cohort.id,
        name=cohort.name,
        allowed_domain=cohort.allowed_domain,
        role=role,
        created_at=cohort.created_at,
    )


def _member_out(membership: CohortMember) -> MemberOut:
    return MemberOut(
        user_id=membership.user_id,
        name=membership.user.name,
        email=membership.user.email,
        role=membership.role,
        is_archived=membership.is_archived,
        joined_at=membership.joined_at,
    )


# ── POST /cohorts ─────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=CohortOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new cohort",
)
async def create_cohort(
    body: CohortCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Any authenticated user can create a cohort and becomes its admin."""
    cohort, membership = await cohort_service.create_cohort(db, body, current_user)
    await db.commit()
    return _cohort_out(cohort, membership.role)


# ── GET /cohorts/eligible ─────────────────────────────────────────────────────
# IMPORTANT: must be declared before /{cohort_id} so FastAPI doesn't try to
# parse "eligible" as a UUID.

@router.get(
    "/eligible",
    response_model=list[CohortOut],
    summary="Cohorts the current user is eligible to join",
)
async def eligible_cohorts(
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Returns cohorts the caller hasn't joined yet but is eligible for.
    Eligibility: cohort has no domain restriction, or the user's email
    domain matches cohort.allowed_domain.
    """
    cohorts = await cohort_service.get_eligible_cohorts(db, current_user)
    # eligible cohorts — user has no role in them yet, show as student
    return [_cohort_out(c, "student") for c in cohorts]


# ── GET /cohorts/join-link?token=... ──────────────────────────────────────────
# Also before /{cohort_id} for the same reason.

@router.get(
    "/join-link",
    response_model=CohortOut,
    summary="Resolve a join-link token to cohort info",
)
async def resolve_join_link(
    token: str = Query(..., description="JWT join token from the share link"),
    current_user: CurrentUser = None,
    db: DbSession = None,
):
    """
    Validates a join-link token and returns the cohort it points to.
    Used by the frontend join page to show the cohort name before joining.
    """
    cohort = await cohort_service.validate_join_token(db, token)
    if cohort is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Join link is invalid or has expired.",
        )
    return _cohort_out(cohort, "student")


# ── GET /cohorts/{cohort_id} ──────────────────────────────────────────────────

@router.get(
    "/{cohort_id}",
    response_model=CohortOut,
    summary="Get cohort details",
)
async def get_cohort(
    cohort_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """Any cohort member can view cohort details."""
    cohort = await _get_cohort_or_404(db, cohort_id)
    membership = await _require_member(db, cohort_id, current_user.id)
    return _cohort_out(cohort, membership.role)


# ── GET /cohorts/{cohort_id}/members ─────────────────────────────────────────

@router.get(
    "/{cohort_id}/members",
    response_model=list[MemberOut],
    summary="List cohort members",
)
async def list_members(
    cohort_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    include_archived: bool = Query(False, description="Include archived members"),
):
    """Any active cohort member can list members."""
    await _get_cohort_or_404(db, cohort_id)
    await _require_member(db, cohort_id, current_user.id)

    pairs = await cohort_service.list_members(db, cohort_id, include_archived)
    return [_member_out(m) for m, _ in pairs]


# ── POST /cohorts/{cohort_id}/members ─────────────────────────────────────────

@router.post(
    "/{cohort_id}/members",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member by email (admin)",
)
async def add_member(
    cohort_id: uuid.UUID,
    body: MemberAdd,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Admin adds a student by email.
    Creates a placeholder User if they haven't signed in yet.
    """
    cohort = await _get_cohort_or_404(db, cohort_id)
    await _require_admin(db, cohort_id, current_user.id)

    try:
        membership = await cohort_service.add_member(db, cohort, body)
    except cohort_service.CohortError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    await db.commit()
    # Reload with user relationship
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from app.models.cohort import CohortMember as CM
    result = await db.execute(
        select(CM)
        .where(CM.cohort_id == cohort_id, CM.user_id == membership.user_id)
        .options(joinedload(CM.user))
    )
    membership = result.scalar_one()
    return _member_out(membership)


# ── PATCH /cohorts/{cohort_id}/members/{user_id} ──────────────────────────────

@router.patch(
    "/{cohort_id}/members/{user_id}",
    response_model=MemberOut,
    summary="Archive/unarchive a member or change role (admin)",
)
async def patch_member(
    cohort_id: uuid.UUID,
    user_id: uuid.UUID,
    body: MemberPatch,
    current_user: CurrentUser,
    db: DbSession,
):
    """Admin can archive/unarchive members or change their role."""
    await _get_cohort_or_404(db, cohort_id)
    await _require_admin(db, cohort_id, current_user.id)

    # Can't modify yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot modify your own membership.",
        )

    membership = await cohort_service.get_membership(
        db, cohort_id, user_id, include_archived=True
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this cohort.",
        )

    # Guard: don't allow archiving the last admin
    if body.is_archived and membership.role == "admin":
        from sqlalchemy import select, func
        from app.models.cohort import CohortMember as CM
        result = await db.execute(
            select(func.count()).where(
                CM.cohort_id == cohort_id,
                CM.role == "admin",
                CM.is_archived == False,  # noqa: E712
            )
        )
        admin_count = result.scalar_one()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot archive the last admin of a cohort.",
            )

    updated = await cohort_service.patch_member(db, membership, body)
    await db.commit()

    # Reload with user relationship for the response
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from app.models.cohort import CohortMember as CM
    result = await db.execute(
        select(CM)
        .where(CM.cohort_id == cohort_id, CM.user_id == user_id)
        .options(joinedload(CM.user))
    )
    updated = result.scalar_one()
    return _member_out(updated)


# ── POST /cohorts/{cohort_id}/join ────────────────────────────────────────────

@router.post(
    "/{cohort_id}/join",
    response_model=CohortOut,
    status_code=status.HTTP_200_OK,
    summary="Join a cohort",
)
async def join_cohort(
    cohort_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Student self-joins a cohort. Domain restriction is enforced.
    Also used after validating a join-link token.
    """
    cohort = await _get_cohort_or_404(db, cohort_id)

    try:
        membership = await cohort_service.join_cohort(db, cohort, current_user)
    except cohort_service.CohortError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    await db.commit()
    return _cohort_out(cohort, membership.role)


# ── GET /cohorts/{cohort_id}/join-link ────────────────────────────────────────

@router.get(
    "/{cohort_id}/join-link",
    response_model=JoinLinkOut,
    summary="Generate a shareable join link (admin)",
)
async def get_join_link(
    cohort_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    """
    Admin generates a 72-hour join link for sharing with students.
    Each call generates a fresh token.
    """
    await _get_cohort_or_404(db, cohort_id)
    await _require_admin(db, cohort_id, current_user.id)

    token = cohort_service.generate_join_token(cohort_id)
    # Build the full URL — frontend join page handles the ?token= param
    frontend_origin = settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"
    url = f"{frontend_origin}/join?token={token}"

    return JoinLinkOut(token=token, url=url)
