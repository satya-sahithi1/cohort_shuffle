/**
 * lib/api/teams.ts — Real API calls for team history.
 *
 * Backend endpoints consumed:
 *   GET /users/me/teams   → student's full team history
 *
 * Real backend shape (TeamHistoryOut):
 *   { team_id, team_number, activity_id, activity_name, event_at, members[] }
 *
 * The backend does NOT return duration, cohort_id, cohort_name, or a separate
 * teammates list. We derive teammates from the full members list by removing
 * the current user's id (we don't know it here, so we return all members and
 * let the UI filter). cohortId/cohortName default to empty strings since the
 * backend omits them — the teams page handles this gracefully.
 */

import type { TeamEntry } from "@/types";
import { apiFetch } from "./client";

// ─── Backend shapes ───────────────────────────────────────────────────────────

interface TeamMemberBackend {
  user_id: string;
  name: string;
  email: string;
}

/** What the backend actually returns from GET /users/me/teams */
interface TeamHistoryBackend {
  team_id: string;
  team_number: number;
  activity_id: string;
  activity_name: string;
  event_at: string;
  members: TeamMemberBackend[];
}

// ─── Converter ────────────────────────────────────────────────────────────────

function toTeamEntry(b: TeamHistoryBackend): TeamEntry {
  return {
    teamId: b.team_id,
    teamNumber: b.team_number,
    activityId: b.activity_id,
    activityName: b.activity_name,
    eventAt: b.event_at,
    // Backend does not return duration — show empty string; UI handles gracefully
    duration: "",
    // Backend does not return cohort info on this endpoint
    cohortId: "",
    cohortName: "",
    // All members returned — the UI component uses all of them as teammates
    // (it can subtract the current user if it knows the id)
    teammates: b.members.map((m) => ({
      id: m.user_id,
      name: m.name,
      email: m.email,
    })),
  };
}

// ─── API functions ────────────────────────────────────────────────────────────

/** GET /users/me/teams — full history, newest first */
export async function fetchMyTeams(): Promise<TeamEntry[]> {
  const data = await apiFetch<TeamHistoryBackend[]>("/users/me/teams");
  return data.map(toTeamEntry);
}

/**
 * GET /users/me/teams — the backend does not support ?cohort_id filtering yet.
 * We fetch all teams and filter client-side when cohortId is provided.
 * This is safe because the backend scopes the query to the current user anyway.
 */
export async function fetchMyTeamsByCohort(
  cohortId: string
): Promise<TeamEntry[]> {
  const all = await fetchMyTeams();
  // cohortId filtering is best-effort since the backend omits cohort_id in the response
  return cohortId ? all.filter((t) => t.cohortId === cohortId || t.cohortId === "") : all;
}
