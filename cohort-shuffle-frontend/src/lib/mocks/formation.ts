/**
 * lib/mocks/formation.ts — Mock data and stubs for formation operations.
 *
 * Replace each function body with a real fetch() call when the backend is ready.
 * Signatures stay the same.
 */

import type { FormationLog, FormationResult, FormedTeam, Activity } from "@/types";

// ─── Seed helpers ─────────────────────────────────────────────────────────────

function minutesAgo(m: number): string {
  return new Date(Date.now() - m * 60 * 1000).toISOString();
}
function daysAgo(d: number): string {
  return new Date(Date.now() - d * 24 * 60 * 60 * 1000).toISOString();
}

// ─── In-memory store ──────────────────────────────────────────────────────────

/**
 * Mock state per activity.
 * act-4 is pre-formed so the UI can show the formed state immediately.
 */
const _formationResults: Record<string, FormationResult> = {
  "act-4": {
    activityId: "act-4",
    runNumber: 1,
    teams: [
      {
        teamId: "team-4-1",
        teamNumber: 1,
        members: [
          { id: "user-alice", name: "Alice Chen", email: "alice@example.com" },
          { id: "user-bob", name: "Bob Martinez", email: "bob@example.com" },
          { id: "user-carol", name: "Carol Patel", email: "carol@example.com" },
          { id: "user-dave", name: "Dave Kim", email: "dave@example.com" },
        ],
      },
      {
        teamId: "team-4-2",
        teamNumber: 2,
        members: [
          { id: "user-eve", name: "Eve Nguyen", email: "eve@example.com" },
          { id: "user-frank", name: "Frank Osei", email: "frank@example.com" },
          { id: "user-grace", name: "Grace Lee", email: "grace@example.com" },
          { id: "user-henry", name: "Henry Park", email: "henry@example.com" },
        ],
      },
      {
        teamId: "team-4-3",
        teamNumber: 3,
        members: [
          { id: "user-iris", name: "Iris Wong", email: "iris@example.com" },
          { id: "user-jake", name: "Jake Morin", email: "jake@example.com" },
          { id: "user-me", name: "You", email: "me@example.com" },
          { id: "user-lena", name: "Lena Ford", email: "lena@example.com" },
        ],
      },
    ],
    score: 2,
    repeatPairs: 2,
    saturation: 0.31,
    saturated: false,
    unfairStudents: [],
    unsatisfiedLocks: [],
    triggeredAt: daysAgo(3),
  },
};

const _formationLogs: Record<string, FormationLog[]> = {
  "act-4": [
    {
      id: "log-4-1",
      activityId: "act-4",
      runNumber: 1,
      triggeredBy: null,
      triggeredByName: null,
      score: 2,
      repeatPairs: 2,
      saturation: 0.31,
      createdAt: daysAgo(3),
    },
  ],
};

// ─── Mutation helpers ─────────────────────────────────────────────────────────

let _runCounter: Record<string, number> = { "act-4": 1 };

function _makeTeams(activityId: string, runNumber: number): FormationResult {
  // Simulate: first run has 0 repeats, later runs have a few
  const isFirstEver = runNumber === 1;
  const saturation = Math.min(0.1 * runNumber, 0.95);
  const saturated = saturation >= 0.8;
  const repeatPairs = isFirstEver ? 0 : runNumber - 1;

  const teams: FormedTeam[] = [
    {
      teamId: `team-${activityId}-${runNumber}-1`,
      teamNumber: 1,
      members: [
        { id: "user-alice", name: "Alice Chen", email: "alice@example.com" },
        { id: "user-bob", name: "Bob Martinez", email: "bob@example.com" },
        { id: "user-carol", name: "Carol Patel", email: "carol@example.com" },
      ],
    },
    {
      teamId: `team-${activityId}-${runNumber}-2`,
      teamNumber: 2,
      members: [
        { id: "user-dave", name: "Dave Kim", email: "dave@example.com" },
        { id: "user-eve", name: "Eve Nguyen", email: "eve@example.com" },
        { id: "user-me", name: "You", email: "me@example.com" },
      ],
    },
  ];

  return {
    activityId,
    runNumber,
    teams,
    score: repeatPairs,
    repeatPairs,
    saturation,
    saturated,
    unfairStudents: [],
    unsatisfiedLocks: [],
    triggeredAt: new Date().toISOString(),
  };
}

// ─── API stubs ────────────────────────────────────────────────────────────────

/**
 * POST /activities/:id/form-teams
 * Admin triggers formation manually. Returns the result.
 * Also mutates the activity's status to "formed".
 */
export async function triggerFormation(
  activityId: string
): Promise<FormationResult> {
  await new Promise((r) => setTimeout(r, 1200)); // simulate algorithm running

  _runCounter[activityId] = (_runCounter[activityId] ?? 0) + 1;
  const runNumber = _runCounter[activityId];
  const result = _makeTeams(activityId, runNumber);
  _formationResults[activityId] = result;

  const logEntry: FormationLog = {
    id: `log-${activityId}-${runNumber}`,
    activityId,
    runNumber,
    triggeredBy: "admin-user",
    triggeredByName: "Admin",
    score: result.score,
    repeatPairs: result.repeatPairs,
    saturation: result.saturation,
    createdAt: new Date().toISOString(),
  };
  _formationLogs[activityId] = [
    logEntry,
    ...(_formationLogs[activityId] ?? []),
  ];

  return result;
}

/**
 * GET /activities/:id/teams
 * Returns the latest formed teams for an activity.
 * Returns null if formation has not run yet.
 */
export async function fetchFormedTeams(
  activityId: string
): Promise<FormationResult | null> {
  await new Promise((r) => setTimeout(r, 300));
  return _formationResults[activityId] ?? null;
}

/**
 * GET /activities/:id/formation-logs
 * Returns the formation history (all runs), most recent first.
 */
export async function fetchFormationLogs(
  activityId: string
): Promise<FormationLog[]> {
  await new Promise((r) => setTimeout(r, 200));
  return _formationLogs[activityId] ?? [];
}

/**
 * POST /activities/:id/validate-locks
 * Checks if the current lock configuration can be satisfied given
 * the registered students. Returns error messages if not.
 *
 * Mock: always returns no errors unless the activity has id "act-lock-bad".
 */
export async function validateLocks(
  activityId: string
): Promise<string[]> {
  await new Promise((r) => setTimeout(r, 200));
  if (activityId === "act-lock-bad") {
    return [
      "Lock error: Alice Chen and Bob Martinez must be together, but their group (3) exceeds team size (2).",
    ];
  }
  return [];
}
