/**
 * lib/api/activities.ts — Real API calls for activities and registrations.
 *
 * Drop-in replacement for lib/mocks/activities.ts.
 * Function signatures and return types are identical — only the internals
 * changed from in-memory arrays to fetch() calls.
 *
 * Backend endpoints consumed:
 *   GET    /cohorts/{cohortId}/activities
 *   GET    /activities/{id}
 *   POST   /cohorts/{cohortId}/activities
 *   PATCH  /activities/{id}
 *   GET    /activities/{id}/register      ← own registration status
 *   POST   /activities/{id}/register
 *   DELETE /activities/{id}/register
 *   GET    /activities/{id}/registrations ← admin list
 */

import type { Activity, Registration } from "@/types";
import { apiFetch } from "./client";

// ─── Shape of the backend ActivityOut response ────────────────────────────────
// The backend uses snake_case; we convert to camelCase for the frontend.

interface ActivityBackend {
  id: string;
  cohort_id: string;
  name: string;
  team_size: number;
  duration: string;
  event_at: string;
  deadline_at: string;
  participant_cap: number | null;
  status: "open" | "closed" | "formed";
  registration_count: number;
  locks: Array<{
    id: string;
    user_a_id: string;
    user_a_name: string;
    user_b_id: string;
    user_b_name: string;
    constraint_type: "together" | "apart";
  }>;
  created_at: string;
  formation_run_count: number;
}

interface RegistrationBackend {
  id: string;
  activity_id: string;
  user_id: string;
  user_name: string;
  user_email: string;
  registered_at: string;
}

// ─── Converters ───────────────────────────────────────────────────────────────

function toActivity(b: ActivityBackend): Activity {
  return {
    id: b.id,
    cohortId: b.cohort_id,
    name: b.name,
    teamSize: b.team_size,
    duration: b.duration,
    eventAt: b.event_at,
    deadlineAt: b.deadline_at,
    participantCap: b.participant_cap,
    status: b.status,
    registrationCount: b.registration_count,
    locks: b.locks.map((l) => ({
      id: l.id,
      userAId: l.user_a_id,
      userAName: l.user_a_name,
      userBId: l.user_b_id,
      userBName: l.user_b_name,
      constraintType: l.constraint_type,
    })),
    createdAt: b.created_at,
    formationRunCount: b.formation_run_count,
  };
}

function toRegistration(b: RegistrationBackend): Registration {
  return {
    id: b.id,
    activityId: b.activity_id,
    userId: b.user_id,
    userName: b.user_name,
    userEmail: b.user_email,
    registeredAt: b.registered_at,
  };
}

// ─── API functions ────────────────────────────────────────────────────────────

/** GET /cohorts/:cohortId/activities */
export async function fetchActivities(cohortId: string): Promise<Activity[]> {
  const data = await apiFetch<ActivityBackend[]>(
    `/cohorts/${cohortId}/activities`
  );
  return data.map(toActivity);
}

/** GET /activities/:id */
export async function fetchActivity(id: string): Promise<Activity | null> {
  try {
    const data = await apiFetch<ActivityBackend>(`/activities/${id}`);
    return toActivity(data);
  } catch (e: unknown) {
    if ((e as { status?: number })?.status === 404) return null;
    throw e;
  }
}

/** GET /activities/:id/register — returns true if the user is registered */
export async function fetchMyRegistration(activityId: string): Promise<boolean> {
  const data = await apiFetch<{ registered: boolean }>(
    `/activities/${activityId}/register`
  );
  return data.registered;
}

/** GET /activities/:id/registrations (admin) */
export async function fetchRegistrations(
  activityId: string
): Promise<Registration[]> {
  const data = await apiFetch<RegistrationBackend[]>(
    `/activities/${activityId}/registrations`
  );
  return data.map(toRegistration);
}

/** POST /activities/:id/register */
export async function registerForActivity(activityId: string): Promise<void> {
  await apiFetch(`/activities/${activityId}/register`, { method: "POST" });
}

/** DELETE /activities/:id/register */
export async function unregisterFromActivity(activityId: string): Promise<void> {
  await apiFetch(`/activities/${activityId}/register`, { method: "DELETE" });
}

/** POST /cohorts/:cohortId/activities (admin) */
export async function createActivity(
  data: Omit<
    Activity,
    "id" | "status" | "registrationCount" | "createdAt" | "formationRunCount"
  >
): Promise<Activity> {
  const body = {
    name: data.name,
    team_size: data.teamSize,
    duration: data.duration,
    event_at: data.eventAt,
    deadline_at: data.deadlineAt,
    participant_cap: data.participantCap ?? null,
    locks: data.locks.map((l) => ({
      user_a_id: l.userAId,
      user_b_id: l.userBId,
      constraint_type: l.constraintType,
    })),
  };
  const result = await apiFetch<ActivityBackend>(
    `/cohorts/${data.cohortId}/activities`,
    {
      method: "POST",
      body: JSON.stringify(body),
    }
  );
  return toActivity(result);
}

/** PATCH /activities/:id (admin) */
export async function updateActivity(
  id: string,
  data: Partial<Omit<Activity, "id" | "cohortId" | "createdAt">>
): Promise<Activity> {
  const body: Record<string, unknown> = {};
  if (data.name !== undefined) body.name = data.name;
  if (data.teamSize !== undefined) body.team_size = data.teamSize;
  if (data.duration !== undefined) body.duration = data.duration;
  if (data.eventAt !== undefined) body.event_at = data.eventAt;
  if (data.deadlineAt !== undefined) body.deadline_at = data.deadlineAt;
  if (data.participantCap !== undefined)
    body.participant_cap = data.participantCap;
  if (data.locks !== undefined)
    body.locks = data.locks.map((l) => ({
      user_a_id: l.userAId,
      user_b_id: l.userBId,
      constraint_type: l.constraintType,
    }));

  const result = await apiFetch<ActivityBackend>(`/activities/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  return toActivity(result);
}
