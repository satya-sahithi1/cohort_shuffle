/**
 * lib/api/client.ts — Base fetch wrapper.
 *
 * All API calls go through `apiFetch()`. It:
 *   - Prepends the backend base URL
 *   - Attaches the NextAuth session token as a Bearer header
 *   - Throws a typed ApiError with the server's detail message on non-2xx
 */

import { getSession } from "next-auth/react";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Error type ───────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ─── Core fetch wrapper ───────────────────────────────────────────────────────

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  // Grab the session token so the backend can identify the user
  const session = await getSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // non-JSON error body — use status text
    }
    throw new ApiError(res.status, detail);
  }

  // 204 No Content — return empty object cast to T
  if (res.status === 204) {
    return {} as T;
  }

  return res.json() as Promise<T>;
}
