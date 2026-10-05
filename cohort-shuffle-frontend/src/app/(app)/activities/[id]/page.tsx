"use client";

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
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  Pencil,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import type {
  Activity,
  FormationLog,
  FormationResult,
  Registration,
} from "@/types";
import {
  fetchActivity,
  fetchMyRegistration,
  fetchRegistrations,
  registerForActivity,
  unregisterFromActivity,
} from "@/lib/api/activities";
import {
  fetchFormedTeams,
  fetchFormationLogs,
  triggerFormation,
  validateLocks,
  moveStudentBetweenTeams,
} from "@/lib/mocks/formation";
import { FormedTeamsView } from "@/components/activities/FormedTeamsView";
import { FormationLogPanel } from "@/components/activities/FormationLogPanel";
import { TeamEditView } from "@/components/activities/TeamEditView";

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
  if (diff <= 0)
    return <span className="text-muted-foreground">Registration closed</span>;

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

  if (loading)
    return (
      <div className="flex justify-center py-6">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );

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

// ─── Saturation warning ───────────────────────────────────────────────────────

function SaturationWarning({ saturation }: { saturation: number }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-orange-200 bg-orange-50 p-3 text-sm text-orange-800 dark:border-orange-800/40 dark:bg-orange-950/30 dark:text-orange-300">
      <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="space-y-0.5">
        <p className="font-medium">High saturation warning</p>
        <p className="text-xs opacity-90">
          {Math.round(saturation * 100)}% of all possible teammate pairs in
          this cohort have already worked together. Zero-repeat teams are no
          longer achievable — the algorithm is minimising repeats as best it
          can.
        </p>
      </div>
    </div>
  );
}

// ─── Lock error banner ────────────────────────────────────────────────────────

function LockErrorBanner({ errors }: { errors: string[] }) {
  return (
    <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 space-y-2">
      <div className="flex items-center gap-2 text-sm font-medium text-destructive">
        <AlertTriangle className="h-4 w-4 shrink-0" />
        Lock constraints cannot be satisfied
      </div>
      <ul className="space-y-1 text-xs text-destructive/90">
        {errors.map((e, i) => (
          <li key={i} className="flex gap-1.5">
            <span className="shrink-0">•</span>
            {e}
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">
        Fix the lock constraints before running formation.
      </p>
    </div>
  );
}

// ─── Collapsible formation log ─────────────────────────────────────────────────

function CollapsibleLogPanel({ logs }: { logs: FormationLog[] }) {
  const [open, setOpen] = useState(false);
  if (logs.length === 0) return null;

  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between text-sm font-medium text-muted-foreground hover:text-foreground transition-colors py-1"
      >
        <span>Formation history ({logs.length} run{logs.length !== 1 ? "s" : ""})</span>
        {open ? (
          <ChevronUp className="h-4 w-4" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )}
      </button>
      {open && (
        <div className="mt-2">
          <FormationLogPanel logs={logs} />
        </div>
      )}
    </div>
  );
}

// ─── Admin formation section ──────────────────────────────────────────────────

interface AdminFormationSectionProps {
  activity: Activity;
  onActivityUpdate: (updated: Activity) => void;
}

function AdminFormationSection({
  activity,
  onActivityUpdate,
}: AdminFormationSectionProps) {
  const isPast = new Date(activity.eventAt) < new Date();

  const [forming, setForming] = useState(false);
  const [lockErrors, setLockErrors] = useState<string[]>([]);
  const [formationResult, setFormationResult] =
    useState<FormationResult | null>(null);
  const [formationLogs, setFormationLogs] = useState<FormationLog[]>([]);
  const [formationError, setFormationError] = useState<string | null>(null);
  const [loadingTeams, setLoadingTeams] = useState(
    activity.status === "formed"
  );
  // Edit mode — toggled by "Edit teams" / "Done editing"
  const [editMode, setEditMode] = useState(false);

  // Load existing teams + logs if already formed
  useEffect(() => {
    if (activity.status !== "formed") return;
    Promise.all([
      fetchFormedTeams(activity.id),
      fetchFormationLogs(activity.id),
    ]).then(([result, logs]) => {
      setFormationResult(result);
      setFormationLogs(logs);
      setLoadingTeams(false);
    });
  }, [activity.id, activity.status]);

  const handleFormTeams = async () => {
    setFormationError(null);
    setLockErrors([]);

    // 1. Pre-flight lock validation
    setForming(true);
    try {
      const errors = await validateLocks(activity.id);
      if (errors.length > 0) {
        setLockErrors(errors);
        setForming(false);
        return;
      }
    } catch {
      setFormationError("Failed to validate locks. Please try again.");
      setForming(false);
      return;
    }

    // 2. Trigger formation
    try {
      const result = await triggerFormation(activity.id);

      // Update local state
      setFormationResult(result);
      setFormationLogs((prev) => [
        {
          id: `log-${result.runNumber}`,
          activityId: activity.id,
          runNumber: result.runNumber,
          triggeredBy: "me",
          triggeredByName: "Admin",
          score: result.score,
          repeatPairs: result.repeatPairs,
          saturation: result.saturation,
          createdAt: result.triggeredAt,
        },
        ...prev,
      ]);

      // Tell parent the activity is now formed
      onActivityUpdate({
        ...activity,
        status: "formed",
        formationRunCount: result.runNumber,
      });
    } catch (e: unknown) {
      setFormationError(
        e instanceof Error ? e.message : "Formation failed. Please try again."
      );
    } finally {
      setForming(false);
    }
  };

  // ── Status: open ──
  if (activity.status === "open") {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Formation runs automatically at the deadline
          {activity.participantCap !== null && " or when the cap is reached"}.
          You can also trigger it manually once registration closes.
        </p>
        <Button size="sm" variant="outline" disabled>
          <Play className="mr-1.5 h-4 w-4" />
          Form teams now
        </Button>
        <p className="text-xs text-muted-foreground">
          Manual trigger is available after registration closes.
        </p>
      </div>
    );
  }

  // ── Status: closed — ready to form ──
  if (activity.status === "closed") {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          Registration is closed.{" "}
          {activity.registrationCount === 0
            ? "No students registered — no teams to form."
            : `${activity.registrationCount} students registered.`}
        </p>

        {lockErrors.length > 0 && <LockErrorBanner errors={lockErrors} />}
        {formationError && (
          <p className="flex items-center gap-1.5 text-sm text-destructive">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            {formationError}
          </p>
        )}

        <Button
          size="sm"
          onClick={handleFormTeams}
          disabled={forming || activity.registrationCount === 0}
        >
          {forming ? (
            <>
              <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
              Forming teams…
            </>
          ) : (
            <>
              <Play className="mr-1.5 h-4 w-4" />
              Form teams
            </>
          )}
        </Button>
      </div>
    );
  }

  // ── Status: formed — show results ──
  if (loadingTeams) {
    return (
      <div className="flex justify-center py-6">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Success header + action buttons row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-green-700 dark:text-green-400">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Teams formed · {activity.formationRunCount} run
          {activity.formationRunCount !== 1 ? "s" : ""}
        </div>

        {/* Edit / Re-run buttons — only before event starts */}
        {!isPast && !editMode && (
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setEditMode(true)}
              disabled={forming || !formationResult}
            >
              <Pencil className="mr-1.5 h-4 w-4" />
              Edit teams
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleFormTeams}
              disabled={forming}
            >
              {forming ? (
                <>
                  <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                  Re-running…
                </>
              ) : (
                <>
                  <RefreshCw className="mr-1.5 h-4 w-4" />
                  Re-run
                </>
              )}
            </Button>
          </div>
        )}
      </div>

      {/* Saturation warning */}
      {formationResult?.saturated && !editMode && (
        <SaturationWarning saturation={formationResult.saturation} />
      )}

      {/* Unfair students warning */}
      {!editMode && formationResult && formationResult.unfairStudents.length > 0 && (
        <div className="flex items-start gap-2 rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800 dark:border-yellow-800/40 dark:bg-yellow-950/30 dark:text-yellow-300">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            {formationResult.unfairStudents.length} student
            {formationResult.unfairStudents.length !== 1 ? "s have" : " has"}{" "}
            no new teammate in this run. Consider re-running.
          </span>
        </div>
      )}

      {lockErrors.length > 0 && <LockErrorBanner errors={lockErrors} />}
      {formationError && (
        <p className="flex items-center gap-1.5 text-sm text-destructive">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {formationError}
        </p>
      )}

      {/* Team view — read mode or edit mode */}
      {formationResult && (
        editMode ? (
          <TeamEditView
            result={formationResult}
            onMove={(studentId, targetTeamId) =>
              moveStudentBetweenTeams(activity.id, studentId, targetTeamId)
            }
            onDone={() => setEditMode(false)}
            onResultUpdate={(updated) => setFormationResult(updated)}
          />
        ) : (
          <FormedTeamsView result={formationResult} isAdmin />
        )
      )}

      {/* Formation log (collapsible) — hidden while editing to reduce noise */}
      {!editMode && <CollapsibleLogPanel logs={formationLogs} />}
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

  // Post-formation team view for students
  const [myFormationResult, setMyFormationResult] =
    useState<FormationResult | null>(null);

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
      // Load teams for student if already formed
      if (!isAdmin && act.status === "formed") {
        fetchFormedTeams(act.id).then(setMyFormationResult);
      }
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
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">
          {activity.name}
        </h1>
        <StatusBadge status={activity.status} />
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
                <>(<DeadlineCountdown deadlineIso={activity.deadlineAt} />)</>
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
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm text-green-700 dark:text-green-400">
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                  Teams have been formed.
                </div>
                {myFormationResult ? (
                  <FormedTeamsView
                    result={myFormationResult}
                    currentUserId={session?.user?.id}
                    isAdmin={false}
                  />
                ) : (
                  <p className="text-sm text-muted-foreground">
                    You were not registered for this activity.
                  </p>
                )}
              </div>
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
                    This activity has passed.
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

          {/* Formation controls + results */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Team formation</CardTitle>
            </CardHeader>
            <CardContent>
              <AdminFormationSection
                activity={activity}
                onActivityUpdate={setActivity}
              />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
