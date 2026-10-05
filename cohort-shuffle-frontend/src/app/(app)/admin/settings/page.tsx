import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { Settings, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Cohort Settings — Cohort Shuffle",
};

export default async function AdminSettingsPage() {
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
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Cohort settings
        </h1>
        <p className="text-sm text-muted-foreground">
          Update the cohort name, allowed email domain, and join link.
        </p>
      </div>

      {/* Empty state */}
      <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed py-24 text-center">
        <Settings className="h-10 w-10 text-muted-foreground/40" />
        <div className="space-y-1">
          <p className="text-sm font-medium text-muted-foreground">
            Settings coming soon
          </p>
          <p className="text-xs text-muted-foreground">
            Cohort name, domain restriction, and join link management will be
            wired to the backend in a future phase.
          </p>
        </div>
      </div>
    </div>
  );
}
