"""
main.py — FastAPI application entrypoint.

Startup sequence:
  1. Create FastAPI app with CORS middleware
  2. Register all routers
  3. On startup: boot APScheduler and schedule deadline jobs for all
     open activities whose deadlines are in the future

APScheduler runs inside the FastAPI process (no separate worker needed
at this scale). Each activity with status='open' and a future deadline
gets one-shot job that fires formation at deadline_at.

When the formation engine (Phase 3) is implemented, the scheduler job
will call formation_service.run(activity_id). For now the job logs the
trigger and marks the activity as 'closed' as a placeholder.

To run the server:
    cd backend
    uvicorn app.main:app --reload --port 8000

API docs:
    http://localhost:8000/docs
    http://localhost:8000/redoc
"""

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.activity import Activity
from app.routers.activities import activity_router, cohort_router
from app.routers.cohorts import router as cohorts_router
from app.routers.registrations import router as registrations_router

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Scheduler ─────────────────────────────────────────────────────────────────

scheduler = AsyncIOScheduler(timezone="UTC")


async def _deadline_job(activity_id: str) -> None:
    """
    Fired by the scheduler when an activity's deadline_at arrives.

    Phase 2: closes the activity so no new registrations can come in.
    Phase 3 will replace this with formation_service.run(activity_id).

    The job is idempotent — if the activity was already closed (e.g., cap
    was reached before the deadline), this is a no-op.
    """
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Activity).where(Activity.id == uuid.UUID(activity_id))
            )
            activity = result.scalar_one_or_none()

            if activity is None:
                logger.warning("Deadline job: activity %s not found", activity_id)
                return

            if activity.status != "open":
                logger.info(
                    "Deadline job: activity %s already %s, skipping",
                    activity_id,
                    activity.status,
                )
                return

            # Close registration. Phase 3 will call form_teams() here.
            activity.status = "closed"
            db.add(activity)
            await db.commit()
            logger.info(
                "Deadline job: activity %s closed at deadline", activity_id
            )

        except Exception:
            logger.exception(
                "Deadline job failed for activity %s", activity_id
            )
            await db.rollback()


def schedule_deadline_job(activity_id: uuid.UUID, deadline_at: datetime) -> None:
    """
    Schedule (or re-schedule) the one-shot deadline job for an activity.
    Safe to call multiple times — APScheduler will replace an existing job
    with the same id.
    """
    now = datetime.now(timezone.utc)
    if deadline_at <= now:
        # Deadline already passed — fire immediately in a short moment
        return

    job_id = f"deadline:{activity_id}"
    scheduler.add_job(
        _deadline_job,
        trigger=DateTrigger(run_date=deadline_at),
        id=job_id,
        args=[str(activity_id)],
        replace_existing=True,
        misfire_grace_time=60,  # allow up to 60s late firing
    )
    logger.info("Scheduled deadline job %s for %s", job_id, deadline_at.isoformat())


def cancel_deadline_job(activity_id: uuid.UUID) -> None:
    """
    Cancel the deadline job for an activity (e.g., when the cap is reached
    and formation should run immediately instead of waiting).
    """
    job_id = f"deadline:{activity_id}"
    try:
        scheduler.remove_job(job_id)
        logger.info("Cancelled deadline job %s", job_id)
    except Exception:
        pass  # job may not exist yet; that's fine


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler — replaces the deprecated @app.on_event pattern.
    Code before `yield` runs on startup; code after runs on shutdown.
    """
    # ── Startup ──
    scheduler.start()
    logger.info("APScheduler started")

    # Load all open activities and schedule their deadline jobs
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Activity).where(Activity.status == "open")
        )
        open_activities = result.scalars().all()

    now = datetime.now(timezone.utc)
    scheduled = 0
    for activity in open_activities:
        deadline = activity.deadline_at
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline > now:
            schedule_deadline_job(activity.id, deadline)
            scheduled += 1

    logger.info(
        "Scheduled %d deadline jobs for %d open activities",
        scheduled,
        len(open_activities),
    )

    yield  # ← app runs while suspended here

    # ── Shutdown ──
    scheduler.shutdown(wait=False)
    logger.info("APScheduler stopped")


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API for Cohort Shuffle — automatic team formation for classes.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
# cohorts_router  → /cohorts                          (cohort CRUD + membership)
# cohort_router   → /cohorts/{cohort_id}/activities   (create + list activities)
# activity_router → /activities/{activity_id}          (get + patch activity)
# registrations   → /activities/{activity_id}/register(s)

app.include_router(cohorts_router, prefix="/cohorts", tags=["cohorts"])
app.include_router(cohort_router, prefix="/cohorts", tags=["activities"])
app.include_router(activity_router, prefix="/activities", tags=["activities"])
app.include_router(registrations_router, prefix="/activities", tags=["registrations"])


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health_check():
    """Returns 200 if the server is running."""
    return {"status": "ok", "app": settings.app_name}
