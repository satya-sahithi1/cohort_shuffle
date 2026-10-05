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
// Extends the default Session to carry id and role on the user object.

declare module "next-auth" {
  interface Session {
    user: AppUser;
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
