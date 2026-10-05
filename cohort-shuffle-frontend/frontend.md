# Cohort Shuffle — Frontend Documentation

---

## Overview

The frontend is a **Next.js 16 (App Router)** application written in **TypeScript**. It uses **Tailwind CSS** for styling, **NextAuth v5** for Google OAuth authentication, and a custom `lib/api/` layer that talks to the FastAPI backend.

All pages are fully built and use mock data (`lib/mocks/`) when the backend is not running. Swapping to live data requires no page changes — only the import source changes from `lib/mocks/` to `lib/api/` (already done).

---

## Tech Stack

| Concern | Choice |
|---|---|
| Framework | Next.js 16.3.8 (App Router) |
| Language | TypeScript 5 |
| Styling | Tailwind CSS v4 |
| Auth | NextAuth v5 (Google OAuth only) |
| UI primitives | @base-ui/react + custom shadcn-style components |
| Icons | lucide-react |
| State | React built-in (useState, useContext) |
| Data fetching | Plain fetch() via lib/api/client.ts |

---

## Project Structure

```
cohort-shuffle-frontend/
├── src/
│   ├── app/                          # Next.js App Router pages
│   │   ├── (app)/                    # Authenticated app shell group
│   │   │   ├── layout.tsx            # Wraps all app pages with CohortProvider + AppShell
│   │   │   ├── dashboard/
│   │   │   │   ├── page.tsx          # Dashboard — open activities + recent teams
│   │   │   │   ├── layout.tsx        # Page title metadata
│   │   │   │   └── loading.tsx       # Skeleton shown while page JS loads
│   │   │   ├── activities/
│   │   │   │   ├── page.tsx          # Activity list (open / past sections)
│   │   │   │   ├── layout.tsx
│   │   │   │   ├── loading.tsx       # Skeleton
│   │   │   │   ├── new/
│   │   │   │   │   ├── page.tsx      # Create activity form (admin only)
│   │   │   │   │   └── layout.tsx
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx      # Activity detail + formation controls
│   │   │   │       └── layout.tsx
│   │   │   ├── teams/
│   │   │   │   ├── page.tsx          # My Teams — full history with cohort filter
│   │   │   │   ├── layout.tsx
│   │   │   │   └── loading.tsx       # Skeleton
│   │   │   ├── admin/
│   │   │   │   ├── page.tsx          # Admin hub — links to activities/members/settings
│   │   │   │   ├── layout.tsx
│   │   │   │   ├── members/
│   │   │   │   │   └── page.tsx      # Cohort members page (empty state)
│   │   │   │   └── settings/
│   │   │   │       └── page.tsx      # Cohort settings page (empty state)
│   │   │   └── join/
│   │   │       ├── page.tsx          # Join cohort by link or browse eligible cohorts
│   │   │       └── layout.tsx
│   │   ├── sign-in/
│   │   │   ├── page.tsx              # Google sign-in button + OAuth error handling
│   │   │   └── layout.tsx
│   │   ├── api/auth/[...nextauth]/
│   │   │   └── route.ts              # NextAuth handler (GET + POST)
│   │   ├── not-found.tsx             # Custom 404 page
│   │   ├── layout.tsx                # Root layout — fonts, SessionProvider
│   │   ├── page.tsx                  # Root redirect → /dashboard
│   │   └── globals.css               # Tailwind base styles
│   ├── components/
│   │   ├── activities/
│   │   │   ├── ActivityCard.tsx      # Card shown in the activities list
│   │   │   ├── FormedTeamsView.tsx   # Post-formation team grid (admin) or your team (student)
│   │   │   ├── FormationLogPanel.tsx # Formation run history rows
│   │   │   └── TeamEditView.tsx      # Admin click-to-move team editor
│   │   ├── layout/
│   │   │   ├── AppShell.tsx          # TopNav + main content wrapper
│   │   │   ├── TopNav.tsx            # Sticky nav — desktop links + mobile slide-in
│   │   │   ├── CohortSwitcher.tsx    # Dropdown to switch active cohort
│   │   │   └── UserMenu.tsx          # Avatar dropdown — user info + sign out
│   │   ├── providers/
│   │   │   └── SessionProvider.tsx   # NextAuth SessionProvider wrapper
│   │   └── ui/                       # Primitive UI components
│   │       ├── button.tsx            # Button with asChild (Radix Slot) support
│   │       ├── badge.tsx
│   │       ├── card.tsx
│   │       ├── avatar.tsx
│   │       ├── input.tsx
│   │       ├── label.tsx
│   │       ├── select.tsx
│   │       ├── textarea.tsx
│   │       ├── dialog.tsx
│   │       ├── dropdown-menu.tsx
│   │       ├── separator.tsx
│   │       └── tooltip.tsx
│   ├── lib/
│   │   ├── api/                      # Real fetch() calls → FastAPI backend
│   │   │   ├── client.ts             # Base fetch wrapper with Bearer auth + ApiError
│   │   │   ├── activities.ts         # Activity + registration API calls
│   │   │   ├── cohorts.ts            # Cohort membership + join API calls
│   │   │   ├── teams.ts              # Team history API calls
│   │   │   └── formation.ts          # Formation trigger, teams fetch, logs, move
│   │   ├── mocks/                    # In-memory stubs (same signatures as lib/api/)
│   │   │   ├── activities.ts
│   │   │   ├── cohorts.ts
│   │   │   ├── teams.ts
│   │   │   └── formation.ts          # Pre-seeded formation result for act-4
│   │   └── utils.ts                  # cn() re-export
│   ├── contexts/
│   │   └── CohortContext.tsx         # Active cohort state + localStorage persistence
│   ├── types/
│   │   └── index.ts                  # All TypeScript types + NextAuth module augmentation
│   ├── auth.ts                       # NextAuth config (Google provider, JWT callbacks)
│   └── proxy.ts                      # Route protection middleware (Next.js 16 convention)
├── .env.local                        # Environment variables (see section below)
├── package.json
└── tsconfig.json
```

---

## Routes

| Route | Who can see it | Description |
|---|---|---|
| `/` | Anyone | Redirects to `/dashboard` |
| `/sign-in` | Unauthenticated | Google sign-in button |
| `/dashboard` | Any signed-in user | Open activities + recent teams summary |
| `/activities` | Any cohort member | Full activity list |
| `/activities/new` | Admin only | Create activity form |
| `/activities/[id]` | Any cohort member | Activity detail, register, formation controls |
| `/teams` | Any cohort member | Full team history with cohort filter |
| `/join` | Any signed-in user | Join cohort by invite link or browse |
| `/admin` | Admin only | Hub — links to activities, members, settings |
| `/admin/members` | Admin only | Cohort member roster (empty state) |
| `/admin/settings` | Admin only | Cohort settings (empty state) |
| `/api/auth/[...nextauth]` | Internal | NextAuth OAuth handler |

Route protection is enforced by `src/proxy.ts`:
- Unauthenticated users accessing protected routes → redirect to `/sign-in?callbackUrl=...`
- Authenticated non-admins accessing `/admin/*` → redirect to `/dashboard`
- Already signed-in users visiting `/sign-in` → redirect to `/dashboard`

---

## Authentication

Sign-in is **Google OAuth only** via NextAuth v5. No passwords are stored.

**How roles work:**
- On first sign-in, the `jwt` callback in `auth.ts` calls `resolveRole(email)`.
- Any email listed in the `ADMIN_EMAILS` environment variable gets `role: "admin"`.
- Everyone else gets `role: "student"`.
- The role is stored in the JWT and exposed on the session as `session.user.role`.

**How the API client gets the token:**
- The `session` callback exposes `session.accessToken = token.jti ?? token.sub`.
- `lib/api/client.ts` reads this via `getSession()` and attaches it as `Authorization: Bearer <token>` on every request to the FastAPI backend.

---

## Environment Variables

Copy `.env.local` and fill in the values before running:

```bash
# Google OAuth credentials
# Create at: https://console.cloud.google.com/
# Redirect URI must be: http://localhost:3000/api/auth/callback/google
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# NextAuth secret — generate with: npx auth secret
NEXTAUTH_SECRET=
NEXTAUTH_URL=http://localhost:3000

# Emails that receive the admin role (comma-separated)
# e.g. ADMIN_EMAILS=you@example.com,colleague@example.com
ADMIN_EMAILS=

# FastAPI backend URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Data Layer

Two parallel layers exist with **identical function signatures**:

### `lib/mocks/` — works without a backend
In-memory data. Simulates network latency. Mutations persist for the browser session. Used during development when the FastAPI backend is not running.

### `lib/api/` — calls the real backend
Every function is a drop-in replacement. Converts snake_case backend responses to camelCase TypeScript types. Sends Bearer auth on every request.

**To switch a page from mock to real:**
Change the import from `@/lib/mocks/activities` to `@/lib/api/activities`. The function signatures are identical so nothing else changes. All pages are already pointing at `lib/api/`.

---

## Key Components

### `TopNav`
Sticky header with desktop nav links and a mobile slide-in panel. Active link uses exact match for `/dashboard` and prefix match for all other routes. Closes on route change, Escape key, or backdrop click. Body scroll is locked while the mobile panel is open.

### `CohortContext`
React context that holds the list of cohorts the user belongs to and which one is currently active. Active cohort is persisted to `localStorage` so it survives page refresh. The context is the source of truth — all pages read `activeCohort` from it rather than from the URL.

### `ActivityCard`
Used in the activities list. Handles register/unregister inline with optimistic count updates. Status badge shows four distinct states: Open (green), Forming soon (blue — registration closed, teams not yet formed), Teams formed (grey), Full (red).

### `FormedTeamsView`
Two modes controlled by the `isAdmin` prop:
- Admin: full grid of all teams, member count badge per team.
- Student: only shows the team the current user is on, highlighted with a "Your team" badge.

### `TeamEditView`
Click-to-move editor for admins. Click a student to select them, then click "Move here" on any other team to move them. All buttons are disabled while a move is in progress. "Done editing" returns to the read view.

### `FormationLogPanel`
Displays each formation run as a row: run number, triggered by (auto or admin name), score, repeat pairs, saturation percentage. Saturation is colour-coded: green < 50%, orange 50–80%, red ≥ 80%.

---

## Types (`src/types/index.ts`)

All shared TypeScript types are in one file:

| Type | Description |
|---|---|
| `Role` | `"admin" \| "student"` |
| `AppUser` | Signed-in user with id, email, name, image, role |
| `Cohort` | Cohort with id, name, role, optional allowed domains |
| `Activity` | Full activity record including locks, status, counts |
| `ActivityLock` | A together/apart constraint between two students |
| `Registration` | One student's registration for an activity |
| `TeamEntry` | One row in a student's team history |
| `Teammate` | A member of a team (id, name, email) |
| `FormedTeam` | One team post-formation (teamId, teamNumber, members[]) |
| `FormationResult` | Full result of a formation run (teams, score, saturation, warnings) |
| `FormationLog` | One row in the formation run history |

---

## Running Locally

```bash
cd cohort-shuffle-frontend

# Install dependencies
npm install

# Fill in .env.local (Google OAuth credentials + ADMIN_EMAILS)

# Start development server
npm run dev
# → http://localhost:3000

# Type check
npx tsc --noEmit

# Production build
npm run build
```

The app works fully without a running backend — all pages use the mock data layer (`lib/mocks/`) which is pre-seeded with realistic data including a pre-formed activity (`act-4`) so you can see the formation UI immediately.

---

## What's Still Needed (Future Phases)

| Feature | Notes |
|---|---|
| `/admin/members` full implementation | UI shell exists, needs backend cohort members endpoints |
| `/admin/settings` full implementation | UI shell exists, needs backend cohort CRUD endpoints |
| Backend auth wiring | `lib/api/` calls are built; FastAPI auth endpoints not yet connected |
| Real-time deadline countdown | Currently polling every 30s; could use SSE or WebSocket |
| End-to-end tests | Full activity lifecycle (register → deadline → form → view teams) |
