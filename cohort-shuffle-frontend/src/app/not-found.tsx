import Link from "next/link";
import { Shuffle } from "lucide-react";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Page Not Found — Cohort Shuffle",
};

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
        <Shuffle className="h-7 w-7" />
      </div>

      <div className="space-y-2">
        <h1 className="text-4xl font-bold tracking-tight">404</h1>
        <p className="text-lg font-medium">Page not found</p>
        <p className="text-sm text-muted-foreground">
          This page doesn't exist or you don't have access to it.
        </p>
      </div>

      <Link
        href="/dashboard"
        className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/80"
      >
        Go to Dashboard
      </Link>
    </div>
  );
}
