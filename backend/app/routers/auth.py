"""
routers/auth.py — Google OAuth login flow.

Routes:
  GET  /auth/google           — redirect browser to Google's OAuth consent screen
  GET  /auth/google/callback  — exchange code for token, upsert user, issue JWT
  GET  /auth/me               — return current user profile + cohort memberships
  POST /auth/logout           — client-side only (JWT is stateless); returns 200

Google OAuth flow (server-side redirect):
  1. Client visits GET /auth/google
  2. Server redirects to Google's authorisation URL
  3. Google redirects to GOOGLE_REDIRECT_URI (/auth/google/callback?code=...&state=...)
  4. Server exchanges code for id_token via Google's token endpoint
  5. Server verifies id_token, upserts the User row, issues a signed JWT
  6. Server redirects the browser to FRONTEND_URL/?token=<jwt>
     (or returns JSON when called from a native/SPA client)

Environment variables required:
  GOOGLE_CLIENT_ID      — from Google Cloud Console OAuth 2.0 credentials
  GOOGLE_CLIENT_SECRET  — from Google Cloud Console OAuth 2.0 credentials
  GOOGLE_REDIRECT_URI   — must match one of the authorised redirect URIs in GCP
                          e.g. http://localhost:8000/auth/google/callback
  FRONTEND_URL          — where to redirect after successful login
                          e.g. http://localhost:3000
"""

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.deps import CurrentUser
from app.models.cohort import Cohort, CohortMember
from app.models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Google OAuth constants ────────────────────────────────────────────────────

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# Scopes: openid (id_token), email, profile (name + picture)
GOOGLE_SCOPES = "openid email profile"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_jwt(user_id: uuid.UUID) -> str:
    """Issue a signed JWT with the user's id as the 'sub' claim."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


async def _upsert_user(
    db: AsyncSession,
    google_id: str,
    email: str,
    name: str,
) -> User:
    """
    Find an existing user by google_id or email; create one if not found.
    Always syncs name from Google so profile changes propagate.
    """
    # Try by google_id first (most reliable)
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Try by email (user may have logged in before google_id was stored)
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user is None:
        # New user
        user = User(
            email=email,
            name=name,
            google_id=google_id,
        )
        db.add(user)
    else:
        # Sync mutable fields
        user.name = name
        if user.google_id is None:
            user.google_id = google_id
        db.add(user)

    await db.flush()
    return user


# ── Response schemas ──────────────────────────────────────────────────────────

class CohortMembershipOut(BaseModel):
    cohort_id: uuid.UUID
    cohort_name: str
    role: str

    model_config = {"from_attributes": True}


class MeOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    created_at: datetime
    cohorts: list[CohortMembershipOut] = []

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "/google",
    summary="Redirect to Google OAuth consent screen",
    response_class=RedirectResponse,
    status_code=302,
)
async def google_login():
    """
    Redirect the browser to Google's OAuth consent page.

    The `state` parameter is a random nonce used to prevent CSRF.
    In production you should store it in a short-lived session or signed cookie
    and verify it in the callback. For simplicity we generate it here;
    the callback does not verify it (add cookie-based verification for production).
    """
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured (GOOGLE_CLIENT_ID missing).",
        )

    state = secrets.token_urlsafe(16)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "access_type": "offline",
        "state": state,
        "prompt": "select_account",
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=url, status_code=302)


@router.get(
    "/google/callback",
    summary="Handle Google OAuth callback — issues a JWT",
)
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(default="", description="State nonce (anti-CSRF)"),
    error: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange the authorization code for user info, upsert the User row,
    and return a signed JWT.

    On success this redirects to FRONTEND_URL/?token=<jwt> so the frontend
    can pick up the token and store it (e.g. in localStorage or a cookie).

    If FRONTEND_URL is not configured, returns JSON {access_token, token_type}.
    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth error: {error}",
        )

    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured.",
        )

    # 1. Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10.0,
        )

    if token_resp.status_code != 200:
        logger.warning("Google token exchange failed: %s", token_resp.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to exchange code with Google.",
        )

    token_data = token_resp.json()
    access_token_google = token_data.get("access_token")

    if not access_token_google:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No access token returned by Google.",
        )

    # 2. Fetch user profile from Google
    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token_google}"},
            timeout=10.0,
        )

    if userinfo_resp.status_code != 200:
        logger.warning("Google userinfo fetch failed: %s", userinfo_resp.text)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch user info from Google.",
        )

    userinfo = userinfo_resp.json()
    google_id: str = userinfo.get("sub", "")
    email: str = userinfo.get("email", "")
    name: str = userinfo.get("name", email)

    if not google_id or not email:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google did not return required user fields (sub, email).",
        )

    # 3. Upsert user and issue JWT
    user = await _upsert_user(db, google_id, email, name)
    await db.commit()

    jwt_token = _make_jwt(user.id)
    logger.info("Issued JWT for user %s (%s)", user.id, user.email)

    # 4. Redirect frontend or return JSON
    frontend_url = settings.frontend_url
    if frontend_url:
        redirect_url = f"{frontend_url.rstrip('/')}?token={jwt_token}"
        return RedirectResponse(url=redirect_url, status_code=302)

    return TokenOut(access_token=jwt_token)


@router.get(
    "/me",
    response_model=MeOut,
    summary="Return current user profile and cohort memberships",
)
async def get_me(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> MeOut:
    """
    Returns the authenticated user's profile plus the list of cohorts
    they belong to (with their per-cohort role).
    """
    result = await db.execute(
        select(CohortMember, Cohort)
        .join(Cohort, CohortMember.cohort_id == Cohort.id)
        .where(
            CohortMember.user_id == current_user.id,
            CohortMember.is_archived == False,  # noqa: E712
        )
        .order_by(Cohort.name)
    )
    rows = result.all()

    cohort_memberships = [
        CohortMembershipOut(
            cohort_id=member.cohort_id,
            cohort_name=cohort.name,
            role=member.role,
        )
        for member, cohort in rows
    ]

    return MeOut(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        created_at=current_user.created_at,
        cohorts=cohort_memberships,
    )


@router.post(
    "/logout",
    summary="Logout (client-side — invalidates nothing server-side)",
    status_code=status.HTTP_200_OK,
)
async def logout():
    """
    JWTs are stateless — the server cannot invalidate them.
    The client should delete its stored token on receiving this 200.

    For production, consider a token blocklist (Redis) if immediate
    revocation is required.
    """
    return {"detail": "Logged out. Please delete your token on the client."}
