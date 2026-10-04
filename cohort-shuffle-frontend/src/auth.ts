import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import type { Role } from "@/types";

/**
 * Determines the global role for a user.
 *
 * In production this would look up the user record in the database.
 * For now, any email in ADMIN_EMAILS gets the admin role; everyone else
 * is a student.
 */
function resolveRole(email: string): Role {
  const adminEmails = (process.env.ADMIN_EMAILS ?? "")
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);

  return adminEmails.includes(email.toLowerCase()) ? "admin" : "student";
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],

  callbacks: {
    /**
     * Runs when a JWT is created (sign-in) or accessed.
     * Attach the user's id and role so they're available in the session.
     */
    async jwt({ token, user }) {
      if (user) {
        // First sign-in: user object is populated by the provider
        token.id = user.id ?? token.sub ?? "";
        token.role = resolveRole(user.email ?? "");
      }
      return token;
    },

    /**
     * Runs when session() is called. Expose id and role on the session object
     * so client components can read them via useSession().
     */
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string;
        session.user.role = token.role as Role;
      }
      return session;
    },
  },

  pages: {
    signIn: "/sign-in",
    error: "/sign-in", // surface auth errors on the sign-in page
  },
});
