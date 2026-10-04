import { redirect } from "next/navigation";

// The root URL redirects to dashboard.
// Middleware will redirect unauthenticated users to /sign-in from there.
export default function RootPage() {
  redirect("/dashboard");
}
