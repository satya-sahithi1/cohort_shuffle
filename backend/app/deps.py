"""
app/deps.py — FastAPI dependency functions.

get_current_user  — extracts the authenticated user from the JWT in the
                    Authorization header or session cookie.
require_cohort_admin — verifies the current user is an admin of a given cohort.

These are injected into route handlers via Depends().
"""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.cohort import CohortMember
from app.models.user import User

settings = get_settings()
_bearer = HTTPBearer(auto_error=False)

# ── Token extraction ──────────────────────────────────────────────────────────

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    """
    Decode the JWT Bearer token and return the corresponding User row.
    Raises HTTP 401 if the token is missing, invalid, or the user doesn't exist.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise JWTError("missing sub claim")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or user.is_archived:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


# ── Cohort role enforcement ───────────────────────────────────────────────────

async def _get_membership(
    db: AsyncSession,
    cohort_id: uuid.UUID,
    user_id: uuid.UUID,
) -> CohortMember | None:
    result = await db.execute(
        select(CohortMember).where(
            CohortMember.cohort_id == cohort_id,
            CohortMember.user_id == user_id,
            CohortMember.is_archived == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def require_cohort_admin(
    cohort_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency that ensures the current user is an admin of the given cohort.
    Raises 403 otherwise.
    """
    membership = await _get_membership(db, cohort_id, current_user.id)
    if membership is None or membership.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for this cohort.",
        )
    return current_user


async def require_cohort_member(
    cohort_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency that ensures the current user is any member of the cohort.
    Raises 403 if they're not a member (or are archived).
    """
    membership = await _get_membership(db, cohort_id, current_user.id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this cohort.",
        )
    return current_user


# ── Convenient type aliases ───────────────────────────────────────────────────
CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
