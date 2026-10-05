"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import {
  CalendarDays,
  Users,
  ArrowRight,
  Loader2,
  CheckCircle2,
  Clock,
  Timer,
  UserCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useCohort } from "@/contexts/CohortContext";
import { fetchActivities } from "@/lib/mocks/activities";
import { fetchMyTeams } from "@/lib/mocks/teams";
import type { Activity, TeamEntry } from "@/types";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  return `${Math.floor(days / 30)}mo ago`;
}

function deadlineLabel(deadlineIso: string): {
  label: string;
  urgent: boolean;
} {
  const diff = new Date(deadlineIso).getTime() - Date.now();
  if (diff <= 0) return { label: "Deadline passed", urgent: true };
  const hours = Math.floor(diff / (1000 * 60 * 60));
  if (hours < 1) {
    const m = Math.floor(diff / (1000 * 60));
    return { label: `${m}m to register`, urgent: true };
  }
  if (hours < 24)
    return { label: `${hours}h to register`, urgent: hours < 4 };
  const days = Math.floor(hours / 24);
  return { label: `${days}d to register`, urgent: false };
}

// ─── Upcoming activity row ────────────────────────────────────────────────────

function ActivityRow({
  activity,
  isRegistered,
}: {
  activity: Activity;
  isRegistered: boolean;
}) {
  const dl = deadlineLabel(activity.deadlineAt);
  return (
    <Link
      href={`/activities/${activity.id}`}
      className="group flex items-start justify-between gap-3 rounded-lg border bg-card p-4 transition-shadow hover:shadow-sm"
    >
      <div className="min-w-0 flex-1 space-y-1.5">
        <p className="truncate font-medium group-hover:underline underline-offset-2">
          {activity.name}
        </p>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <CalendarDays className="h-3.5 w-3.5 shrink-0" />
            {formatDate(activity.eventAt)}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-3.5 w-3.5 shrink-0" />
            {activity.duration}
          </span>
          <span className="flex items-center gap-1">
            <Users className="h-3.5 w-3.5 shrink-0" />
            Teams of {activity.teamSize}
          </span>
        </div>
        <div
          className={`flex items-center gap-1.5 text-xs font-medium ${
            dl.urgent ? "text-orange-600" : "text-muted-foreground"
          }`}
        >
          <Timer className="h-3.5 w-3.5 shrink-0" />
          {dl.label}
        </div>
      </div>

      <div className="flex shrink-0 flex-col items-end gap-2">
        {isRegistered ? (
          <Badge
            variant="outline"
            className="gap-1 border-green-300 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950/40 dark:text-green-400"
          >
            <CheckCircle2 className="h-3 w-3" />
            Registered
          </Badge>
        ) : (
          <Badge variant="secondary">Register →</Badge>
        )}
      </div>
    </Link>
  );
}

// ─── Team snippet row ─────────────────────────────────────────────────────────

function TeamRow({ entry }: { entry: TeamEntry }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border bg-card p-4">
      <div className="min-w-0 flex-1 space-y-1">
        <p className="truncate font-medium">{entry.activityName}</p>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary" className="text-xs">
            Team {entry.teamNumber}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {entry.cohortName}
          </span>
        </div>
        {entry.teammates.length > 0 && (
          <div className="flex items-center gap-1.5 pt-1">
            <div className="flex -space-x-1.5">
              {entry.teammates.slice(0, 4).map((t) => (
                <div
                  key={t.id}
                  title={t.name}
                  className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-background bg-muted"
                >
                  <UserCircle2 className="h-4 w-4 text-muted-foreground" />
                </div>
              ))}
              {entry.teammates.length > 4 && (
                <div className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-background bg-muted text-[10px] text-muted-foreground">
                  +{entry.teammates.length - 4}
                </div>
              )}
            </div>
            <span className="text-xs text-muted-foreground">
              with{" "}
              {entry.teammates
                .slice(0, 2)
                .map((t) => t.name.split(" ")[0])
                .join(", ")}
              {entry.teammates.length > 2
                ? ` + ${entry.teammates.length - 2} more`
                : ""}
            </span>
          </div>
        )}
      </div>
      <span className="shrink-0 text-xs text-muted-foreground">
        {timeAgo(entry.eventAt)}
      </span>
    </div>
  );
}

// ─── Section header ───────────────────────────────────────────────────────────

function SectionHeader({
  title,
  href,
  label,
}: {
  title: string;
  href: string;
  label: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <h2 className="text-base font-semibold">{title}</h2>
      <Button variant="ghost" size="sm" asChild>
        <Link href={href}>
          {label}
          <ArrowRight className="ml-1 h-3.5 w-3.5" />
        </Link>
      </Button>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { data: session } = useSession();
  const { activeCohort, isLoading: cohortLoading } = useCohort();

  const [activities, setActivities] = useState<Activity[]>([]);
  const [teams, setTeams] = useState<TeamEntry[]>([]);
  const [registeredIds] = useState<Set<string>>(new Set(["act-4"])); // mirrors mock
  const [loading, setLoading] = useState(true);

  const firstName = session?.user?.name?.split(" ")[0] ?? "there";

  const load = useCallback(async () => {
    if (!activeCohort) return;
    setLoading(true);
    try {
      const [acts, myTeams] = await Promise.all([
        fetchActivities(activeCohort.id),
        fetchMyTeams(),
      ]);
      // Keep only open activities that haven't passed their deadline
      setActivities(
        acts
          .filter(
            (a) => a.status === "open" && new Date(a.deadlineAt) > new Date()
          )
          .slice(0, 3)
      );
      setTeams(myTeams.slice(0, 3));
    } finally {
      setLoading(false);
    }
  }, [activeCohort]);

  useEffect(() => {
    if (!cohortLoading) load();
  }, [cohortLoading, load]);

  // ── Render ──

  if (cohortLoading || loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Welcome back, {firstName}.
        </h1>
        <p className="text-sm text-muted-foreground">
          {activeCohort?.name ?? "Select a cohort to get started."}
        </p>
      </div>

      {/* No cohort */}
      {!activeCohort && (
        <div className="rounded-xl border border-dashed p-12 text-center text-muted-foreground">
          <p className="text-sm">
            Join or select a cohort to see your activities and teams.
          </p>
          <Button asChild className="mt-4" size="sm" variant="outline">
            <Link href="/join">Browse cohorts</Link>
          </Button>
        </div>
      )}

      {activeCohort && (
        <>
          {/* ── Upcoming activities ── */}
          <section className="space-y-3">
            <SectionHeader
              title="Open activities"
              href="/activities"
              label="All activities"
            />

            {activities.length === 0 ? (
              <div className="rounded-xl border border-dashed p-10 text-center text-sm text-muted-foreground">
                No open activities right now.
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {activities.map((a) => (
                  <ActivityRow
                    key={a.id}
                    activity={a}
                    isRegistered={registeredIds.has(a.id)}
                  />
                ))}
              </div>
            )}
          </section>

          {/* ── Recent teams ── */}
          <section className="space-y-3">
            <SectionHeader
              title="Recent teams"
              href="/teams"
              label="Full history"
            />

            {teams.length === 0 ? (
              <div className="rounded-xl border border-dashed p-10 text-center text-sm text-muted-foreground">
                You haven't been placed on any teams yet.
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {teams.map((t) => (
                  <TeamRow key={t.teamId} entry={t} />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
