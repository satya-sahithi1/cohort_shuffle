"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Calendar,
  Clock,
  Users,
  Timer,
  Lock,
  CheckCircle2,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import type { Activity } from "@/types";
import { registerForActivity, unregisterFromActivity } from "@/lib/api/activities";

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

function formatDeadlineCountdown(deadlineIso: string): {
  label: string;
  urgent: boolean;
} {
  const diff = new Date(deadlineIso).getTime() - Date.now();
  if (diff <= 0) return { label: "Deadline passed", urgent: true };
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  if (hours < 1) return { label: `${minutes}m left to register`, urgent: true };
  if (hours < 24)
    return { label: `${hours}h ${minutes}m left to register`, urgent: hours < 4 };
  const days = Math.floor(hours / 24);
  return { label: `${days}d left to register`, urgent: false };
}

// ─── Status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ activity }: { activity: Activity }) {
  if (activity.status === "formed") {
    return (
      <Badge variant="secondary" className="gap-1">
        <CheckCircle2 className="h-3 w-3" />
        Teams formed
      </Badge>
    );
  }
  if (activity.status === "closed") {
    return (
      <Badge
        variant="outline"
        className="gap-1 border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-400"
      >
        <Lock className="h-3 w-3" />
        Forming soon
      </Badge>
    );
  }
  if (
    activity.participantCap !== null &&
    activity.registrationCount >= activity.participantCap
  ) {
    return (
      <Badge variant="destructive" className="gap-1">
        <Lock className="h-3 w-3" />
        Full
      </Badge>
    );
  }
  return (
    <Badge className="gap-1 bg-green-600 text-white hover:bg-green-700">
      Open
    </Badge>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface ActivityCardProps {
  activity: Activity;
  /** Whether the current user is registered for this activity. */
  isRegistered: boolean;
  /** Whether the current user is an admin in this cohort. */
  isAdmin?: boolean;
  /** Called after a successful register or unregister so parent can refresh. */
  onRegistrationChange?: (activityId: string, registered: boolean) => void;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ActivityCard({
  activity,
  isRegistered,
  isAdmin = false,
  onRegistrationChange,
}: ActivityCardProps) {
  const [registering, setRegistering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const deadline = formatDeadlineCountdown(activity.deadlineAt);
  const isPast = new Date(activity.eventAt) < new Date();
  const canRegister =
    activity.status === "open" &&
    !isPast &&
    (activity.participantCap === null ||
      activity.registrationCount < activity.participantCap);
  const canUnregister = isRegistered && activity.status === "open" && !isPast;

  const handleRegister = async () => {
    setRegistering(true);
    setError(null);
    try {
      await registerForActivity(activity.id);
      onRegistrationChange?.(activity.id, true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Registration failed");
    } finally {
      setRegistering(false);
    }
  };

  const handleUnregister = async () => {
    setRegistering(true);
    setError(null);
    try {
      await unregisterFromActivity(activity.id);
      onRegistrationChange?.(activity.id, false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unregistration failed");
    } finally {
      setRegistering(false);
    }
  };

  return (
    <Card className="flex flex-col transition-shadow hover:shadow-md">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base leading-snug">
            <Link
              href={`/activities/${activity.id}`}
              className="hover:underline underline-offset-2"
            >
              {activity.name}
            </Link>
          </CardTitle>
          <StatusBadge activity={activity} />
        </div>

        {/* Meta row */}
        <CardDescription className="mt-2 space-y-1 text-xs">
          <span className="flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5 shrink-0" />
            {formatDate(activity.eventAt)}
          </span>
          <span className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 shrink-0" />
            {activity.duration}
          </span>
          <span className="flex items-center gap-1.5">
            <Users className="h-3.5 w-3.5 shrink-0" />
            Teams of {activity.teamSize}
            {activity.participantCap !== null && (
              <span className="text-muted-foreground">
                · {activity.registrationCount}/{activity.participantCap} spots
              </span>
            )}
            {activity.participantCap === null && (
              <span className="text-muted-foreground">
                · {activity.registrationCount} registered
              </span>
            )}
          </span>
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1 pb-2">
        {/* Deadline countdown */}
        {activity.status === "open" && !isPast && (
          <div
            className={`flex items-center gap-1.5 text-xs font-medium ${
              deadline.urgent ? "text-orange-600" : "text-muted-foreground"
            }`}
          >
            <Timer className="h-3.5 w-3.5 shrink-0" />
            {deadline.label}
          </div>
        )}

        {/* Lock constraints indicator */}
        {activity.locks.length > 0 && (
          <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
            <Lock className="h-3.5 w-3.5 shrink-0" />
            {activity.locks.length} lock
            {activity.locks.length !== 1 ? "s" : ""} set
          </div>
        )}

        {/* Error */}
        {error && (
          <p className="mt-2 flex items-center gap-1 text-xs text-destructive">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            {error}
          </p>
        )}
      </CardContent>

      <CardFooter className="gap-2 pt-2">
        {/* Register / Unregister — only for students */}
        {!isAdmin && (
          <>
            {isRegistered ? (
              <Button
                size="sm"
                variant="outline"
                disabled={!canUnregister || registering}
                onClick={handleUnregister}
                className="flex-1"
              >
                {registering ? (
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <CheckCircle2 className="mr-1.5 h-3.5 w-3.5 text-green-600" />
                )}
                {registering ? "Updating…" : "Registered"}
              </Button>
            ) : (
              <Button
                size="sm"
                disabled={!canRegister || registering}
                onClick={handleRegister}
                className="flex-1"
              >
                {registering ? (
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                ) : null}
                {registering ? "Registering…" : "Register"}
              </Button>
            )}
          </>
        )}

        {/* Detail link */}
        <Button size="sm" variant="ghost" asChild className={isAdmin ? "flex-1" : ""}>
          <Link href={`/activities/${activity.id}`}>Details →</Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
