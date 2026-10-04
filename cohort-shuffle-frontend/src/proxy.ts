import { auth } from "@/auth";
import { NextResponse } from "next/server";
import type { NextAuthRequest } from "next-auth";

/**
 * Route guard rules:
 *
 * /sign-in          → if already authenticated, redirect to /dashboard
 * /dashboard, /activities, /teams, /join
 *                   → if not authenticated, redirect to /sign-in
 * /admin (and sub-routes)
 *                   → if authenticated but not admin, redirect to /dashboard
 */
export default auth((req: NextAuthRequest) => {
  const { nextUrl } = req;
  const isLoggedIn = !!req.auth?.user;
  const isAdmin = req.auth?.user?.role === "admin";

  const path = nextUrl.pathname;

  // Already signed in → skip sign-in page
  if (path.startsWith("/sign-in") && isLoggedIn) {
    return NextResponse.redirect(new URL("/dashboard", nextUrl));
  }

  // Protected routes — must be authenticated
  const protectedPrefixes = ["/dashboard", "/activities", "/teams", "/join", "/admin"];
  const isProtected = protectedPrefixes.some((prefix) => path.startsWith(prefix));

  if (isProtected && !isLoggedIn) {
    const signInUrl = new URL("/sign-in", nextUrl);
    signInUrl.searchParams.set("callbackUrl", path);
    return NextResponse.redirect(signInUrl);
  }

  // Admin-only routes — must be admin
  if (path.startsWith("/admin") && isLoggedIn && !isAdmin) {
    return NextResponse.redirect(new URL("/dashboard", nextUrl));
  }

  return NextResponse.next();
});

export const config = {
  // Run middleware on all routes except Next.js internals and static files
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
