# Cohort Shuffle — Implementation Plan

---

## Tech Stack

### Backend
- **Python 3.11+** with **FastAPI**
  - Clean async support, automatic API docs, fast to write
  - Algorithm module runs as pure Python — no framework coupling
- **PostgreSQL** — relational data with clear foreign keys fits the data model perfectly
- **SQLAlchemy 2.0** (async) — ORM for database access
- **APScheduler** — runs the formation job at deadline time
- **Authlib** — handles Google OAuth flow

### Frontend
- **React 18** with **Vite**
  - Two distinct UIs (admin dashboard, student view) — React handles this cleanly
- **React Router** — client-side routing
- **TanStack Query** — server state, caching, refetching
- **Tailwind CSS** — utility-first styling, fast to build with

### Infrastructure (simple, self-hosted or cheap cloud)
- **Docker + Docker Compose** — one command to run everything locally and in prod
- **Nginx** — reverse proxy, serves frontend static files, proxies API
- **PostgreSQL** runs in its own container

No Kubernetes, no message queues, no microservices. This is a small app — keep it simple.

---

## Project Layout

Monorepo — everything in one folder, one clone.

```
cohort_shuffle/
├── backend/
│   ├── algorithm/        # pure Python shuffle logic, no DB
│   ├── app/              # FastAPI web server
│   ├── tests/            # backend-specific integration tests
│   ├── alembic/          # DB migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   └── Dockerfile
├── tests/                # TOP-LEVEL: algorithm unit tests, mirrors backend/algorithm/
│   └── algorithm/
│       ├── test_scorer.py
│       ├── test_greedy.py
│       ├── test_swapper.py
│       ├── test_fairness.py
│       ├── test_engine.py
│       └── conftest.py   # shared fixtures (student lists, pair histories)
├── docker-compose.yml
├── nginx.conf
└── docs/                 # problem_draft2.md, algorithm_approach1.md, implementation_plan.md
```

The `tests/` folder at root is entirely independent of the web stack. It only imports from `backend/algorithm/`. You can run it at any point without a running server or database.

---

## Python Environment

- Plain `venv` + `requirements.txt` for simplicity
- `pyproject.toml` added for proper packaging (so `tests/` can import `backend/algorithm/` cleanly without path hacks)
- Test runner: `pytest`
- `conftest.py` at `tests/algorithm/` provides shared fixtures: pre-built student lists, sample pair histories, lock sets

---



---

## Database Schema

```
users
  id            UUID  PK
  email         TEXT  UNIQUE
  name          TEXT
  google_id     TEXT  UNIQUE
  is_archived   BOOL  DEFAULT false
  created_at    TIMESTAMPTZ

cohorts
  id            UUID  PK
  name          TEXT
  admin_id      UUID  FK → users.id
  allowed_domain TEXT  NULLABLE   -- e.g. "university.edu", null = any
  created_at    TIMESTAMPTZ

cohort_members
  cohort_id     UUID  FK → cohorts.id
  user_id       UUID  FK → users.id
  role          ENUM  ('admin', 'student')
  is_archived   BOOL  DEFAULT false
  joined_at     TIMESTAMPTZ
  PRIMARY KEY (cohort_id, user_id)

activities
  id            UUID  PK
  cohort_id     UUID  FK → cohorts.id
  name          TEXT
  team_size     INT
  duration      TEXT
  event_at      TIMESTAMPTZ
  deadline_at   TIMESTAMPTZ
  participant_cap INT  NULLABLE
  status        ENUM  ('open', 'closed', 'formed')
  formation_run_count INT DEFAULT 0
  created_at    TIMESTAMPTZ

activity_locks
  id            UUID  PK
  activity_id   UUID  FK → activities.id
  user_a        UUID  FK → users.id
  user_b        UUID  FK → users.id
  constraint_type ENUM ('together', 'apart')

registrations
  id            UUID  PK
  activity_id   UUID  FK → activities.id
  user_id       UUID  FK → users.id
  registered_at TIMESTAMPTZ
  UNIQUE (activity_id, user_id)

teams
  id            UUID  PK
  activity_id   UUID  FK → activities.id
  team_number   INT
  formation_run INT   -- which run produced this (for re-run tracking)

team_members
  team_id       UUID  FK → teams.id
  user_id       UUID  FK → users.id
  PRIMARY KEY (team_id, user_id)

formation_logs
  id            UUID  PK
  activity_id   UUID  FK → activities.id
  run_number    INT
  triggered_by  UUID  FK → users.id  NULLABLE  -- null = automatic
  score         INT
  repeat_pairs  INT
  saturation    FLOAT
  created_at    TIMESTAMPTZ
```

**Key design notes:**
- History is derived entirely from `team_members` — no separate pair history table.
- `formation_run` on `teams` tracks which run produced which teams, so re-runs don't mix with previous results.
- `is_archived` on users and cohort_members handles departing students without deletion.

---

## API Endpoints

### Auth
```
GET  /auth/google              → redirect to Google OAuth
GET  /auth/google/callback     → handle callback, issue session cookie
POST /auth/logout
GET  /auth/me                  → current user info + cohort memberships
```

### Cohorts
```
POST   /cohorts                        → create cohort (admin)
GET    /cohorts/{id}                   → cohort details
GET    /cohorts/{id}/members           → list members
POST   /cohorts/{id}/members           → add student manually (admin)
PATCH  /cohorts/{id}/members/{uid}     → archive/unarchive student (admin)
```

### Activities
```
POST   /cohorts/{id}/activities        → create activity (admin)
GET    /cohorts/{id}/activities        → list activities (all members)
GET    /activities/{id}                → activity detail
PATCH  /activities/{id}                → edit activity, validate locks (admin)
POST   /activities/{id}/form-teams     → manual formation trigger (admin)
```

### Registrations
```
POST   /activities/{id}/register       → student registers
DELETE /activities/{id}/register       → student unregisters (before deadline)
GET    /activities/{id}/registrations  → list registered students (admin)
```

### Teams
```
GET    /activities/{id}/teams          → teams for activity (post-formation)
GET    /users/me/teams                 → student's full team history
PATCH  /teams/{id}/members             → manual team edit (admin)
```

---

## Formation Flow (Backend)

```
Trigger: deadline passes OR cap is reached
    ↓
formation_service.run(activity_id)
    ↓
1. Lock activity status → 'forming' (idempotency guard — prevents double run)
    ↓
2. Load registered students from DB
    ↓
3. Validate locks — if unsatisfiable, abort + notify admin, status back to 'closed'
    ↓
4. Load pair history from team_members (sparse: only pairs with count > 0)
    ↓
5. algorithm/engine.py → returns team assignments
    ↓
6. Write teams + team_members to DB in a single transaction
    ↓
7. Compute saturation, log to formation_logs
    ↓
8. If saturation ≥ 0.80 → flag on activity record for frontend to show warning
    ↓
9. Update activity status → 'formed'
```

The idempotency guard in step 1 (status check + atomic update) prevents the double-formation bug mentioned in the spec, even if the scheduler fires twice.

---

## Scheduler

APScheduler runs inside the FastAPI process. At startup:

```python
for each open activity with deadline_at in the future:
    schedule a one-shot job at deadline_at → formation_service.run(activity_id)
```

When a new activity is created, its deadline job is added immediately.

When a cap is hit during registration, the scheduler job is cancelled and formation runs inline.

---

## Algorithm Module (backend/algorithm/)

The algorithm is a pure Python module with **no database calls**. It takes:

```python
def form_teams(
    students: list[str],          # student IDs
    team_size: int,
    pair_history: dict,           # {(a,b): (count, days_ago)} sparse
    locks: list[Lock],            # must_together / must_apart constraints
    time_limit: float = 2.0
) -> list[list[str]]:             # list of teams
```

And returns team assignments. The formation service handles all DB reads/writes around it.

This separation means the algorithm can be unit-tested completely independently of the web framework or database.

---

## Frontend Pages

### Student view
- **Login** — "Sign in with Google" button, redirect after auth
- **Activities** — list of all cohort activities, each with name / date / deadline / team size / registration status. Register/unregister button per activity.
- **My Teams** — full history. Each entry: activity name, date, team number, teammates.

### Admin view
- **Dashboard** — list of cohorts, summary of recent activities
- **Create Activity** — form with all fields. Deadline warning shown inline. Lock constraint builder (student picker + constraint type dropdown). Cap field.
- **Activity Detail** — registered students count, deadline countdown, formation status, saturation warning if applicable. Manual "Form Teams" button. Re-run button (before event start). Formation log.
- **Team View** — teams displayed post-formation. Admin can drag-drop or manually reassign students.

---

## Build Phases

### Phase 1 — Foundation (get data model + auth working)
1. Project scaffold: FastAPI + PostgreSQL + Docker Compose
2. Google OAuth login, session management
3. DB schema + Alembic migrations
4. Cohort CRUD — create, add members, domain restriction
5. Basic frontend: login page, cohort join flow

### Phase 2 — Activity lifecycle
6. Activity creation form (all fields, deadline rule, lock builder)
7. Registration endpoints + frontend register/unregister buttons
8. Deadline enforcement — scheduler setup, cap-hit trigger
9. Activities list page for students

### Phase 3 — Team formation (core)
10. Algorithm module — scorer, greedy, swapper, fairness pass, engine
11. Unit tests for algorithm (this is the most important test suite)
12. Formation service — DB read/write wrapper around algorithm
13. Formation trigger wiring (scheduler + manual)
14. Lock validation before formation
15. Formation log + saturation warning

### Phase 4 — Team views + admin controls
16. Student My Teams page
17. Admin team view — post-formation display
18. Manual team edit (admin)
19. Re-run formation (admin, pre-event only)
20. Formation log display

### Phase 5 — Polish
21. Error states and empty states in UI
22. Mobile-responsive layout
23. End-to-end tests for the full activity lifecycle

---

## What to Build First

Start with Phase 1 + the algorithm module in parallel:

- The algorithm needs no web stack — write and test it immediately as a standalone Python module.
- The web stack (auth + DB) can be scaffolded separately.
- They meet in Phase 3 when the formation service wires them together.

This means two people can work independently, or you can do the algorithm first (it's the interesting part) and then build the app around it.
