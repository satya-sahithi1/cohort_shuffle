"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  ArrowLeft,
  Calendar,
  Clock,
  Users,
  Timer,
  Lock,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  RefreshCw,
  UserCheck,
  Play,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import type { Activity, Registration } from "@/types";
import {
  fetchActivity,
  fetchMyRegistration,
  fetchRegistrations,
  registerForActivity,
  unregisterFromActivity,
} from "@/lib/api/activities";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatShort(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function DeadlineCountdown({ deadlineIso }: { deadlineIso: string }) {
  const [, forceUpdate] = useState(0);

  useEffect(() => {
    const id = setInterval(() => forceUpdate((n) => n + 1), 30_000);
    return () => clearInterval(id);
  }, []);

  const diff = new Date(deadlineIso).getTime() - Date.now();
  if (diff <= 0) {
    return (
      <span className="text-muted-foreground">Registration closed</span>
    );
  }
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  const urgent = hours < 4;
  const label =
    hours < 1
      ? `${minutes}m`
      : hours < 24
      ? `${hours}h ${minutes}m`
      : `${Math.floor(hours / 24)}d ${hours % 24}h`;

  return (
    <span className={urgent ? "font-medium text-orange-600" : ""}>
      {label} remaining
    </span>
  );
}

// ─── Status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: Activity["status"] }) {
  if (status === "formed")
    return (
      <Badge variant="secondary" className="gap-1">
        <CheckCircle2 className="h-3 w-3" /> Teams formed
      </Badge>
    );
  if (status === "closed")
    return (
      <Badge variant="outline" className="gap-1 text-muted-foreground">
        <Lock className="h-3 w-3" /> Closed
      </Badge>
    );
  return (
    <Badge className="gap-1 bg-green-600 text-white hover:bg-green-700">
      Open
    </Badge>
  );
}

// ─── Admin registration list ──────────────────────────────────────────────────

function RegistrationList({
  activityId,
  cap,
}: {
  activityId: string;
  cap: number | null;
}) {
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRegistrations(activityId).then((data) => {
      setRegistrations(data);
      setLoading(false);
    });
  }, [activityId]);

  if (loading) {
    return (
      <div className="flex justify-center py-6">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-sm text-muted-foreground">
        {registrations.length} registered
        {cap !== null && ` / ${cap} cap`}
      </p>
      {registrations.length === 0 ? (
        <p className="text-sm italic text-muted-foreground">
          No one has registered yet.
        </p>
      ) : (
        <ul className="divide-y rounded-lg border">
          {registrations.map((r) => (
            <li
              key={r.id}
              className="flex items-center justify-between px-4 py-2.5"
            >
              <div>
                <p className="text-sm font-medium">{r.userName}</p>
                <p className="text-xs text-muted-foreground">{r.userEmail}</p>
              </div>
              <p className="text-xs text-muted-foreground">
                {formatShort(r.registeredAt)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ActivityDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { data: session } = useSession();
  const isAdmin = session?.user?.role === "admin";

  const [activity, setActivity] = useState<Activity | null>(null);
  const [isRegistered, setIsRegistered] = useState(false);
  const [loading, setLoading] = useState(true);
  const [registering, setRegistering] = useState(false);
  const [regError, setRegError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const [act, reg] = await Promise.all([
      fetchActivity(params.id),
      isAdmin ? Promise.resolve(false) : fetchMyRegistration(params.id),
    ]);
    if (!act) {
      setNotFound(true);
    } else {
      setActivity(act);
      setIsRegistered(reg);
    }
    setLoading(false);
  }, [params.id, isAdmin]);

  useEffect(() => {
    load();
  }, [load]);

  const handleRegister = async () => {
    if (!activity) return;
    setRegistering(true);
    setRegError(null);
    try {
      await registerForActivity(activity.id);
      setIsRegistered(true);
      setActivity((a) =>
        a ? { ...a, registrationCount: a.registrationCount + 1 } : a
      );
    } catch (e: unknown) {
      setRegError(e instanceof Error ? e.message : "Registration failed");
    } finally {
      setRegistering(false);
    }
  };

  const handleUnregister = async () => {
    if (!activity) return;
    setRegistering(true);
    setRegError(null);
    try {
      await unregisterFromActivity(activity.id);
      setIsRegistered(false);
      setActivity((a) =>
        a
          ? { ...a, registrationCount: Math.max(0, a.registrationCount - 1) }
          : a
      );
    } catch (e: unknown) {
      setRegError(e instanceof Error ? e.message : "Unregistration failed");
    } finally {
      setRegistering(false);
    }
  };

  // ── Render ──

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (notFound || !activity) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={() => router.back()}>
          <ArrowLeft className="mr-1.5 h-4 w-4" /> Back
        </Button>
        <div className="rounded-xl border border-dashed p-16 text-center text-muted-foreground">
          <p className="text-sm">Activity not found.</p>
        </div>
      </div>
    );
  }

  const isPast = new Date(activity.eventAt) < new Date();
  const isFull =
    activity.participantCap !== null &&
    activity.registrationCount >= activity.participantCap;
  const canRegister = activity.status === "open" && !isPast && !isFull;
  const canUnregister = isRegistered && activity.status === "open" && !isPast;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Back */}
      <Button variant="ghost" size="sm" onClick={() => router.back()}>
        <ArrowLeft className="mr-1.5 h-4 w-4" /> Back
      </Button>

      {/* Header */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">
            {activity.name}
          </h1>
          <StatusBadge status={activity.status} />
        </div>
      </div>

      {/* Meta card */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Details</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm sm:grid-cols-2">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span>{formatDate(activity.eventAt)}</span>
          </div>
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span>{activity.duration}</span>
          </div>
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span>
              Teams of {activity.teamSize}
              {activity.participantCap !== null && (
                <span className="ml-1 text-muted-foreground">
                  · {activity.registrationCount}/{activity.participantCap} spots
                </span>
              )}
              {activity.participantCap === null && (
                <span className="ml-1 text-muted-foreground">
                  · {activity.registrationCount} registered
                </span>
              )}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Timer className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span>
              Deadline: {formatShort(activity.deadlineAt)}{" "}
              {activity.status === "open" && !isPast && (
                <>
                  (
                  <DeadlineCountdown deadlineIso={activity.deadlineAt} />)
                </>
              )}
            </span>
          </div>
          {activity.locks.length > 0 && (
            <div className="flex items-center gap-2 sm:col-span-2">
              <Lock className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span>
                {activity.locks.length} lock constraint
                {activity.locks.length !== 1 ? "s" : ""} set
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Cap full warning */}
      {isFull && activity.status === "open" && (
        <div className="flex items-center gap-2 rounded-lg border border-orange-200 bg-orange-50 p-3 text-sm text-orange-800 dark:border-orange-800/40 dark:bg-orange-950/30 dark:text-orange-300">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          This activity is full. Registration is closed.
        </div>
      )}

      {/* ── Student view ── */}
      {!isAdmin && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Your registration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {activity.status === "formed" ? (
              <p className="text-sm text-muted-foreground">
                Teams have been formed. Check{" "}
                <a href="/teams" className="underline underline-offset-2">
                  My Teams
                </a>{" "}
                to see your assignment.
              </p>
            ) : (
              <>
                {isRegistered ? (
                  <div className="flex items-center gap-2 text-sm text-green-700 dark:text-green-400">
                    <CheckCircle2 className="h-4 w-4 shrink-0" />
                    You are registered for this activity.
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    You are not registered yet.
                  </p>
                )}

                {regError && (
                  <p className="flex items-center gap-1.5 text-sm text-destructive">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    {regError}
                  </p>
                )}

                <div className="flex gap-2">
                  {isRegistered ? (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={!canUnregister || registering}
                      onClick={handleUnregister}
                    >
                      {registering ? (
                        <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                      ) : null}
                      {registering ? "Updating…" : "Unregister"}
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      disabled={!canRegister || registering}
                      onClick={handleRegister}
                    >
                      {registering ? (
                        <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                      ) : (
                        <UserCheck className="mr-1.5 h-4 w-4" />
                      )}
                      {registering ? "Registering…" : "Register"}
                    </Button>
                  )}
                </div>

                {isPast && (
                  <p className="text-xs text-muted-foreground">
                    This activity has passed. Registration is no longer
                    available.
                  </p>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── Admin view ── */}
      {isAdmin && (
        <>
          {/* Registered students */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Registered students</CardTitle>
            </CardHeader>
            <CardContent>
              <RegistrationList
                activityId={activity.id}
                cap={activity.participantCap}
              />
            </CardContent>
          </Card>

          {/* Lock details */}
          {activity.locks.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Lock constraints</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {activity.locks.map((lock) => (
                    <li
                      key={lock.id}
                      className="flex items-center gap-2 text-sm"
                    >
                      <Lock className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      <span className="font-medium">{lock.userAName}</span>
                      <Badge variant="outline" className="text-xs">
                        {lock.constraintType === "together"
                          ? "must be together"
                          : "must be apart"}
                      </Badge>
                      <span className="font-medium">{lock.userBName}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Formation controls */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Team formation</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {activity.status === "formed" ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm text-green-700 dark:text-green-400">
                    <CheckCircle2 className="h-4 w-4 shrink-0" />
                    Teams formed ({activity.formationRunCount} run
                    {activity.formationRunCount !== 1 ? "s" : ""})
                  </div>
                  {!isPast && (
                    <Button size="sm" variant="outline" disabled>
                      <RefreshCw className="mr-1.5 h-4 w-4" />
                      Re-run formation
                    </Button>
                  )}
                  <p className="text-xs text-muted-foreground">
                    Team editing and re-run will be available in Phase 4.
                  </p>
                </div>
              ) : activity.status === "closed" ? (
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Registration is closed. Formation can be triggered manually.
                  </p>
                  <Button size="sm" disabled>
                    <Play className="mr-1.5 h-4 w-4" />
                    Form teams
                  </Button>
                  <p className="text-xs text-muted-foreground">
                    Formation engine will be wired in Phase 3.
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Formation runs automatically at the deadline
                    {activity.participantCap !== null &&
                      " or when the cap is reached"}
                    .
                  </p>
                  <Button size="sm" variant="outline" disabled>
                    <Play className="mr-1.5 h-4 w-4" />
                    Form teams now
                  </Button>
                  <p className="text-xs text-muted-foreground">
                    Manual formation trigger available after registration closes.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
