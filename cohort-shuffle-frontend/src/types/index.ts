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
