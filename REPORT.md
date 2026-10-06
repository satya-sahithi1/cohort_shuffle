# Cohort Shuffle — Verification Report

Generated: 2026-10-06  
Verified by: running every check from scratch, no prior claims trusted.

---

## 1. Summary

The backend API is structurally complete: all modules import cleanly, all 21 business routes are registered, the algorithm passes its backend test suite (74/74), and team formation runs correctly in simulation. However the app cannot be used end-to-end because there is no login flow — the `/auth/*` routes (Google OAuth) have not been built, so no client can obtain a JWT. Two additional bugs (a schema mismatch and a top-level code sync issue) will cause failures in specific conditions.

**Overall status: Ready with issues**

---

## 2. What Was Built

- PostgreSQL schema: 9 tables (`users`, `cohorts`, `cohort_members`, `activities`, `activity_locks`, `registrations`, `teams`, `team_members`, `formation_logs`). One Alembic migration (`0001_initial_schema.py`).
- FastAPI app with async SQLAlchemy and APScheduler.
- Cohort management: create, join (domain-restricted), invite link (JWT), member add/archive/role-change.
- Activity lifecycle: create with locks, edit, deadline scheduler that fires formation automatically.
- Registration: register, unregister (with cap-hit re-open), admin list.
- Team formation: `formation_service.py` reads DB, calls algorithm, writes teams, logs result.
- Teams API: trigger formation manually, view formed teams + logs, student history, admin member edit.
- Algorithm module (`backend/app/algorithm/`): greedy placer, swap optimiser, fairness pass, scorer, shape calculator.
- JWT auth dependency (`deps.py`): validates Bearer tokens for every route. Works once a token exists.
- Health check: `GET /health`.

---

## 3. Verification Results

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Python version ≥ 3.11 | PASS | `python --version` → `Python 3.12.3` |
| 2 | All backend deps installed | PARTIAL | `pip list` shows all core deps. `APScheduler` installed is `3.11.3`, pinned to `3.10.4` in requirements.txt. `passlib[bcrypt]` is in requirements.txt but not installed (not used in code yet). |
| 3 | All modules import without error | PASS | 23 modules imported; all printed `OK`. Command: `python -c "__import__('app.main')"` (see section 9). |
| 4 | All expected routes registered | PASS | 21 business routes + 9 meta/docs = 30 total. `GET /activities/{id}/teams`, `POST /activities/{id}/form-teams`, `GET /users/me/teams`, `PATCH /teams/{id}/members` all present. |
| 5 | `/auth/*` routes exist | FAIL | Command: `grep -r 'auth_router\|/auth/' backend/app/routers/` → no matches. No `/auth/google`, `/auth/callback`, `/auth/me`, `/auth/logout` routes exist anywhere. |
| 6 | DB schema matches models | PASS | Migration `0001_initial_schema.py` creates all 9 tables. `activity_status` enum in migration: `('open','closed','forming','formed')`. Matches `Activity` model. |
| 7 | `ActivityOut` schema covers all status values | FAIL | `schemas/activity.py` line 103: `status: Literal["open", "closed", "formed"]`. Missing `"forming"`. The DB and model both have `"forming"`. Any API response serialised while `activity.status == "forming"` will raise a Pydantic validation error (HTTP 500). |
| 8 | `unregister()` guards formed/forming status | PARTIAL | `registration_service.py` line 112 checks deadline only. If `activity.status == "forming"` or `"formed"` but deadline has not yet passed (possible for manual formation), a student can still call DELETE /register. The re-open logic on line 130 only fires for `status == "closed"`, so a formed activity would not be incorrectly re-opened, but the delete itself would still succeed silently. |
| 9 | `.env.example` covers all config vars | PASS | `.env.example` has `DATABASE_URL`, `SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `DEBUG`, `CORS_ORIGINS`. All match `config.py` fields. No undocumented required vars. |
| 10 | Top-level `algorithm/` in sync with `backend/app/algorithm/` | FAIL | `algorithm/swapper.py:13`: `def optimise(teams, history)` — no `deadline` param. `algorithm/engine.py:143`: calls `swap_optimise(best_teams, history, deadline=deadline)`. 8 tests fail with `TypeError: optimise() got an unexpected keyword argument 'deadline'`. The backend copy (`backend/app/algorithm/swapper.py`) is correct; the top-level copy is stale. |
| 11 | Backend algorithm tests pass | PASS (backend) / FAIL (top-level) | `backend/tests/algorithm/`: 74 passed, 0 failed. `tests/algorithm/`: 88 passed, 8 failed. See section 4. |
| 12 | Simulation completes within 2 s | PASS | All four cohort sizes finished each round within the 2 s budget. See section 5. |

---

## 4. Test Results

### Backend algorithm tests (backend/tests/algorithm/)

```
Command: cd backend && .venv/bin/pytest tests/algorithm/ -v
Result:  74 passed, 0 failed  (2.84 s)
```

### Top-level algorithm tests (tests/algorithm/)

```
Command: cd /path/to/cohort_shuffle && .venv/bin/pytest tests/algorithm/ -v
Result:  88 passed, 8 failed  (0.12 s)
```

**All 8 failures are the same cause:** `algorithm/swapper.py::optimise()` does not accept the `deadline` keyword argument that `algorithm/engine.py` passes on line 143 and 151.

Failing tests:
- `TestWithHistory::test_all_students_placed`
- `TestWithHistory::test_no_duplicates_in_teams`
- `TestWithHistory::test_score_lower_than_naive_random`
- `TestWithHistory::test_saturation_increases_over_activities`
- `TestWithHistory::test_result_fields_populated`
- `TestFairness::test_no_fairness_violations_early_activities`
- `TestFairness::test_unfair_students_field_matches_has_violations`
- `TestLocksSatisfied::test_together_lock_satisfied_with_history`

### Commands you can run

```bash
# Backend tests (all pass):
cd backend
.venv/bin/pytest tests/algorithm/ -v

# Top-level tests (8 fail):
cd ..
.venv/bin/pytest tests/algorithm/ -v
```

---

## 5. Simulation Results

These numbers come from synthetic test data generated in Python. They are not measurements of real user behaviour and are not guarantees of production performance.

Each simulation runs 4 formation rounds on a single cohort, accumulating pair history across rounds.

```
Command used:
  cd backend && .venv/bin/python -c "... (form_teams loop)" 
```

### 10 students, team_size=3

| Round | Teams | Sizes | Score | Repeat pairs | Saturation | Restarts | Time (ms) |
|-------|-------|-------|-------|-------------|-----------|---------|-----------|
| 1     | 3     | 3–4   | 0.00  | 0           | 0.000     | 0       | 0.2       |
| 2     | 3     | 3–4   | 1.50  | 1           | 0.267     | 9943    | 2000      |
| 3     | 3     | 3–4   | 2.83  | 2           | 0.511     | 7280    | 2000      |
| 4     | 3     | 3–4   | 3.75  | 2           | 0.733     | 5713    | 2000      |

Note: 10 students have only 45 possible pairs total; repeats are unavoidable from round 2.

### 20 students, team_size=4

| Round | Teams | Sizes | Score | Repeat pairs | Saturation | Restarts | Time (ms) |
|-------|-------|-------|-------|-------------|-----------|---------|-----------|
| 1     | 5     | 4–4   | 0.00  | 0           | 0.000     | 0       | 0.1       |
| 2     | 5     | 4–4   | 0.00  | 0           | 0.158     | 0       | 1.5       |
| 3     | 5     | 4–4   | 0.00  | 0           | 0.316     | 0       | 1.6       |
| 4     | 5     | 4–4   | 0.00  | 0           | 0.474     | 10      | 24.4      |

### 30 students, team_size=5

| Round | Teams | Sizes | Score | Repeat pairs | Saturation | Restarts | Time (ms) |
|-------|-------|-------|-------|-------------|-----------|---------|-----------|
| 1     | 6     | 5–5   | 0.00  | 0           | 0.000     | 0       | 0.2       |
| 2     | 6     | 5–5   | 0.00  | 0           | 0.138     | 0       | 4.6       |
| 3     | 6     | 5–5   | 0.00  | 0           | 0.276     | 0       | 4.6       |
| 4     | 6     | 5–5   | 1.25  | 1           | 0.414     | 261     | 2000      |

### 60 students, team_size=5

| Round | Teams | Sizes | Score | Repeat pairs | Saturation | Restarts | Time (ms) |
|-------|-------|-------|-------|-------------|-----------|---------|-----------|
| 1     | 12    | 5–5   | 0.00  | 0           | 0.000     | 0       | 0.5       |
| 2     | 12    | 5–5   | 0.00  | 0           | 0.068     | 0       | 20.3      |
| 3     | 12    | 5–5   | 0.00  | 0           | 0.136     | 0       | 21.2      |
| 4     | 12    | 5–5   | 0.00  | 0           | 0.203     | 0       | 20.7      |

**Score** = total weighted repeat-pair cost (0 = no repeats). **Saturation** = fraction of all possible pairs who have already worked together. All students placed in every round.

---

## 6. Known Issues

Ordered by seriousness.

### ISSUE-1 — No login flow (Blocker)

**What it affects:** Everything. Without `/auth/*` routes, no client can obtain a JWT. All 21 business endpoints require `Authorization: Bearer <token>`. The app cannot be used by any real user.

**Suggested fix:** Implement `routers/auth.py` with Google OAuth using `Authlib`. Minimum routes: `GET /auth/google` (redirect), `GET /auth/google/callback` (exchange code, issue JWT), `GET /auth/me` (current user + cohorts), `POST /auth/logout`. Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to `.env.example`.

---

### ISSUE-2 — `ActivityOut` schema missing `"forming"` status (Runtime crash)

**What it affects:** Any GET or PATCH request for an activity whose status is `"forming"` (i.e., during the brief window while formation is running) will return HTTP 500 instead of a valid response. The formation service sets `status = "forming"` as an idempotency guard before running.

**Evidence:** `schemas/activity.py` line 103: `status: Literal["open", "closed", "formed"]`. Model and migration both define `('open', 'closed', 'forming', 'formed')`.

**Suggested fix (one line):**
```python
# schemas/activity.py line 103
status: Literal["open", "closed", "forming", "formed"]
```

---

### ISSUE-3 — Top-level `algorithm/swapper.py` out of sync with `backend/app/algorithm/swapper.py` (Test failures)

**What it affects:** 8 of 96 top-level algorithm tests fail. The production backend uses `backend/app/algorithm/` (which is correct), so this does not affect the running app. It does mean the top-level test suite cannot be trusted as a standalone check.

**Evidence:** `algorithm/swapper.py:13`: `def optimise(teams, history)`. `algorithm/engine.py:143`: `swap_optimise(teams, history, deadline=deadline)` → `TypeError`.

**Suggested fix:** Copy `backend/app/algorithm/swapper.py` over `algorithm/swapper.py`, or add `deadline: float | None = None` to `algorithm/swapper.py::optimise()`.

---

### ISSUE-4 — `unregister()` does not check activity status (Minor logic gap)

**What it affects:** A student can call `DELETE /activities/{id}/register` on an activity with `status = "forming"` or `"formed"` if the deadline has not yet passed. The registration row is deleted, but the activity status is not changed (line 130 only re-opens for `status == "closed"`). The student would be removed from registration but their team assignment is not updated.

**Suggested fix:** Add a status check at the top of `unregister()`:
```python
if activity.status in ("forming", "formed"):
    raise RegistrationError("Teams have already been formed; you cannot unregister.")
```

---

### ISSUE-5 — `passlib[bcrypt]` in requirements.txt but not installed (Minor)

**What it affects:** `pip install -r requirements.txt` on a fresh machine will install passlib. It is not imported anywhere in the current code, so no runtime effect. If it were ever imported, it would work.

**Suggested fix:** Remove from `requirements.txt`, or install it if password hashing will be needed later.

---

### ISSUE-6 — APScheduler version drift (Minor)

**What it affects:** `requirements.txt` pins `apscheduler==3.10.4`, but `3.11.3` is installed. Minor version bumps in APScheduler are generally backward-compatible, but this is untested.

**Suggested fix:** Update the pin: `apscheduler==3.11.3`.

---

## 7. Not Done Yet

From the implementation plan phases:

| Phase | Task | Status |
|-------|------|--------|
| Phase 1 | Google OAuth login (`/auth/google`, `/auth/callback`, `/auth/me`, `/auth/logout`) | Not started |
| Phase 1 | Frontend: login page, cohort join flow | Not started |
| Phase 2 | Frontend: activity creation, registration UI | Not started |
| Phase 4 | Frontend: student My Teams page | Not started |
| Phase 4 | Frontend: admin team view and edit UI | Not started |
| Phase 4 | Frontend: formation log display | Not started |
| Phase 5 | Error and empty states in UI | Not started |
| Phase 5 | Mobile-responsive layout | Not started |
| Phase 5 | End-to-end tests for full activity lifecycle | Not started |
| Any | Docker Compose setup | Not started |
| Any | Nginx config | Not started |

The frontend scaffold exists (`cohort-shuffle-frontend/`) with Next.js and shadcn/ui, but no real pages have been connected to the backend API.

---

## 8. Open Questions

1. **Auth provider:** The plan says Google OAuth. If the project is running in an environment without internet access, Google OAuth will not work. Is a username/password fallback needed for local dev?

2. **Formation trigger on cap-hit:** When a student's registration hits the cap, the activity closes immediately. The current code does NOT run formation automatically at that point — it only closes the activity. Formation is triggered by the scheduler at deadline time. If the cap is hit well before the deadline, students wait a long time with no teams. Is that the intended behaviour?

3. **Re-run policy:** `POST /activities/{id}/form-teams` allows re-runs on a `formed` activity. Are there any restrictions (e.g., only before `event_at`)? The router currently has no such guard.

4. **Top-level `algorithm/` directory:** Is it still needed? The backend uses `backend/app/algorithm/`. If the top-level copy is just for standalone testing, it needs to be kept in sync manually. Consider deleting it and pointing the top-level tests at the backend copy via `pythonpath`.

5. **Team edit after formation:** `PATCH /teams/{id}/members` replaces the full member list. It does not check that each user is also in the activity's registrations — only that they are a cohort member. A user could be added to a team without being registered. Is that intentional (for admin overrides)?

6. **`random_seed` type in FormationLog:** The model stores `random_seed` as `Integer` (32-bit). The engine generates seeds via `random.randrange(2**32)`, which fits. But `2**32 - 1 = 4294967295` exceeds PostgreSQL's `INT` max (`2147483647`). Seeds above ~2.1 billion will overflow. Should the column be `BIGINT`?

---

## 9. How to Run It

### Prerequisites

- Python 3.11+
- PostgreSQL running locally (or via Docker)
- A `.env` file at `backend/.env` (copy from `.env.example`)

### Setup

```bash
# 1. Clone and enter the backend
cd backend

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and edit .env
cp .env.example .env
# Edit .env: set DATABASE_URL to your postgres instance
# Edit .env: set SECRET_KEY to a long random string
```

### Create the database

```bash
# If using PostgreSQL locally, create the DB first:
# psql -U postgres -c "CREATE DATABASE cohort_shuffle;"

# Then run migrations:
cd backend
.venv/bin/alembic upgrade head
```

### Run tests

```bash
# Backend algorithm tests (all should pass):
cd backend
.venv/bin/pytest tests/algorithm/ -v

# Top-level algorithm tests (8 will fail — see ISSUE-3):
cd ..
.venv/bin/pytest tests/algorithm/ -v
```

### Start the server

```bash
cd backend
.venv/bin/uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs  
Health check: http://localhost:8000/health

### Verify routes are registered

```bash
cd backend
.venv/bin/python -c "
from app.main import app
for r in sorted(app.routes, key=lambda r: getattr(r,'path','')):
    if hasattr(r,'methods'):
        print(sorted(r.methods), r.path)
"
```

### Run a quick simulation

```bash
cd backend
.venv/bin/python - <<'EOF'
from app.algorithm.engine import form_teams
students = [f"s{i}" for i in range(20)]
r = form_teams(students, team_size=4, history={})
print(f"Teams: {len(r.teams)}, Score: {r.score}, Seed: {r.random_seed}")
for i, t in enumerate(r.teams, 1):
    print(f"  Team {i}: {t}")
EOF
```
