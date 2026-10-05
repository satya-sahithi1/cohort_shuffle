import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { Users, UserPlus, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Cohort Members — Cohort Shuffle",
};

export default async function AdminMembersPage() {
  const session = await auth();
  if (!session) redirect("/sign-in");
  if (session.user.role !== "admin") redirect("/dashboard");

  return (
    <div className="space-y-6">
      {/* Back */}
      <Button variant="ghost" size="sm" asChild>
        <Link href="/admin">
          <ArrowLeft className="mr-1.5 h-4 w-4" />
          Back to admin
        </Link>
      </Button>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Cohort members
          </h1>
          <p className="text-sm text-muted-foreground">
            Manage the student roster — invite new members, view roles, and
            archive departing students.
          </p>
        </div>
        <Button size="sm" disabled>
          <UserPlus className="mr-1.5 h-4 w-4" />
          Invite member
        </Button>
      </div>

      {/* Empty state */}
      <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed py-24 text-center">
        <Users className="h-10 w-10 text-muted-foreground/40" />
        <div className="space-y-1">
          <p className="text-sm font-medium text-muted-foreground">
            Member management coming soon
          </p>
          <p className="text-xs text-muted-foreground">
            Student roster, invite links, and archiving will be wired to the
            backend in a future phase.
          </p>
        </div>
      </div>
    </div>
  );
}
