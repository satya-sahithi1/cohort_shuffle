"""
main.py — FastAPI application entrypoint.

This file:
  1. Creates the FastAPI app instance
  2. Adds CORS middleware (so the frontend can call the backend)
  3. Registers all routers (each router = one group of endpoints)
  4. Exposes a health check at GET /health

To run the server:
    cd backend
    uvicorn app.main:app --reload --port 8000

The --reload flag restarts the server whenever you save a file.
Useful during development.

API docs are auto-generated and available at:
    http://localhost:8000/docs     (Swagger UI)
    http://localhost:8000/redoc    (ReDoc)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API for Cohort Shuffle — automatic team formation for classes.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allows the frontend (running on a different port) to make API calls.
# In production this would be locked to the actual frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
# Each router is registered here with its URL prefix.
# Routers are added as they are built in later phases.
#
# from app.routers import auth, cohorts, activities, registrations, teams
# app.include_router(auth.router,          prefix="/auth",       tags=["auth"])
# app.include_router(cohorts.router,       prefix="/cohorts",    tags=["cohorts"])
# app.include_router(activities.router,    prefix="/activities", tags=["activities"])
# app.include_router(registrations.router, prefix="/activities", tags=["registrations"])
# app.include_router(teams.router,         prefix="",            tags=["teams"])


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health_check():
    """
    Returns 200 if the server is running.
    Use this to confirm the backend is reachable before running the frontend.
    """
    return {"status": "ok", "app": settings.app_name}
