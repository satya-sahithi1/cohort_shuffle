"use client";

import { useCallback, useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import {
  Users,
  Calendar,
  Clock,
  Loader2,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  UserCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useCohort } from "@/contexts/CohortContext";
import { fetchMyTeams, fetchMyTeamsByCohort } from "@/lib/mocks/teams";
import type { TeamEntry } from "@/types";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  if (days < 30) return `${Math.floor(days / 7)}w ago`;
  if (days < 365) return `${Math.floor(days / 30)}mo ago`;
  return `${Math.floor(days / 365)}y ago`;
}

// ─── Team card ────────────────────────────────────────────────────────────────

function TeamCard({ entry }: { entry: TeamEntry }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-xl border bg-card transition-shadow hover:shadow-sm">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3 p-4">
        <div className="min-w-0 flex-1 space-y-1">
          <p className="truncate font-medium leading-snug">
            {entry.activityName}
          </p>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5 shrink-0" />
              {formatDate(entry.eventAt)}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5 shrink-0" />
              {entry.duration}
            </span>
            <span className="flex items-center gap-1">
              <Users className="h-3.5 w-3.5 shrink-0" />
              {entry.teammates.length + 1} members
            </span>
          </div>
        </div>

        <div className="flex shrink-0 flex-col items-end gap-1.5">
          <Badge variant="secondary" className="text-xs">
            Team {entry.teamNumber}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {timeAgo(entry.eventAt)}
          </span>
        </div>
      </div>

      {/* Cohort tag */}
      <div className="border-t px-4 py-2">
        <span className="inline-block rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
          {entry.cohortName}
        </span>
      </div>

      {/* Teammates — collapsible */}
      <div className="border-t">
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex w-full items-center justify-between px-4 py-2.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          aria-expanded={expanded}
        >
          <span>
            {entry.teammates.length === 0
              ? "No teammates (solo)"
              : `${entry.teammates.length} teammate${entry.teammates.length !== 1 ? "s" : ""}`}
          </span>
          {entry.teammates.length > 0 &&
            (expanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            ))}
        </button>

        {expanded && entry.teammates.length > 0 && (
          <ul className="divide-y border-t">
            {entry.teammates.map((t) => (
              <li
                key={t.id}
                className="flex items-center gap-3 px-4 py-2.5"
              >
                <UserCircle2 className="h-5 w-5 shrink-0 text-muted-foreground/60" />
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{t.name}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {t.email}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState({ filtered }: { filtered: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed py-20 text-center">
      <Users className="h-10 w-10 text-muted-foreground/40" />
      <div className="space-y-1">
        <p className="text-sm font-medium text-muted-foreground">
          No teams yet
        </p>
        <p className="text-xs text-muted-foreground">
          {filtered
            ? "You haven't been placed on any teams in this cohort."
            : "Once teams are formed for activities you're in, they'll appear here."}
        </p>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TeamsPage() {
  const { data: session } = useSession();
  const { activeCohort, cohorts, isLoading: cohortLoading } = useCohort();

  const [teams, setTeams] = useState<TeamEntry[]>([]);
  const [filterCohortId, setFilterCohortId] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data =
        filterCohortId === "all"
          ? await fetchMyTeams()
          : await fetchMyTeamsByCohort(filterCohortId);
      setTeams(data);
    } catch {
      setError("Failed to load team history. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [filterCohortId]);

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

  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-center">
        <p className="text-sm text-destructive">{error}</p>
        <Button size="sm" variant="outline" onClick={load}>
          <RefreshCw className="mr-1.5 h-4 w-4" />
          Retry
        </Button>
      </div>
    );
  }

  const isFiltered = filterCohortId !== "all";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">My Teams</h1>
          <p className="text-sm text-muted-foreground">
            {session?.user?.name?.split(" ")[0]
              ? `${session.user.name.split(" ")[0]}'s full team history`
              : "Your full team history across all activities"}
          </p>
        </div>

        {/* Cohort filter — only show if the user is in multiple cohorts */}
        {cohorts.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Filter:</span>
            <div className="flex flex-wrap gap-1.5">
              <button
                onClick={() => setFilterCohortId("all")}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  filterCohortId === "all"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`}
              >
                All cohorts
              </button>
              {cohorts.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setFilterCohortId(c.id)}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                    filterCohortId === c.id
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  }`}
                >
                  {c.name}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Summary stat */}
      {teams.length > 0 && (
        <div className="flex flex-wrap gap-4">
          <div className="rounded-lg border bg-card px-4 py-3 text-center">
            <p className="text-2xl font-semibold">{teams.length}</p>
            <p className="text-xs text-muted-foreground">
              {teams.length === 1 ? "activity" : "activities"}
            </p>
          </div>
          <div className="rounded-lg border bg-card px-4 py-3 text-center">
            <p className="text-2xl font-semibold">
              {new Set(teams.flatMap((t) => t.teammates.map((m) => m.id))).size}
            </p>
            <p className="text-xs text-muted-foreground">unique teammates</p>
          </div>
          <div className="rounded-lg border bg-card px-4 py-3 text-center">
            <p className="text-2xl font-semibold">
              {new Set(teams.map((t) => t.cohortId)).size}
            </p>
            <p className="text-xs text-muted-foreground">
              {new Set(teams.map((t) => t.cohortId)).size === 1
                ? "cohort"
                : "cohorts"}
            </p>
          </div>
        </div>
      )}

      {/* Team list */}
      {teams.length === 0 ? (
        <EmptyState filtered={isFiltered} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {teams.map((entry) => (
            <TeamCard key={entry.teamId} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}
