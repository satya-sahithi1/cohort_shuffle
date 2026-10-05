"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { Plus, Loader2, CalendarDays, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ActivityCard } from "@/components/activities/ActivityCard";
import { useCohort } from "@/contexts/CohortContext";
import {
  fetchActivities,
  fetchMyRegistration,
} from "@/lib/mocks/activities";
import type { Activity } from "@/types";

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState({ isAdmin }: { isAdmin: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed py-20 text-center">
      <CalendarDays className="h-10 w-10 text-muted-foreground/50" />
      <div className="space-y-1">
        <p className="text-sm font-medium text-muted-foreground">
          No activities posted yet
        </p>
        {isAdmin && (
          <p className="text-xs text-muted-foreground">
            Create the first activity for this cohort.
          </p>
        )}
      </div>
      {isAdmin && (
        <Button size="sm" asChild>
          <Link href="/activities/new">
            <Plus className="mr-1.5 h-4 w-4" />
            Create activity
          </Link>
        </Button>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ActivitiesPage() {
  const { data: session } = useSession();
  const { activeCohort, isLoading: cohortLoading } = useCohort();
  const isAdmin = session?.user?.role === "admin";

  const [activities, setActivities] = useState<Activity[]>([]);
  const [registeredIds, setRegisteredIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!activeCohort) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchActivities(activeCohort.id);
      setActivities(data);

      // Fetch registration status for each activity in parallel (student only)
      if (!isAdmin) {
        const results = await Promise.all(
          data.map((a) => fetchMyRegistration(a.id))
        );
        const registered = new Set(
          data.filter((_, i) => results[i]).map((a) => a.id)
        );
        setRegisteredIds(registered);
      }
    } catch {
      setError("Failed to load activities. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [activeCohort, isAdmin]);

  useEffect(() => {
    if (!cohortLoading) load();
  }, [cohortLoading, load]);

  const handleRegistrationChange = useCallback(
    (activityId: string, registered: boolean) => {
      setRegisteredIds((prev) => {
        const next = new Set(prev);
        if (registered) next.add(activityId);
        else next.delete(activityId);
        return next;
      });
      // Also bump/decrement the local count on the activity
      setActivities((prev) =>
        prev.map((a) =>
          a.id === activityId
            ? {
                ...a,
                registrationCount: registered
                  ? a.registrationCount + 1
                  : Math.max(0, a.registrationCount - 1),
              }
            : a
        )
      );
    },
    []
  );

  // ── Render ──

  if (cohortLoading || loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!activeCohort) {
    return (
      <div className="rounded-xl border border-dashed p-12 text-center text-muted-foreground">
        <p className="text-sm">Select or join a cohort to see activities.</p>
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

  // Split into open vs closed/formed
  const openActivities = activities.filter((a) => a.status === "open");
  const pastActivities = activities.filter((a) => a.status !== "open");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Activities</h1>
          <p className="text-sm text-muted-foreground">
            {activeCohort.name}
          </p>
        </div>
        {isAdmin && (
          <Button asChild>
            <Link href="/activities/new">
              <Plus className="mr-1.5 h-4 w-4" />
              New activity
            </Link>
          </Button>
        )}
      </div>

      {activities.length === 0 ? (
        <EmptyState isAdmin={isAdmin} />
      ) : (
        <div className="space-y-8">
          {/* Open activities */}
          {openActivities.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-medium text-muted-foreground uppercase tracking-wide">
                Open for registration
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {openActivities.map((activity) => (
                  <ActivityCard
                    key={activity.id}
                    activity={activity}
                    isRegistered={registeredIds.has(activity.id)}
                    isAdmin={isAdmin}
                    onRegistrationChange={handleRegistrationChange}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Past / formed activities */}
          {pastActivities.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-medium text-muted-foreground uppercase tracking-wide">
                Past activities
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {pastActivities.map((activity) => (
                  <ActivityCard
                    key={activity.id}
                    activity={activity}
                    isRegistered={registeredIds.has(activity.id)}
                    isAdmin={isAdmin}
                    onRegistrationChange={handleRegistrationChange}
                  />
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
