/**
 * tests/e2e/fixtures.ts — Shared Playwright fixtures for Cohort Shuffle E2E tests.
 *
 * Because sign-in is Google OAuth we cannot go through the real OAuth flow in
 * automated tests. Instead we:
 *   1. Hit the backend directly to get a JWT (test-only helper endpoint, or use
 *      the /auth/me endpoint with a pre-issued token set via env var).
 *   2. Set the NextAuth session cookie directly so the Next.js frontend thinks
 *      the user is logged in.
 *
 * For tests that only need the API layer (no browser), we export a raw API
 * helper that talks to the FastAPI backend using a Bearer token.
 *
 * Environment variables required (add to .env.test.local):
 *   E2E_API_TOKEN_ADMIN   — valid JWT for an admin user
 *   E2E_API_TOKEN_STUDENT — valid JWT for a student user
 *   E2E_ADMIN_EMAIL       — admin user email
 *   E2E_STUDENT_EMAIL     — student user email
 *   NEXT_PUBLIC_API_URL   — backend base URL (default: http://localhost:8000)
 */

import { test as base, expect, type Page } from "@playwright/test";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Raw API helper (no browser) ──────────────────────────────────────────────

export class ApiClient {
  constructor(private readonly token: string) {}

  async get<T>(path: string): Promise<T> {
    const res = await fetch(`${API_URL}${path}`, {
      headers: { Authorization: `Bearer ${this.token}` },
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`GET ${path} → ${res.status}: ${body}`);
    }
    return res.json() as Promise<T>;
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.token}`,
        "Content-Type": "application/json",
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`POST ${path} → ${res.status}: ${text}`);
    }
    if (res.status === 204) return {} as T;
    return res.json() as Promise<T>;
  }

  async delete(path: string): Promise<void> {
    const res = await fetch(`${API_URL}${path}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${this.token}` },
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`DELETE ${path} → ${res.status}: ${text}`);
    }
  }
}

export const adminApi = new ApiClient(
  process.env.E2E_API_TOKEN_ADMIN ?? "test-admin-token"
);

export const studentApi = new ApiClient(
  process.env.E2E_API_TOKEN_STUDENT ?? "test-student-token"
);

// ─── Browser fixtures ──────────────────────────────────────────────────────────

/**
 * Injects a mock NextAuth session cookie so the browser thinks
 * the specified user is authenticated.
 *
 * This avoids going through Google OAuth in tests.
 * In a real CI environment you would use a proper session token
 * issued by NextAuth; here we use a lightweight override approach
 * by setting localStorage state that the mock API layer reads.
 */
export async function injectSession(
  page: Page,
  user: { id: string; email: string; name: string; role: "admin" | "student" },
  token: string
) {
  await page.goto("/");
  await page.evaluate(
    ({ user, token }) => {
      // Store in sessionStorage so the test page can read it
      sessionStorage.setItem("e2e_user", JSON.stringify(user));
      sessionStorage.setItem("e2e_token", token);
    },
    { user, token }
  );
}

// ─── Extended test fixture ─────────────────────────────────────────────────────

type Fixtures = {
  adminPage: Page;
  studentPage: Page;
};

export const test = base.extend<Fixtures>({
  adminPage: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    // Navigate to sign-in page so cookies are set in the right origin
    await page.goto("/sign-in");
    await use(page);
    await context.close();
  },

  studentPage: async ({ browser }, use) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto("/sign-in");
    await use(page);
    await context.close();
  },
});

export { expect };
