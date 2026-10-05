/**
 * Mock data and API stubs for teams.
 *
 * Replace each function body with a real fetch() call against the FastAPI
 * backend when it's ready. All types and function signatures stay the same.
 */

import type { TeamEntry } from "@/types";

// ─── Seed data ────────────────────────────────────────────────────────────────

function daysAgo(d: number): string {
  return new Date(Date.now() - d * 24 * 60 * 60 * 1000).toISOString();
}

/**
 * Mock team history for the current (student) user.
 * Entries are in reverse-chronological order (most recent first).
 */
const _myTeams: TeamEntry[] = [
  {
    teamId: "team-act4-1",
    teamNumber: 3,
    activityId: "act-4",
    activityName: "Code Review Session",
    eventAt: daysAgo(3),
    duration: "1 hour",
    cohortId: "cohort-cs101-2026",
    cohortName: "CS 101 — Autumn 2026",
    teammates: [
      { id: "user-alice", name: "Alice Chen", email: "alice@example.com" },
      { id: "user-bob", name: "Bob Martinez", email: "bob@example.com" },
      { id: "user-eve", name: "Eve Nguyen", email: "eve@example.com" },
    ],
  },
  {
    teamId: "team-past-1",
    teamNumber: 1,
    activityId: "act-past-1",
    activityName: "System Design Kickoff",
    eventAt: daysAgo(14),
    duration: "2 hours",
    cohortId: "cohort-cs101-2026",
    cohortName: "CS 101 — Autumn 2026",
    teammates: [
      { id: "user-carol", name: "Carol Patel", email: "carol@example.com" },
      { id: "user-dave", name: "Dave Kim", email: "dave@example.com" },
      { id: "user-frank", name: "Frank Osei", email: "frank@example.com" },
    ],
  },
  {
    teamId: "team-past-2",
    teamNumber: 4,
    activityId: "act-past-2",
    activityName: "UX Critique Pairs",
    eventAt: daysAgo(7),
    duration: "45 minutes",
    cohortId: "cohort-design-2026",
    cohortName: "UX Design Studio — 2026",
    teammates: [
      { id: "user-grace", name: "Grace Lee", email: "grace@example.com" },
    ],
  },
  {
    teamId: "team-past-3",
    teamNumber: 2,
    activityId: "act-past-3",
    activityName: "Intro to REST APIs",
    eventAt: daysAgo(21),
    duration: "90 minutes",
    cohortId: "cohort-cs101-2026",
    cohortName: "CS 101 — Autumn 2026",
    teammates: [
      { id: "user-henry", name: "Henry Park", email: "henry@example.com" },
      { id: "user-iris", name: "Iris Wong", email: "iris@example.com" },
      { id: "user-jake", name: "Jake Morin", email: "jake@example.com" },
    ],
  },
];

// ─── API stubs ────────────────────────────────────────────────────────────────

/**
 * GET /users/me/teams
 * Returns the full team history for the current user across all cohorts,
 * most recent first.
 */
export async function fetchMyTeams(): Promise<TeamEntry[]> {
  await new Promise((r) => setTimeout(r, 350));
  return [..._myTeams];
}

/**
 * GET /users/me/teams?cohortId=:id
 * Returns the team history filtered to a specific cohort.
 */
export async function fetchMyTeamsByCohort(
  cohortId: string
): Promise<TeamEntry[]> {
  await new Promise((r) => setTimeout(r, 300));
  return _myTeams.filter((t) => t.cohortId === cohortId);
}

/**
 * GET /activities/:id/teams
 * Returns all teams for a specific activity (admin use — post-formation).
 * Mock returns an empty array until formation is wired up in Phase 3.
 */
export async function fetchTeamsForActivity(
  _activityId: string
): Promise<TeamEntry[]> {
  await new Promise((r) => setTimeout(r, 300));
  return [];
}
