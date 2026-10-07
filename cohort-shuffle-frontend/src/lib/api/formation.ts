/**
 * lib/api/formation.ts — Real API calls for team formation.
 *
 * Backend endpoints consumed:
 *   POST /activities/{id}/form-teams          trigger formation (admin)
 *   GET  /activities/{id}/teams               fetch teams + logs
 *   PATCH /teams/{id}/members                 replace team members (admin)
 *
 * The backend returns different shapes to what the frontend FormationResult
 * type expects, so this module bridges the two.
 *
 * Backend shapes:
 *   POST /form-teams  → TeamOut[]
 *   GET  /teams       → { teams: TeamOut[], logs: FormationLogOut[] }
 *   PATCH /members    → TeamOut  (the updated team)
 *
 * Frontend shapes (used by all components):
 *   FormationResult   { activityId, runNumber, teams: FormedTeam[], score, ... }
 *   FormationLog      { id, activityId, runNumber, ... }
 */

import type { FormationLog, FormationResult, FormedTeam } from "@/types";
import { apiFetch } from "./client";

// ─── Backend shapes ───────────────────────────────────────────────────────────

interface TeamMemberBackend {
  user_id: string;
  name: string;
  email: string;
}

interface TeamOutBackend {
  id: string;
  activity_id: string;
  team_number: number;
  formation_run: number;
  members: TeamMemberBackend[];
}

interface FormationLogBackend {
  id: string;
  activity_id: string;
  run_number: number;
  triggered_by: string | null;
  score: number;
  repeat_pairs: number;
  saturation: number;
  random_seed: number | null;
  created_at: string;
}

interface ActivityTeamsBackend {
  teams: TeamOutBackend[];
  logs: FormationLogBackend[];
}

// ─── Converters ───────────────────────────────────────────────────────────────

function toFormedTeam(b: TeamOutBackend): FormedTeam {
  return {
    teamId: b.id,
    teamNumber: b.team_number,
    members: b.members.map((m) => ({
      id: m.user_id,
      name: m.name,
      email: m.email,
    })),
  };
}

/**
 * The backend POST /form-teams returns only the teams list.
 * We synthesise a FormationResult from the teams + latest log.
 */
function teamsToFormationResult(
  activityId: string,
  teams: TeamOutBackend[],
  log?: FormationLogBackend
): FormationResult {
  const runNumber = teams[0]?.formation_run ?? log?.run_number ?? 1;
  return {
    activityId,
    runNumber,
    teams: teams.map(toFormedTeam),
    score: log?.score ?? 0,
    repeatPairs: log?.repeat_pairs ?? 0,
    saturation: log?.saturation ?? 0,
    saturated: (log?.saturation ?? 0) >= 0.8,
    unfairStudents: [],
    unsatisfiedLocks: [],
    triggeredAt: log?.created_at ?? new Date().toISOString(),
  };
}

function toFormationLog(b: FormationLogBackend): FormationLog {
  return {
    id: b.id,
    activityId: b.activity_id,
    runNumber: b.run_number,
    triggeredBy: b.triggered_by,
    triggeredByName: null, // backend doesn't return the name in the log
    score: b.score,
    repeatPairs: b.repeat_pairs,
    saturation: b.saturation,
    createdAt: b.created_at,
  };
}

// ─── API functions ────────────────────────────────────────────────────────────

/**
 * POST /activities/:id/form-teams — admin triggers formation.
 * Backend returns the newly formed teams (TeamOut[]).
 * We fetch the logs immediately after to build a full FormationResult.
 */
export async function triggerFormation(
  activityId: string
): Promise<FormationResult> {
  const teams = await apiFetch<TeamOutBackend[]>(
    `/activities/${activityId}/form-teams`,
    { method: "POST" }
  );

  // Fetch logs so we can populate score/saturation on the FormationResult
  let log: FormationLogBackend | undefined;
  try {
    const combined = await apiFetch<ActivityTeamsBackend>(
      `/activities/${activityId}/teams`
    );
    log = combined.logs[0]; // latest log is first
  } catch {
    // best-effort — proceed without log stats
  }

  return teamsToFormationResult(activityId, teams, log);
}

/**
 * GET /activities/:id/teams — fetch latest formed teams + logs.
 * Returns null if the activity is not yet formed (404 or 409 from backend).
 */
export async function fetchFormedTeams(
  activityId: string
): Promise<FormationResult | null> {
  try {
    const data = await apiFetch<ActivityTeamsBackend>(
      `/activities/${activityId}/teams`
    );
    const log = data.logs[0];
    return teamsToFormationResult(activityId, data.teams, log);
  } catch (e: unknown) {
    const status = (e as { status?: number })?.status;
    if (status === 404 || status === 409) return null;
    throw e;
  }
}

/**
 * Fetch formation logs for an activity (extracted from the combined endpoint).
 */
export async function fetchFormationLogs(
  activityId: string
): Promise<FormationLog[]> {
  try {
    const data = await apiFetch<ActivityTeamsBackend>(
      `/activities/${activityId}/teams`
    );
    return data.logs.map(toFormationLog);
  } catch (e: unknown) {
    const status = (e as { status?: number })?.status;
    if (status === 404 || status === 409) return [];
    throw e;
  }
}

/**
 * POST /activities/:id/validate-locks — pre-flight lock check.
 * NOTE: This endpoint may not exist in the current backend implementation.
 * We return an empty errors array (no errors) if the endpoint 404s.
 */
export async function validateLocks(activityId: string): Promise<string[]> {
  try {
    const data = await apiFetch<{ errors: string[] }>(
      `/activities/${activityId}/validate-locks`,
      { method: "POST" }
    );
    return data.errors;
  } catch (e: unknown) {
    const status = (e as { status?: number })?.status;
    if (status === 404 || status === 405) return []; // endpoint not implemented
    throw e;
  }
}

/**
 * PATCH /teams/:teamId/members
 * Moves a student from one team to another by:
 *   1. Finding the target team's current members
 *   2. Finding the source team (the team the student is currently on)
 *   3. Sending two PATCH requests to swap the student
 *
 * Returns an updated FormationResult built from the latest GET /teams.
 */
export async function moveStudentBetweenTeams(
  activityId: string,
  studentId: string,
  targetTeamId: string
): Promise<FormationResult> {
  // Fetch current state to know what teams exist and what members they have
  const current = await apiFetch<ActivityTeamsBackend>(
    `/activities/${activityId}/teams`
  );

  const targetTeam = current.teams.find((t) => t.id === targetTeamId);
  if (!targetTeam) {
    throw new Error("Target team not found.");
  }

  // Find the source team (the one containing the student)
  const sourceTeam = current.teams.find((t) =>
    t.members.some((m) => m.user_id === studentId)
  );
  if (!sourceTeam) {
    throw new Error("Student not found in any team.");
  }

  // Build new member lists:
  //   - source team: remove the student
  //   - target team: add the student
  const newSourceMembers = sourceTeam.members
    .filter((m) => m.user_id !== studentId)
    .map((m) => m.user_id);

  const newTargetMembers = [
    ...targetTeam.members.map((m) => m.user_id),
    studentId,
  ];

  // Patch both teams (source first so the student isn't on two teams momentarily)
  if (newSourceMembers.length > 0) {
    await apiFetch(`/teams/${sourceTeam.id}/members`, {
      method: "PATCH",
      body: JSON.stringify({ user_ids: newSourceMembers }),
    });
  }

  await apiFetch(`/teams/${targetTeamId}/members`, {
    method: "PATCH",
    body: JSON.stringify({ user_ids: newTargetMembers }),
  });

  // Re-fetch the full updated state
  const updated = await apiFetch<ActivityTeamsBackend>(
    `/activities/${activityId}/teams`
  );
  const log = updated.logs[0];
  return teamsToFormationResult(activityId, updated.teams, log);
}
