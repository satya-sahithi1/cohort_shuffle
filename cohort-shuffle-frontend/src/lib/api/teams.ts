/**
 * lib/api/teams.ts — Real API calls for team history.
 *
 * Drop-in replacement for lib/mocks/teams.ts.
 *
 * Backend endpoints consumed:
 *   GET /users/me/teams                 → full history
 *   GET /users/me/teams?cohort_id=...   → filtered by cohort
 *   GET /activities/{id}/teams          → all teams for an activity (admin)
 */

import type { TeamEntry, Teammate } from "@/types";
import { apiFetch } from "./client";

// ─── Backend shapes ───────────────────────────────────────────────────────────

interface TeamEntryBackend {
  team_id: string;
  team_number: number;
  activity_id: string;
  activity_name: string;
  event_at: string;
  duration: string;
  cohort_id: string;
  cohort_name: string;
  teammates: Array<{ id: string; name: string; email: string }>;
}

// ─── Converter ────────────────────────────────────────────────────────────────

function toTeamEntry(b: TeamEntryBackend): TeamEntry {
  return {
    teamId: b.team_id,
    teamNumber: b.team_number,
    activityId: b.activity_id,
    activityName: b.activity_name,
    eventAt: b.event_at,
    duration: b.duration,
    cohortId: b.cohort_id,
    cohortName: b.cohort_name,
    teammates: b.teammates,
  };
}

// ─── API functions ────────────────────────────────────────────────────────────

/** GET /users/me/teams */
export async function fetchMyTeams(): Promise<TeamEntry[]> {
  const data = await apiFetch<TeamEntryBackend[]>("/users/me/teams");
  return data.map(toTeamEntry);
}

/** GET /users/me/teams?cohort_id=:id */
export async function fetchMyTeamsByCohort(
  cohortId: string
): Promise<TeamEntry[]> {
  const data = await apiFetch<TeamEntryBackend[]>(
    `/users/me/teams?cohort_id=${encodeURIComponent(cohortId)}`
  );
  return data.map(toTeamEntry);
}

/** GET /activities/:id/teams (admin, post-formation) */
export async function fetchTeamsForActivity(
  activityId: string
): Promise<TeamEntry[]> {
  const data = await apiFetch<TeamEntryBackend[]>(
    `/activities/${activityId}/teams`
  );
  return data.map(toTeamEntry);
}
