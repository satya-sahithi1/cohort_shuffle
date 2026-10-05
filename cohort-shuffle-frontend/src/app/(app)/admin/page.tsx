import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { Settings, CalendarDays, Users, ArrowRight } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default async function AdminPage() {
  const session = await auth();
  if (!session) redirect("/sign-in");
  if (session.user.role !== "admin") redirect("/dashboard");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Admin</h1>
        <p className="text-sm text-muted-foreground">
          Manage activities, cohort members, and team formation.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Activities */}
        <div className="rounded-xl border bg-card p-5 space-y-3">
          <div className="flex items-center gap-2">
            <CalendarDays className="h-5 w-5 text-primary" />
            <h2 className="font-medium">Activities</h2>
          </div>
          <p className="text-sm text-muted-foreground">
            Create activities, set deadlines, add lock constraints, and trigger
            team formation.
          </p>
          <Button asChild size="sm" variant="outline" className="w-full">
            <Link href="/activities">
              View activities
              <ArrowRight className="ml-1.5 h-4 w-4" />
            </Link>
          </Button>
        </div>

        {/* Members */}
        <div className="rounded-xl border bg-card p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            <h2 className="font-medium">Cohort members</h2>
          </div>
          <p className="text-sm text-muted-foreground">
            Manage the student roster, invite new members, and archive
            departing students.
          </p>
          <Button size="sm" variant="outline" className="w-full" disabled>
            Manage members
            <span className="ml-2 text-xs text-muted-foreground">
              (Phase 1)
            </span>
          </Button>
        </div>

        {/* Settings */}
        <div className="rounded-xl border bg-card p-5 space-y-3">
          <div className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-primary" />
            <h2 className="font-medium">Cohort settings</h2>
          </div>
          <p className="text-sm text-muted-foreground">
            Update the cohort name, domain restriction, and join link.
          </p>
          <Button size="sm" variant="outline" className="w-full" disabled>
            Settings
            <span className="ml-2 text-xs text-muted-foreground">
              (Phase 1)
            </span>
          </Button>
        </div>
      </div>
    </div>
  );
}
