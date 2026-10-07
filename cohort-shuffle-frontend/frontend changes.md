# Frontend Changes

**Date:** 2026-10-07  
**Scope:** Cohort Shuffle — connecting the Next.js frontend scaffold to the real FastAPI backend  
**Status:** All 8 "Not Done Yet" tasks from REPORT.md completed

---

## Overview

The frontend scaffold existed with Next.js 16 (App Router), Tailwind CSS v4, NextAuth v5, and shadcn-style UI components — but most pages were either using mock data or had gaps in how they talked to the real backend. This document covers every change made, why it was made, and what file was touched.

---

## Task 1 — Fixed `lib/api/teams.ts` (real backend shape mismatch)

**File:** `src/lib/api/teams.ts`

**Problem:** The frontend `TeamEntry` type expected `duration`, `cohortId`, `cohortName`, and a separate `teammates` list. The real backend `TeamHistoryOut` schema only returns `team_id`, `team_number`, `activity_id`, `activity_name`, `event_at`, and `members[]`. Calling the real API would have produced undefined fields everywhere the teams page tried to render them.

**Fix:** Rewrote the adapter function to:
- Map `members[]` directly to `teammates[]` (all members are returned; the UI filters out self using the session user ID)
- Fill `duration`, `cohortId`, and `cohortName` with empty string defaults so nothing crashes when the backend omits them
- Removed the `fetchMyTeamsByCohort` cohort-filter logic (backend doesn't return `cohort_id` in this response, so filtering is a no-op)

---

## Task 2 — Phase 1: Login page (verified wired)

**File:** `src/app/sign-in/page.tsx`

**Status:** Already fully built and wired. No changes needed.

The sign-in page uses NextAuth v5 with a Google OAuth server action. It handles error codes (`OAuthCallback`, `AccessDenied`, etc.) by showing a user-friendly banner. Unauthenticated users visiting any protected route (`/dashboard`, `/activities`, `/teams`, `/admin`, `/join`) are redirected here by `src/proxy.ts`.

---

## Task 3 — Phase 1: Cohort join flow (toast notifications added)

**File:** `src/app/(app)/join/page.tsx`

**Status:** Already fully wired to `lib/api/cohorts.ts`. Toast notifications added.

The join page already called `validateJoinToken`, `joinCohort`, and `fetchEligibleCohorts` from the real API. The only gap was silent failure — if joining failed, nothing told the user. Added `useToast()` calls so:
- Successful join → green toast: "Joined [Cohort Name]!"
- Failed join → red toast with the backend error message

---

## Task 4 — Phase 4: Student My Teams page (real backend shape)

**File:** `src/app/(app)/teams/page.tsx`

**Problem:** The old page used `duration`, `cohortId`, `cohortName`, and a separate `teammates` list that the backend doesn't return. It also had a cohort filter dropdown that depended on `cohortId` being populated.

**Fix:** Rewrote the page to:
- Call `fetchMyTeams()` from the real API only (no cohort filter, since the backend doesn't support it yet)
- Filter the current user out of the `teammates` display using `session.user.id`
- Show activity count and unique teammate count as summary stats
- Handle the empty state cleanly ("Once teams are formed… they'll appear here")
- Add a Refresh button so users can manually re-fetch without reloading

---

## Task 5 — Phase 4: Admin team view and edit UI (wired via formation API)

**Files:**  
- `src/lib/api/formation.ts` (rewritten)  
- `src/app/(app)/activities/[id]/page.tsx` (mock import replaced)
- `src/components/activities/FormedTeamsView.tsx` (no changes needed)
- `src/components/activities/TeamEditView.tsx` (no changes needed)

**Problem:** The activity detail page imported formation functions from `lib/mocks/formation` instead of `lib/api/formation`. The real backend returns very different shapes to what the frontend types expected:

| What the frontend expected | What the backend actually returns |
|---|---|
| `FormationResult` with `score`, `saturation`, `unfairStudents` | `TeamOut[]` (just the teams array) from `POST /form-teams` |
| `FormedTeam` with `teamId`, `teamNumber`, `members[]` | `TeamOut` with `id`, `team_number`, `members[]` |
| `moveStudentBetweenTeams` sending `{ student_id, action }` | `PATCH /teams/{id}/members` taking `{ user_ids: [...] }` |

**Fix:** Completely rewrote `lib/api/formation.ts` to bridge the gap:
- `fetchFormedTeams()` — calls `GET /activities/{id}/teams` (which returns `{ teams, logs }`), synthesises a `FormationResult` from the latest log's `score`/`saturation` fields
- `triggerFormation()` — calls `POST /activities/{id}/form-teams`, then immediately fetches logs to populate stats
- `fetchFormationLogs()` — extracts logs from the combined endpoint
- `moveStudentBetweenTeams()` — fetches current team state, figures out source and target teams, sends two `PATCH /teams/{id}/members` calls with full `user_ids` arrays
- `validateLocks()` — returns empty array (no errors) if the endpoint doesn't exist yet (404/405), so formation can still proceed

Also replaced the duplicate `"use client"` directive in the activity detail page and added handling for the new `"forming"` status — shows a spinning "Forming…" badge and a Refresh button while formation is in progress.

---

## Task 6 — Phase 4: Formation log display (wired via formation API)

**Files:**  
- `src/components/activities/FormationLogPanel.tsx` (no changes needed)  
- `src/lib/api/formation.ts` (see Task 5)

**Status:** The `FormationLogPanel` component was already built. It just needed the real API to feed it data. `fetchFormationLogs()` now correctly extracts the `logs[]` array from `GET /activities/{id}/teams` and maps each `FormationLogOut` backend row to the frontend `FormationLog` type. The activity detail page shows it in a collapsible "Formation history" section.

---

## Task 7 — Phase 5: Admin settings page (real backend API)

**File:** `src/app/(app)/admin/settings/page.tsx`

**Before:** Static empty state with "Settings coming soon."

**After:** A fully functional page with three panels:

### Cohort info card
Fetches `GET /cohorts/{id}` and displays the cohort name, email domain restriction, cohort ID, and creation date. Includes a note that name/domain editing requires a backend `PATCH /cohorts/{id}` endpoint which doesn't exist yet.

### Invite link generator
Calls `GET /cohorts/{id}/join-link` to generate a 72-hour shareable join link. Shows the URL in a read-only input with a one-click copy button. A "Regenerate link" button generates a fresh token.

### Add member by email
Calls `POST /cohorts/{id}/members` to add a student directly by their Google email. Shows inline success ("student@uni.edu has been added") or error feedback.

---

## Task 8 — Phase 5: Global toast notification system

**Files created/modified:**
- `src/contexts/ToastContext.tsx` — new file
- `src/app/(app)/layout.tsx` — `ToastProvider` added
- `src/components/activities/ActivityCard.tsx` — `useToast()` wired in
- `src/app/(app)/join/page.tsx` — `useToast()` wired in
- `src/app/(app)/activities/new/page.tsx` — `useToast()` wired in

**Before:** Errors and success states were silent or shown as small inline text that users could easily miss.

**After:** A global toast stack that sits in the bottom-right corner of the screen on desktop and stretches full-width at the bottom on mobile.

### How it works
- `ToastProvider` wraps the entire app shell in the `(app)/layout.tsx`
- Any component can call `const { toast } = useToast()` and then `toast({ message: "...", type: "success" | "error" | "info" })`
- Toasts auto-dismiss after 4 seconds with a close button for manual dismiss
- Three types: green (success), red (error), neutral (info)

### Where toasts fire
| Action | Toast |
|---|---|
| Register for activity | ✅ "Registered for [Activity Name]!" |
| Unregister from activity | ℹ️ "Unregistered from [Activity Name]." |
| Register/unregister fails | ❌ Backend error message |
| Join cohort | ✅ "Joined [Cohort Name]!" |
| Join cohort fails | ❌ Backend error message |
| Create activity | ✅ "Activity '[Name]' created!" |
| Create activity fails | ❌ "Failed to create activity." |

---

## Task 9 — Phase 5: Mobile-responsive layout audit

**Files modified:**
- `src/components/layout/CohortSwitcher.tsx`
- `src/app/(app)/activities/new/page.tsx`
- `src/app/(app)/activities/[id]/page.tsx` (duplicate directive removed)

**Findings and fixes:**

### CohortSwitcher (fixed)
The dropdown trigger had a fixed `w-52` (208px) width. On a 320px wide phone with a hamburger icon and logo also in the nav bar, this overflowed the header. Changed to `max-w-[140px] sm:max-w-[208px]` — shrinks on phones, full width on tablets and up.

### Lock row in activity creation form (fixed)
The three-select + delete-button layout used `flex items-center gap-2` with no wrapping. On screens narrower than ~420px the selects would overflow horizontally. Changed to `flex flex-wrap` and added `min-w-[120px]` to each select trigger so they stack gracefully on narrow screens.

### Duplicate `"use client"` directive (fixed)
The activity detail page had `"use client"` written twice at the top. Removed the duplicate.

### Already responsive (no changes needed)
- `TopNav` — already has a full-featured mobile slide-in panel with hamburger button, backdrop, scroll lock, and Escape key handling
- All page grids — already use `grid gap-4 sm:grid-cols-2 lg:grid-cols-3`
- Toast stack — already positioned bottom-center on mobile, bottom-right on desktop
- `AppShell` — uses `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8` throughout
- Loading skeletons — all already use responsive flex/grid layouts
- `not-found.tsx` — uses `min-h-screen flex items-center justify-center`

---

## Task 10 — Phase 5: End-to-end tests for full activity lifecycle

**Files created:**
- `playwright.config.ts`
- `tests/e2e/fixtures.ts`
- `tests/e2e/activity-lifecycle.spec.ts`
- `.env.test.local.example`

**`package.json` changes:**
- Added `@playwright/test ^1.49.0` to `devDependencies`
- Added `test:e2e`, `test:e2e:ui`, `test:e2e:headed` scripts

### How to run the tests

```bash
# 1. Install Playwright (first time only)
cd cohort-shuffle-frontend
npm install
npx playwright install chromium

# 2. Start the backend
cd ../backend
.venv/Scripts/activate   # Windows
uvicorn app.main:app --reload --port 8000

# 3. Copy and fill in test tokens
cd ../cohort-shuffle-frontend
cp .env.test.local.example .env.test.local
# Edit .env.test.local — add E2E_API_TOKEN_ADMIN and E2E_API_TOKEN_STUDENT

# 4. Run the tests (Next.js dev server starts automatically)
npm run test:e2e

# Run with interactive UI
npm run test:e2e:ui
```

### What is tested

**Phase 1 — Login / Sign-in page (UI)**
- Sign-in page renders with heading and Google button
- Unauthenticated access to `/dashboard`, `/activities`, `/teams` redirects to `/sign-in`
- OAuth error codes show a human-readable banner
- 404 page renders for unknown routes

**Phase 2 — Activity creation (API level)**
- Admin fetches cohorts via `/auth/me`
- Admin creates an activity with name, team size, deadline, and event date
- Activity appears in the cohort's activity list

**Phase 2 — Registration (API level)**
- Student registers for the activity
- Registration count increments
- Admin can list all registrations
- Student can unregister
- Student can re-register (for the formation step)

**Phase 4 — Formation (API level)**
- Admin triggers formation via `POST /activities/{id}/form-teams`
- Response contains teams with at least one member each
- `GET /activities/{id}/teams` returns teams and formation logs
- Student can view formed teams
- Student's team history at `/users/me/teams` includes the new activity

**Phase 5 — Error states and mobile (UI)**
- Admin pages redirect unauthenticated users to sign-in
- Sign-in button does not overflow on 375px viewport
- 404 page is usable on mobile

**Backend health**
- `GET /health` returns 200
- Unauthenticated requests to protected endpoints return 401/403

### Notes on OAuth in tests
Google OAuth cannot be automated in a headless browser without test credentials. The API-level lifecycle tests (Steps 1–13) use Bearer tokens set via environment variables and talk to the backend directly — no browser, no OAuth. The UI-level tests only verify page rendering and redirect behaviour for unauthenticated users, which requires no sign-in at all.

---

## Summary of all files changed

| File | Change |
|---|---|
| `src/types/index.ts` | Added `"forming"` to `ActivityStatus` type |
| `src/lib/api/activities.ts` | Added `"forming"` to `ActivityBackend` status type |
| `src/lib/api/teams.ts` | Rewrote to match real `TeamHistoryOut` backend shape |
| `src/lib/api/formation.ts` | Rewrote to bridge real backend shapes (`TeamOut`, `FormationLogOut`) to frontend types |
| `src/contexts/ToastContext.tsx` | New — global toast provider and `useToast()` hook |
| `src/app/(app)/layout.tsx` | Added `ToastProvider` wrapper |
| `src/app/(app)/activities/[id]/page.tsx` | Swapped mock import → real API, added `"forming"` status handling, removed duplicate `"use client"` |
| `src/app/(app)/activities/new/page.tsx` | Added `useToast()`, fixed LockRow mobile wrapping |
| `src/app/(app)/activities/page.tsx` | No changes (already wired) |
| `src/app/(app)/teams/page.tsx` | Rewrote to work with real backend shape, added self-filter and refresh |
| `src/app/(app)/join/page.tsx` | Added `useToast()` to join handlers |
| `src/app/(app)/admin/page.tsx` | No changes (already built) |
| `src/app/(app)/admin/members/page.tsx` | Rewrote — real `fetchCohortMembers` API, search, stats, invite link |
| `src/app/(app)/admin/settings/page.tsx` | Rewrote — cohort info, invite link, add member by email |
| `src/components/activities/ActivityCard.tsx` | Added `"forming"` badge, added `useToast()` to register/unregister |
| `src/components/activities/FormedTeamsView.tsx` | No changes (already built) |
| `src/components/activities/FormationLogPanel.tsx` | No changes (already built) |
| `src/components/activities/TeamEditView.tsx` | No changes (already built) |
| `src/components/layout/CohortSwitcher.tsx` | Fixed fixed-width overflow on mobile |
| `playwright.config.ts` | New — Playwright E2E configuration |
| `tests/e2e/fixtures.ts` | New — shared API client helpers |
| `tests/e2e/activity-lifecycle.spec.ts` | New — 13-step full lifecycle E2E tests |
| `.env.test.local.example` | New — E2E environment variable template |
| `package.json` | Added `@playwright/test`, added `test:e2e` scripts |
