/**
 * lib/api/formation.ts — Real API calls for team formation.
 *
 * Drop-in replacement for lib/mocks/formation.ts.
 *
 * Backend endpoints consumed:
 *   POST /activities/{id}/form-teams          trigger formation (admin)
 *   GET  /activities/{id}/teams               fetch formed teams
 *   GET  /activities/{id}/formation-logs      fetch run history
 *   POST /activities/{id}/validate-locks      pre-flight lock check
 */

import type { FormationLog, FormationResult, FormedTeam } from "@/types";
import { apiFetch } from "./client";

// ─── Backend shapes ───────────────────────────────────────────────────────────

interface FormedTeamBackend {
  team_id: string;
  team_number: number;
  members: Array<{ id: string; name: string; email: string }>;
}

interface FormationResultBackend {
  activity_id: string;
  run_number: number;
  teams: FormedTeamBackend[];
  score: number;
  repeat_pairs: number;
  saturation: number;
  saturated: boolean;
  unfair_students: string[];
  unsatisfied_locks: Array<{
    id: string;
    user_a_id: string;
    user_a_name: string;
    user_b_id: string;
    user_b_name: string;
    constraint_type: "together" | "apart";
  }>;
  triggered_at: string;
}

interface FormationLogBackend {
  id: string;
  activity_id: string;
  run_number: number;
  triggered_by: string | null;
  triggered_by_name: string | null;
  score: number;
  repeat_pairs: number;
  saturation: number;
  created_at: string;
}

// ─── Converters ───────────────────────────────────────────────────────────────

function toFormedTeam(b: FormedTeamBackend): FormedTeam {
  return {
    teamId: b.team_id,
    teamNumber: b.team_number,
    members: b.members,
  };
}

function toFormationResult(b: FormationResultBackend): FormationResult {
  return {
    activityId: b.activity_id,
    runNumber: b.run_number,
    teams: b.teams.map(toFormedTeam),
    score: b.score,
    repeatPairs: b.repeat_pairs,
    saturation: b.saturation,
    saturated: b.saturated,
    unfairStudents: b.unfair_students,
    unsatisfiedLocks: b.unsatisfied_locks.map((l) => ({
      id: l.id,
      userAId: l.user_a_id,
      userAName: l.user_a_name,
      userBId: l.user_b_id,
      userBName: l.user_b_name,
      constraintType: l.constraint_type,
    })),
    triggeredAt: b.triggered_at,
  };
}

function toFormationLog(b: FormationLogBackend): FormationLog {
  return {
    id: b.id,
    activityId: b.activity_id,
    runNumber: b.run_number,
    triggeredBy: b.triggered_by,
    triggeredByName: b.triggered_by_name,
    score: b.score,
    repeatPairs: b.repeat_pairs,
    saturation: b.saturation,
    createdAt: b.created_at,
  };
}

// ─── API functions ────────────────────────────────────────────────────────────

/** POST /activities/:id/form-teams — admin triggers formation */
export async function triggerFormation(
  activityId: string
): Promise<FormationResult> {
  const data = await apiFetch<FormationResultBackend>(
    `/activities/${activityId}/form-teams`,
    { method: "POST" }
  );
  return toFormationResult(data);
}

/** GET /activities/:id/teams — fetch latest formed teams */
export async function fetchFormedTeams(
  activityId: string
): Promise<FormationResult | null> {
  try {
    const data = await apiFetch<FormationResultBackend>(
      `/activities/${activityId}/teams`
    );
    return toFormationResult(data);
  } catch (e: unknown) {
    if ((e as { status?: number })?.status === 404) return null;
    throw e;
  }
}

/** GET /activities/:id/formation-logs — fetch run history */
export async function fetchFormationLogs(
  activityId: string
): Promise<FormationLog[]> {
  const data = await apiFetch<FormationLogBackend[]>(
    `/activities/${activityId}/formation-logs`
  );
  return data.map(toFormationLog);
}

/** POST /activities/:id/validate-locks — pre-flight lock check */
export async function validateLocks(activityId: string): Promise<string[]> {
  const data = await apiFetch<{ errors: string[] }>(
    `/activities/${activityId}/validate-locks`,
    { method: "POST" }
  );
  return data.errors;
}

/**
 * PATCH /teams/:teamId/members
 * Moves a student to a different team.
 * Returns the updated full FormationResult.
 */
export async function moveStudentBetweenTeams(
  activityId: string,
  studentId: string,
  targetTeamId: string
): Promise<FormationResult> {
  const data = await apiFetch<FormationResultBackend>(
    `/teams/${targetTeamId}/members`,
    {
      method: "PATCH",
      body: JSON.stringify({
        student_id: studentId,
        action: "move_to_this_team",
      }),
    }
  );
  return toFormationResult(data);
}
