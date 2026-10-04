import { auth } from "@/auth";
import { redirect } from "next/navigation";

export default async function DashboardPage() {
  const session = await auth();
  if (!session) redirect("/sign-in");

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome back, {session.user.name?.split(" ")[0]}.
        </p>
      </div>

      {/* Phase 1 will fill this with real content */}
      <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
        Activities and team summaries will appear here.
      </div>
    </div>
  );
}
