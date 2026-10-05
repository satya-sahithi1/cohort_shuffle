/**
 * Mock data and API stubs for activities.
 *
 * Replace each function body with a real fetch() call against the FastAPI
 * backend when it's ready. All types and function signatures stay the same.
 */

import type { Activity, Registration } from "@/types";

// ─── Seed data ────────────────────────────────────────────────────────────────

const now = new Date();

/** Helpers to build relative ISO strings */
function hoursFromNow(h: number): string {
  return new Date(now.getTime() + h * 60 * 60 * 1000).toISOString();
}
function daysFromNow(d: number): string {
  return new Date(now.getTime() + d * 24 * 60 * 60 * 1000).toISOString();
}
function daysAgo(d: number): string {
  return new Date(now.getTime() - d * 24 * 60 * 60 * 1000).toISOString();
}

/** Mutable in-memory store so register/unregister mutations persist within a session. */
const _activities: Activity[] = [
  {
    id: "act-1",
    cohortId: "cohort-cs101-2026",
    name: "Requirements Analysis Sprint",
    teamSize: 4,
    duration: "2 hours",
    eventAt: hoursFromNow(48),
    deadlineAt: hoursFromNow(46),
    participantCap: null,
    status: "open",
    registrationCount: 18,
    locks: [],
    createdAt: daysAgo(2),
    formationRunCount: 0,
  },
  {
    id: "act-2",
    cohortId: "cohort-cs101-2026",
    name: "API Design Workshop",
    teamSize: 3,
    duration: "90 minutes",
    eventAt: hoursFromNow(72),
    deadlineAt: hoursFromNow(70),
    participantCap: 30,
    status: "open",
    registrationCount: 24,
    locks: [
      {
        id: "lock-1",
        userAId: "user-alice",
        userAName: "Alice Chen",
        userBId: "user-bob",
        userBName: "Bob Martinez",
        constraintType: "together",
      },
    ],
    createdAt: daysAgo(1),
    formationRunCount: 0,
  },
  {
    id: "act-3",
    cohortId: "cohort-cs101-2026",
    name: "Database Schema Review",
    teamSize: 5,
    duration: "3 hours",
    eventAt: daysFromNow(7),
    deadlineAt: daysFromNow(6),
    participantCap: null,
    status: "open",
    registrationCount: 5,
    locks: [],
    createdAt: daysAgo(0),
    formationRunCount: 0,
  },
  {
    id: "act-4",
    cohortId: "cohort-cs101-2026",
    name: "Code Review Session",
    teamSize: 4,
    duration: "1 hour",
    eventAt: daysAgo(3),
    deadlineAt: daysAgo(3),
    participantCap: null,
    status: "formed",
    registrationCount: 32,
    locks: [],
    createdAt: daysAgo(10),
    formationRunCount: 1,
  },
  {
    id: "act-5",
    cohortId: "cohort-design-2026",
    name: "UX Critique Pairs",
    teamSize: 2,
    duration: "45 minutes",
    eventAt: hoursFromNow(24),
    deadlineAt: hoursFromNow(22),
    participantCap: 20,
    status: "open",
    registrationCount: 12,
    locks: [],
    createdAt: daysAgo(1),
    formationRunCount: 0,
  },
];

/** Tracks which activity IDs the current (mocked) user has registered for. */
const _myRegistrations: Set<string> = new Set(["act-4"]);

/** Full registration records per activity (for admin view). */
const _registrations: Record<string, Registration[]> = {
  "act-1": [
    {
      id: "reg-1-1",
      activityId: "act-1",
      userId: "user-alice",
      userName: "Alice Chen",
      userEmail: "alice@example.com",
      registeredAt: daysAgo(1),
    },
    {
      id: "reg-1-2",
      activityId: "act-1",
      userId: "user-bob",
      userName: "Bob Martinez",
      userEmail: "bob@example.com",
      registeredAt: daysAgo(1),
    },
    {
      id: "reg-1-3",
      activityId: "act-1",
      userId: "user-carol",
      userName: "Carol Patel",
      userEmail: "carol@example.com",
      registeredAt: hoursFromNow(-20),
    },
  ],
  "act-2": [
    {
      id: "reg-2-1",
      activityId: "act-2",
      userId: "user-alice",
      userName: "Alice Chen",
      userEmail: "alice@example.com",
      registeredAt: daysAgo(1),
    },
    {
      id: "reg-2-2",
      activityId: "act-2",
      userId: "user-dave",
      userName: "Dave Kim",
      userEmail: "dave@example.com",
      registeredAt: hoursFromNow(-18),
    },
  ],
};

// ─── API stubs ────────────────────────────────────────────────────────────────

/**
 * GET /cohorts/:cohortId/activities
 * Returns all activities for the given cohort, most recent first.
 */
export async function fetchActivities(cohortId: string): Promise<Activity[]> {
  await new Promise((r) => setTimeout(r, 350));
  return _activities
    .filter((a) => a.cohortId === cohortId)
    .sort(
      (a, b) =>
        new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );
}

/**
 * GET /activities/:id
 * Returns a single activity by ID.
 */
export async function fetchActivity(id: string): Promise<Activity | null> {
  await new Promise((r) => setTimeout(r, 250));
  return _activities.find((a) => a.id === id) ?? null;
}

/**
 * GET /activities/:id/my-registration
 * Returns true if the current user is registered for this activity.
 */
export async function fetchMyRegistration(
  activityId: string
): Promise<boolean> {
  await new Promise((r) => setTimeout(r, 150));
  return _myRegistrations.has(activityId);
}

/**
 * GET /activities/:id/registrations   (admin only)
 * Returns the full list of registered students.
 */
export async function fetchRegistrations(
  activityId: string
): Promise<Registration[]> {
  await new Promise((r) => setTimeout(r, 300));
  return _registrations[activityId] ?? [];
}

/**
 * POST /activities/:id/register
 * Registers the current user for the activity.
 */
export async function registerForActivity(activityId: string): Promise<void> {
  await new Promise((r) => setTimeout(r, 400));
  const activity = _activities.find((a) => a.id === activityId);
  if (!activity) throw new Error("Activity not found");
  if (activity.status !== "open") throw new Error("Registration is closed");
  if (
    activity.participantCap !== null &&
    activity.registrationCount >= activity.participantCap
  ) {
    throw new Error("Activity is full");
  }
  _myRegistrations.add(activityId);
  activity.registrationCount++;
}

/**
 * DELETE /activities/:id/register
 * Unregisters the current user from the activity (only before deadline).
 */
export async function unregisterFromActivity(
  activityId: string
): Promise<void> {
  await new Promise((r) => setTimeout(r, 400));
  const activity = _activities.find((a) => a.id === activityId);
  if (!activity) throw new Error("Activity not found");
  if (activity.status !== "open") throw new Error("Deadline has passed");
  _myRegistrations.delete(activityId);
  activity.registrationCount = Math.max(0, activity.registrationCount - 1);
}

/**
 * POST /cohorts/:cohortId/activities   (admin only)
 * Creates a new activity. Returns the created activity.
 */
export async function createActivity(
  data: Omit<Activity, "id" | "status" | "registrationCount" | "createdAt" | "formationRunCount">
): Promise<Activity> {
  await new Promise((r) => setTimeout(r, 600));
  const activity: Activity = {
    ...data,
    id: `act-${Date.now()}`,
    status: "open",
    registrationCount: 0,
    createdAt: new Date().toISOString(),
    formationRunCount: 0,
  };
  _activities.push(activity);
  return activity;
}
