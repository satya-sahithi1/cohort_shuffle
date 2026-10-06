# Frontend Fix Checklist

---

## Setup (must do first)

- [ ] Run `npm install` inside `cohort-shuffle-frontend/`
- [ ] Create `.env.local` with:
  ```
  NEXTAUTH_SECRET=any-random-string
  NEXTAUTH_URL=http://localhost:3000
  NEXT_PUBLIC_API_URL=http://localhost:8000
  GOOGLE_CLIENT_ID=your-id.apps.googleusercontent.com
  GOOGLE_CLIENT_SECRET=your-secret
  ```

---

## Auth fix

- [ ] `auth.ts` issues a NextAuth session token, but the backend expects its own JWT (issued by `/auth/google/callback`). These are two different tokens — need to decide: either use NextAuth's token as-is and remove backend JWT auth, or have NextAuth call the backend after Google login to exchange for a backend JWT and store that as `session.accessToken`.

---

## Missing file

- [ ] Create `src/middleware.ts` — route guards (redirect unauthenticated users to `/sign-in`, redirect non-admins away from `/admin/*`)

---

## Pages using mock data instead of real API

- [ ] `activities/[id]/page.tsx` — formation trigger, team view, and formation logs still import from `lib/mocks/formation` (register/unregister already use real API)
- [ ] `admin/members/page.tsx` — placeholder stub, not wired to `GET /cohorts/{id}/members`
- [ ] `admin/settings/page.tsx` — placeholder stub, not wired to `PATCH /cohorts/{id}`

---

## Pages already wired to real API (no action needed)

- [x] `dashboard/page.tsx` — uses real `fetchActivities`, `fetchMyTeams`
- [x] `activities/page.tsx` — uses real `fetchActivities`, `fetchMyRegistration`
- [x] `activities/new/page.tsx` — uses real `createActivity`, `fetchCohortMembers`
- [x] `sign-in/page.tsx` — uses NextAuth Google provider
- [x] `join/page.tsx` — uses real `fetchEligibleCohorts`, `joinCohort`, `validateJoinToken`

---

## Nice to have

- [ ] End-to-end tests for full activity lifecycle (register → deadline fires → teams formed → student sees teams)
- [ ] Mobile responsive polish
- [ ] Error and empty states (partially done — some pages have them, some don't)
