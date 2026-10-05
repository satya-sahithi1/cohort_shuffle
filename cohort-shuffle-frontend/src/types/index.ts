// ─── User ────────────────────────────────────────────────────────────────────

export type Role = "admin" | "student";

export interface AppUser {
  id: string;
  email: string;
  name: string;
  image?: string;
  /** Global role — only "admin" accounts have admin access. */
  role: Role;
}

// ─── Cohort ──────────────────────────────────────────────────────────────────

export interface Cohort {
  id: string;
  name: string;
  /** The user's role inside this specific cohort. */
  role: Role;
  /** Optional email domain restriction, e.g. "students.university.edu" */
  allowedDomains?: string[];
}

// ─── Activity ────────────────────────────────────────────────────────────────

export type ActivityStatus = "open" | "closed" | "formed";
export type LockConstraintType = "together" | "apart";

export interface ActivityLock {
  id: string;
  userAId: string;
  userAName: string;
  userBId: string;
  userBName: string;
  constraintType: LockConstraintType;
}

export interface Activity {
  id: string;
  cohortId: string;
  name: string;
  teamSize: number;
  /** Human-readable duration, e.g. "2 hours" */
  duration: string;
  /** ISO datetime of the event */
  eventAt: string;
  /** ISO datetime of the registration deadline */
  deadlineAt: string;
  /** null = no cap */
  participantCap: number | null;
  status: ActivityStatus;
  registrationCount: number;
  locks: ActivityLock[];
  createdAt: string;
  formationRunCount: number;
}

// ─── Registration ─────────────────────────────────────────────────────────────

export interface Registration {
  id: string;
  activityId: string;
  userId: string;
  userName: string;
  userEmail: string;
  registeredAt: string;
}

// ─── NextAuth session augmentation ───────────────────────────────────────────
// Extends the default Session and JWT to carry id, role, and accessToken.

declare module "next-auth" {
  interface Session {
    user: AppUser;
    /** The raw JWT string, used by the API client as Bearer token. */
    accessToken: string;
  }

  interface User {
    role: Role;
  }

  interface JWT {
    id: string;
    role: Role;
  }
}

// ─── Teams ───────────────────────────────────────────────────────────────────

export interface Teammate {
  id: string;
  name: string;
  email: string;
}

/**
 * One entry in a student's team history.
 * Maps to a team_members row joined with teams + activities.
 */
export interface TeamEntry {
  /** The team's UUID */
  teamId: string;
  /** e.g. "Team 3" */
  teamNumber: number;
  activityId: string;
  activityName: string;
  /** ISO datetime of the activity */
  eventAt: string;
  /** Human-readable duration string, e.g. "2 hours" */
  duration: string;
  cohortId: string;
  cohortName: string;
  /** Other students on the same team (excludes the viewer themselves) */
  teammates: Teammate[];
}

// ─── Formation ───────────────────────────────────────────────────────────────

/** One formed team inside a single activity — used for the post-formation view. */
export interface FormedTeam {
  teamId: string;
  teamNumber: number;
  /** All members of this team (admin sees everyone; student view filters to their own) */
  members: Teammate[];
}

/**
 * What the API returns when formation is triggered or when teams are fetched
 * post-formation.
 */
export interface FormationResult {
  activityId: string;
  runNumber: number;
  teams: FormedTeam[];
  /** Lower = fewer repeats = better */
  score: number;
  repeatPairs: number;
  /** 0–1 fraction of all possible pairs already met */
  saturation: number;
  /** true when saturation >= 0.80 — show the admin a warning */
  saturated: boolean;
  /** Student IDs who have no new teammate in this run (fairness violation) */
  unfairStudents: string[];
  /** Lock constraints that could not be satisfied */
  unsatisfiedLocks: ActivityLock[];
  triggeredAt: string;
}

/** One row in the formation log — a record of a single formation run. */
export interface FormationLog {
  id: string;
  activityId: string;
  runNumber: number;
  /** null = triggered automatically at deadline */
  triggeredBy: string | null;
  triggeredByName: string | null;
  score: number;
  repeatPairs: number;
  saturation: number;
  createdAt: string;
}
