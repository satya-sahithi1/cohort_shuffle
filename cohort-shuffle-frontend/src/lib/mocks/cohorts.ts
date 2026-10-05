import type { Cohort } from "@/types";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface CohortMember {
  id: string;
  name: string;
  email: string;
  role: "admin" | "student";
}

// ─── Seed data ────────────────────────────────────────────────────────────────

const _membersByCohort: Record<string, CohortMember[]> = {
  "cohort-cs101-2026": [
    { id: "user-alice", name: "Alice Chen", email: "alice@example.com", role: "student" },
    { id: "user-bob", name: "Bob Martinez", email: "bob@example.com", role: "student" },
    { id: "user-carol", name: "Carol Patel", email: "carol@example.com", role: "student" },
    { id: "user-dave", name: "Dave Kim", email: "dave@example.com", role: "student" },
    { id: "user-eve", name: "Eve Nguyen", email: "eve@example.com", role: "student" },
    { id: "user-frank", name: "Frank Osei", email: "frank@example.com", role: "student" },
    { id: "user-admin", name: "Admin User", email: "admin@example.com", role: "admin" },
  ],
  "cohort-design-2026": [
    { id: "user-grace", name: "Grace Lee", email: "grace@example.com", role: "student" },
    { id: "user-henry", name: "Henry Park", email: "henry@example.com", role: "student" },
    { id: "user-admin", name: "Admin User", email: "admin@example.com", role: "admin" },
  ],
};

/**
 * Stub for GET /cohorts/:id/members
 * Returns all members of a cohort (admin use, for the lock builder).
 */
export async function fetchCohortMembers(
  cohortId: string
): Promise<CohortMember[]> {
  await new Promise((r) => setTimeout(r, 250));
  return _membersByCohort[cohortId] ?? [];
}

// ─────────────────────────────────────────────────────────────────────────────

/**
 * Stub for GET /api/cohorts/mine
 * Returns the cohorts the signed-in user is already a member of.
 * Replace the fetch call in CohortContext with a real API call when the
 * backend is ready.
 */
export async function fetchMyCohorts(): Promise<Cohort[]> {
  // Simulate network latency in dev
  await new Promise((r) => setTimeout(r, 400));

  return [
    {
      id: "cohort-cs101-2026",
      name: "CS 101 — Autumn 2026",
      role: "student",
    },
    {
      id: "cohort-design-2026",
      name: "UX Design Studio — 2026",
      role: "admin",
    },
  ];
}

/**
 * Stub for GET /api/cohorts/eligible
 * Returns cohorts the user can join (domain-matched, not yet a member of).
 */
export async function fetchEligibleCohorts(): Promise<Cohort[]> {
  await new Promise((r) => setTimeout(r, 400));

  return [
    {
      id: "cohort-ml-2026",
      name: "Machine Learning Bootcamp — 2026",
      role: "student",
      allowedDomains: ["students.university.edu"],
    },
  ];
}

/**
 * Stub for POST /api/cohorts/:id/join
 */
export async function joinCohort(cohortId: string): Promise<void> {
  await new Promise((r) => setTimeout(r, 500));
  console.log("[mock] Joined cohort:", cohortId);
}

/**
 * Stub for POST /api/cohorts/join-link
 * Validates a join token and returns the cohort info.
 */
export async function validateJoinToken(
  token: string
): Promise<Cohort | null> {
  await new Promise((r) => setTimeout(r, 400));

  if (token === "demo-token") {
    return {
      id: "cohort-demo-2026",
      name: "Demo Cohort — 2026",
      role: "student",
    };
  }

  return null;
}
