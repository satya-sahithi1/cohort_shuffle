# Phase 0 — Foundation & Auth

## Overview

Phase 0 establishes the entire foundation the app runs on. Nothing in later phases works without this: no page loads correctly without auth, no data is scoped correctly without the cohort context, and no role-based UI works without the route guards.

**Stack:** Next.js (App Router) · TypeScript · Tailwind CSS · shadcn/ui · NextAuth.js v5 (beta)

---

## What gets built

### 1. Project scaffold

- Next.js app with TypeScript, Tailwind, and shadcn/ui initialized
- `src/` directory layout with `app/`, `components/`, `lib/`, `hooks/`, and `types/` folders
- Path alias `@/*` pointing to `src/`

---

### 2. Google OAuth via NextAuth.js

Authentication is Google-only. No passwords are stored anywhere.

**How it works:**

1. User hits the sign-in page and clicks "Sign in with Google"
2. Google OAuth flow runs; on success NextAuth creates a session
3. Session contains: `user.id`, `user.email`, `user.name`, `user.image`, `user.role`
4. `role` is fetched from the backend on the first login and stored in the JWT

**Config location:** `src/auth.ts` (NextAuth config) + `src/app/api/auth/[...nextauth]/route.ts` (route handler)

**Environment variables needed (`.env.local`):**
```
NEXTAUTH_SECRET=
NEXTAUTH_URL=http://localhost:3000
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

---

### 3. Route guards (middleware)

File: `src/middleware.ts`

| Route pattern | Rule |
|---|---|
| `/sign-in` | Redirect to `/dashboard` if already authenticated |
| `/dashboard/*`, `/activities/*`, `/teams/*` | Redirect to `/sign-in` if not authenticated |
| `/admin/*` | Redirect to `/dashboard` if authenticated but not admin |

The middleware reads the NextAuth session token directly (no extra DB call) to keep latency low.

---

### 4. Global layout shell

File: `src/components/layout/AppShell.tsx`

Renders for every authenticated route. Contains:

- **Top nav bar** — app name/logo on the left, cohort switcher in the center, user menu on the right
- **Cohort switcher** — dropdown listing all cohorts the user belongs to; selecting one sets the active cohort in context
- **User menu** (avatar dropdown) — shows name + email, role badge, "Sign out" action
- **Role-aware nav links** — students see "Activities" and "My Teams"; admins additionally see "Manage" (admin dashboard link)

The shell is applied via `src/app/(app)/layout.tsx` — all authenticated pages live under the `(app)` route group.

---

### 5. Cohort context

File: `src/contexts/CohortContext.tsx`

A React context that:

- Fetches the user's cohort memberships from the backend on mount (after login)
- Exposes: `cohorts`, `activeCohort`, `setActiveCohort`, `isLoading`
- Persists the last active cohort ID in `localStorage` so switching tabs doesn't reset it
- All subsequent API calls (activities, teams, roster) are scoped to `activeCohort.id`

**Shape:**
```ts
type Cohort = {
  id: string;
  name: string;
  role: "admin" | "student"; // role is per-cohort
};

type CohortContextValue = {
  cohorts: Cohort[];
  activeCohort: Cohort | null;
  setActiveCohort: (cohort: Cohort) => void;
  isLoading: boolean;
};
```

---

### 6. Cohort join flow

Triggered when a newly logged-in user has no cohort memberships yet, or when they land via a join link.

**Two entry points:**

**A. First login (no memberships):**
- User is redirected to `/join` after sign-in
- Page fetches eligible cohorts (matched by email domain against cohort domain restrictions)
- Each eligible cohort is shown as a card; user clicks "Join" to enroll
- If no eligible cohorts exist, a message says to ask an admin for a join link

**B. Join link:**
- URL format: `/join?token=<cohort_join_token>`
- Page validates the token, shows the cohort name, and lets the user confirm joining
- After joining, redirects to `/dashboard`

---

### 7. Sign-in page

Route: `/sign-in`

- Single "Sign in with Google" button (Google branded, per OAuth guidelines)
- App name and tagline above the button
- No email/password fields — Google only
- Redirects to `/join` if user has no cohorts, otherwise to `/dashboard`

**Sign-out:**
- Triggered from the user menu in the nav
- Calls `signOut()` from NextAuth, clears the session, redirects to `/sign-in`
- Active cohort is cleared from `localStorage` on sign-out

---

## File structure after Phase 0

```
src/
├── app/
│   ├── (app)/                        # authenticated route group
│   │   ├── layout.tsx                # AppShell wrapper
│   │   ├── dashboard/
│   │   │   └── page.tsx              # placeholder dashboard
│   │   └── join/
│   │       └── page.tsx              # cohort join flow
│   ├── api/
│   │   └── auth/
│   │       └── [...nextauth]/
│   │           └── route.ts          # NextAuth route handler
│   ├── sign-in/
│   │   └── page.tsx                  # sign-in page
│   ├── layout.tsx                    # root layout (SessionProvider)
│   └── globals.css
├── auth.ts                           # NextAuth config
├── middleware.ts                     # route guards
├── components/
│   ├── layout/
│   │   ├── AppShell.tsx
│   │   ├── TopNav.tsx
│   │   ├── CohortSwitcher.tsx
│   │   └── UserMenu.tsx
│   └── ui/                           # shadcn components
├── contexts/
│   └── CohortContext.tsx
├── hooks/
│   └── useCohort.ts                  # convenience hook for CohortContext
├── lib/
│   └── utils.ts                      # shadcn utils
└── types/
    └── index.ts                      # shared TypeScript types
```

---

## What is mocked in Phase 0

Since the backend does not exist yet, two API calls are stubbed:

| Call | Stub location | Notes |
|---|---|---|
| `GET /api/cohorts/mine` | `src/lib/mocks/cohorts.ts` | Returns 1–2 fake cohorts |
| `GET /api/cohorts/eligible` | `src/lib/mocks/cohorts.ts` | Returns eligible cohorts for join flow |

Stubs return typed data matching the real shapes so they can be swapped for real fetch calls in one place.

---

## Definition of done

- [ ] `npm run dev` starts without errors
- [ ] Unauthenticated user visiting `/dashboard` is redirected to `/sign-in`
- [ ] Sign-in page loads and shows Google button
- [ ] After mock-login (or real Google login with credentials set), user lands on dashboard shell
- [ ] Cohort switcher shows cohorts from mock data; switching updates the active cohort
- [ ] Student sees "Activities" and "My Teams" in nav; admin additionally sees "Manage"
- [ ] User menu shows name, email, role badge, and sign-out
- [ ] Sign-out clears session and redirects to `/sign-in`
- [ ] Visiting `/admin/*` as a student redirects to `/dashboard`
- [ ] `/join` page shows eligible cohorts or join-link confirmation
