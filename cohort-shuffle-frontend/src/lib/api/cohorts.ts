/**
 * lib/api/cohorts.ts — Real API calls for cohorts and members.
 *
 * Drop-in replacement for lib/mocks/cohorts.ts.
 *
 * Backend endpoints consumed:
 *   GET  /auth/me           → user's own cohort memberships
 *   GET  /cohorts/eligible  → cohorts the user can join
 *   POST /cohorts/{id}/join
 *   GET  /cohorts/join-link?token=...
 *   GET  /cohorts/{id}/members
 */

import type { Cohort } from "@/types";
import { apiFetch } from "./client";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface CohortMember {
  id: string;
  name: string;
  email: string;
  role: "admin" | "student";
}

interface CohortBackend {
  id: string;
  name: string;
  role: "admin" | "student";
  allowed_domain?: string | null;
}

interface MemberBackend {
  user_id: string;
  name: string;
  email: string;
  role: "admin" | "student";
}

// ─── Converters ───────────────────────────────────────────────────────────────

function toCohort(b: CohortBackend): Cohort {
  return {
    id: b.id,
    name: b.name,
    role: b.role,
    ...(b.allowed_domain ? { allowedDomains: [b.allowed_domain] } : {}),
  };
}

function toMember(b: MemberBackend): CohortMember {
  return {
    id: b.user_id,
    name: b.name,
    email: b.email,
    role: b.role,
  };
}

// ─── API functions ────────────────────────────────────────────────────────────

/** GET /auth/me — returns the cohorts the signed-in user belongs to */
export async function fetchMyCohorts(): Promise<Cohort[]> {
  const data = await apiFetch<{ cohorts: CohortBackend[] }>("/auth/me");
  return data.cohorts.map(toCohort);
}

/** GET /cohorts/eligible — cohorts the user can join (domain-matched) */
export async function fetchEligibleCohorts(): Promise<Cohort[]> {
  const data = await apiFetch<CohortBackend[]>("/cohorts/eligible");
  return data.map(toCohort);
}

/** POST /cohorts/:id/join */
export async function joinCohort(cohortId: string): Promise<void> {
  await apiFetch(`/cohorts/${cohortId}/join`, { method: "POST" });
}

/** GET /cohorts/join-link?token=:token */
export async function validateJoinToken(
  token: string
): Promise<Cohort | null> {
  try {
    const data = await apiFetch<CohortBackend>(
      `/cohorts/join-link?token=${encodeURIComponent(token)}`
    );
    return toCohort(data);
  } catch (e: unknown) {
    if ((e as { status?: number })?.status === 404) return null;
    throw e;
  }
}

/** GET /cohorts/:id/members (admin) */
export async function fetchCohortMembers(
  cohortId: string
): Promise<CohortMember[]> {
  const data = await apiFetch<MemberBackend[]>(`/cohorts/${cohortId}/members`);
  return data.map(toMember);
}
