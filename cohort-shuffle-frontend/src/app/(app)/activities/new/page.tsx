"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  Plus,
  Trash2,
  AlertTriangle,
  Lock,
  Info,
  Loader2,
  ArrowLeft,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCohort } from "@/contexts/CohortContext";
import { createActivity } from "@/lib/mocks/activities";
import {
  fetchCohortMembers,
  type CohortMember,
} from "@/lib/mocks/cohorts";
import type { ActivityLock, LockConstraintType } from "@/types";

// ─── Deadline rule helpers ────────────────────────────────────────────────────

/**
 * Returns the computed deadline state given a post time and event time.
 *
 * Spec rule (§4.1):
 *   - If gap ≤ 20 min → auto-lock deadline to eventAt - 2 min, field is disabled.
 *   - Otherwise → admin sets it freely, but show a warning if the gap < 20 min.
 */
function computeDeadlineState(eventAt: Date): {
  autoLocked: boolean;
  autoDeadline: Date | null;
  /** Show the "≥20 min before" warning */
  showWarning: boolean;
} {
  const now = new Date();
  const gapMs = eventAt.getTime() - now.getTime();
  const gapMin = gapMs / 60_000;

  if (gapMin <= 20) {
    const autoDeadline = new Date(eventAt.getTime() - 2 * 60_000);
    return { autoLocked: true, autoDeadline, showWarning: false };
  }

  return { autoLocked: false, autoDeadline: null, showWarning: true };
}

function toLocalDatetimeValue(d: Date): string {
  // Format as YYYY-MM-DDTHH:mm for <input type="datetime-local">
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

function fromLocalDatetimeValue(val: string): Date | null {
  if (!val) return null;
  const d = new Date(val);
  return isNaN(d.getTime()) ? null : d;
}

// ─── Lock row ─────────────────────────────────────────────────────────────────

interface LockRowProps {
  lock: ActivityLock;
  members: CohortMember[];
  onChange: (updated: ActivityLock) => void;
  onRemove: () => void;
  otherLocks: ActivityLock[];
}

function LockRow({ lock, members, onChange, onRemove }: LockRowProps) {
  const students = members.filter((m) => m.role === "student");

  return (
    <div className="flex items-center gap-2 rounded-lg border p-3">
      {/* Student A */}
      <Select
        value={lock.userAId}
        onValueChange={(val) => {
          const m = members.find((s) => s.id === val);
          if (m)
            onChange({ ...lock, userAId: m.id, userAName: m.name });
        }}
      >
        <SelectTrigger className="h-8 flex-1 text-sm">
          <SelectValue placeholder="Student A" />
        </SelectTrigger>
        <SelectContent>
          {students.map((s) => (
            <SelectItem key={s.id} value={s.id}>
              {s.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Constraint type */}
      <Select
        value={lock.constraintType}
        onValueChange={(val) =>
          onChange({ ...lock, constraintType: val as LockConstraintType })
        }
      >
        <SelectTrigger className="h-8 w-36 text-sm">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="together">must be together</SelectItem>
          <SelectItem value="apart">must be apart</SelectItem>
        </SelectContent>
      </Select>

      {/* Student B */}
      <Select
        value={lock.userBId}
        onValueChange={(val) => {
          const m = members.find((s) => s.id === val);
          if (m)
            onChange({ ...lock, userBId: m.id, userBName: m.name });
        }}
      >
        <SelectTrigger className="h-8 flex-1 text-sm">
          <SelectValue placeholder="Student B" />
        </SelectTrigger>
        <SelectContent>
          {students.map((s) => (
            <SelectItem key={s.id} value={s.id}>
              {s.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-8 w-8 shrink-0 text-muted-foreground hover:text-destructive"
        onClick={onRemove}
        aria-label="Remove lock"
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  );
}

// ─── Form validation ──────────────────────────────────────────────────────────

interface FormErrors {
  name?: string;
  teamSize?: string;
  duration?: string;
  eventAt?: string;
  deadlineAt?: string;
  participantCap?: string;
  locks?: string;
}

function validateForm(data: {
  name: string;
  teamSize: string;
  duration: string;
  eventAt: Date | null;
  deadlineAt: Date | null;
  participantCap: string;
  locks: ActivityLock[];
}): FormErrors {
  const errs: FormErrors = {};

  if (!data.name.trim()) errs.name = "Activity name is required.";
  const ts = parseInt(data.teamSize, 10);
  if (!data.teamSize || isNaN(ts) || ts < 2)
    errs.teamSize = "Team size must be at least 2.";
  if (!data.duration.trim()) errs.duration = "Duration is required.";
  if (!data.eventAt) errs.eventAt = "Event date and time is required.";
  if (data.eventAt && data.eventAt < new Date())
    errs.eventAt = "Event time must be in the future.";
  if (!data.deadlineAt) errs.deadlineAt = "Registration deadline is required.";
  if (data.deadlineAt && data.eventAt && data.deadlineAt >= data.eventAt)
    errs.deadlineAt = "Deadline must be before the event.";
  if (data.participantCap) {
    const cap = parseInt(data.participantCap, 10);
    if (isNaN(cap) || cap < 2) errs.participantCap = "Cap must be at least 2.";
  }

  // Lock validation
  for (const lock of data.locks) {
    if (!lock.userAId || !lock.userBId) {
      errs.locks = "All lock rules must have two students selected.";
      break;
    }
    if (lock.userAId === lock.userBId) {
      errs.locks = "Both students in a lock rule must be different.";
      break;
    }
  }

  return errs;
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function NewActivityPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const { activeCohort } = useCohort();
  const isAdmin = session?.user?.role === "admin";

  // Redirect non-admins away
  useEffect(() => {
    if (session && !isAdmin) router.replace("/activities");
  }, [session, isAdmin, router]);

  // ── Form state ──
  const [name, setName] = useState("");
  const [teamSize, setTeamSize] = useState("4");
  const [duration, setDuration] = useState("");
  const [eventAtStr, setEventAtStr] = useState("");
  const [deadlineAtStr, setDeadlineAtStr] = useState("");
  const [participantCap, setParticipantCap] = useState("");
  const [locks, setLocks] = useState<ActivityLock[]>([]);
  const [members, setMembers] = useState<CohortMember[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Deadline auto-lock state
  const eventAt = fromLocalDatetimeValue(eventAtStr);
  const deadlineState = eventAt ? computeDeadlineState(eventAt) : null;
  const isDeadlineLocked = deadlineState?.autoLocked ?? false;

  // When event time changes, apply auto-lock if triggered
  const prevEventAtRef = useRef(eventAtStr);
  useEffect(() => {
    if (eventAtStr === prevEventAtRef.current) return;
    prevEventAtRef.current = eventAtStr;
    if (deadlineState?.autoLocked && deadlineState.autoDeadline) {
      setDeadlineAtStr(toLocalDatetimeValue(deadlineState.autoDeadline));
    }
  }, [eventAtStr, deadlineState]);

  // Load cohort members for lock builder
  useEffect(() => {
    if (activeCohort) {
      fetchCohortMembers(activeCohort.id).then(setMembers);
    }
  }, [activeCohort]);

  // ── Lock builder ──
  const addLock = () => {
    const students = members.filter((m) => m.role === "student");
    if (students.length < 2) return;
    setLocks((prev) => [
      ...prev,
      {
        id: `lock-${Date.now()}`,
        userAId: students[0].id,
        userAName: students[0].name,
        userBId: students[1].id,
        userBName: students[1].name,
        constraintType: "together",
      },
    ]);
  };

  const updateLock = useCallback((id: string, updated: ActivityLock) => {
    setLocks((prev) => prev.map((l) => (l.id === id ? updated : l)));
  }, []);

  const removeLock = useCallback((id: string) => {
    setLocks((prev) => prev.filter((l) => l.id !== id));
  }, []);

  // ── Submit ──
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    const deadlineAt = isDeadlineLocked
      ? deadlineState?.autoDeadline ?? fromLocalDatetimeValue(deadlineAtStr)
      : fromLocalDatetimeValue(deadlineAtStr);

    const validationErrors = validateForm({
      name,
      teamSize,
      duration,
      eventAt,
      deadlineAt,
      participantCap,
      locks,
    });

    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    if (!activeCohort) return;

    setSubmitting(true);
    try {
      const activity = await createActivity({
        cohortId: activeCohort.id,
        name: name.trim(),
        teamSize: parseInt(teamSize, 10),
        duration: duration.trim(),
        eventAt: eventAt!.toISOString(),
        deadlineAt: deadlineAt!.toISOString(),
        participantCap: participantCap ? parseInt(participantCap, 10) : null,
        locks,
      });
      router.push(`/activities/${activity.id}`);
    } catch {
      setSubmitError("Failed to create activity. Please try again.");
      setSubmitting(false);
    }
  };

  // ── Guard ──
  if (!session) return null;
  if (!isAdmin) return null;

  // ── Deadline help text ──
  const deadlineHelp = isDeadlineLocked
    ? `Auto-set to 2 minutes before the event because the gap is ≤ 20 minutes. You cannot change this.`
    : `Set this at least 20 minutes before the event start time.`;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Back */}
      <Button variant="ghost" size="sm" onClick={() => router.back()}>
        <ArrowLeft className="mr-1.5 h-4 w-4" />
        Back
      </Button>

      <div>
        <h1 className="text-2xl font-semibold tracking-tight">New activity</h1>
        <p className="text-sm text-muted-foreground">
          {activeCohort?.name ?? "Select a cohort"}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6" noValidate>
        {/* ── Required fields ── */}
        <fieldset className="space-y-4 rounded-xl border p-5">
          <legend className="px-1 text-sm font-medium">Activity details</legend>

          {/* Name */}
          <div className="space-y-1.5">
            <Label htmlFor="name">
              Activity name <span aria-hidden="true" className="text-destructive">*</span>
            </Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setErrors((p) => ({ ...p, name: undefined }));
              }}
              placeholder="e.g. Requirements Analysis Sprint"
              aria-describedby={errors.name ? "name-error" : undefined}
              aria-invalid={!!errors.name}
            />
            {errors.name && (
              <p id="name-error" className="text-xs text-destructive">
                {errors.name}
              </p>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {/* Team size */}
            <div className="space-y-1.5">
              <Label htmlFor="team-size">
                Team size <span aria-hidden="true" className="text-destructive">*</span>
              </Label>
              <Input
                id="team-size"
                type="number"
                min={2}
                max={50}
                value={teamSize}
                onChange={(e) => {
                  setTeamSize(e.target.value);
                  setErrors((p) => ({ ...p, teamSize: undefined }));
                }}
                aria-invalid={!!errors.teamSize}
                aria-describedby={errors.teamSize ? "ts-error" : undefined}
              />
              {errors.teamSize && (
                <p id="ts-error" className="text-xs text-destructive">
                  {errors.teamSize}
                </p>
              )}
            </div>

            {/* Duration */}
            <div className="space-y-1.5">
              <Label htmlFor="duration">
                Duration <span aria-hidden="true" className="text-destructive">*</span>
              </Label>
              <Input
                id="duration"
                value={duration}
                onChange={(e) => {
                  setDuration(e.target.value);
                  setErrors((p) => ({ ...p, duration: undefined }));
                }}
                placeholder="e.g. 2 hours"
                aria-invalid={!!errors.duration}
                aria-describedby={errors.duration ? "dur-error" : undefined}
              />
              {errors.duration && (
                <p id="dur-error" className="text-xs text-destructive">
                  {errors.duration}
                </p>
              )}
            </div>
          </div>

          {/* Event date & time */}
          <div className="space-y-1.5">
            <Label htmlFor="event-at">
              Date and time <span aria-hidden="true" className="text-destructive">*</span>
            </Label>
            <Input
              id="event-at"
              type="datetime-local"
              value={eventAtStr}
              onChange={(e) => {
                setEventAtStr(e.target.value);
                setErrors((p) => ({ ...p, eventAt: undefined, deadlineAt: undefined }));
              }}
              aria-invalid={!!errors.eventAt}
              aria-describedby={errors.eventAt ? "event-error" : undefined}
            />
            {errors.eventAt && (
              <p id="event-error" className="text-xs text-destructive">
                {errors.eventAt}
              </p>
            )}
          </div>

          {/* Registration deadline */}
          <div className="space-y-1.5">
            <Label htmlFor="deadline-at">
              Registration deadline{" "}
              <span aria-hidden="true" className="text-destructive">*</span>
            </Label>

            {/* Warning banner */}
            {!isDeadlineLocked && eventAtStr && (
              <div className="flex items-start gap-2 rounded-lg border border-orange-200 bg-orange-50 p-3 text-xs text-orange-800 dark:border-orange-800/40 dark:bg-orange-950/30 dark:text-orange-300">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                Set the deadline at least 20 minutes before the event start time.
              </div>
            )}

            {/* Auto-lock notice */}
            {isDeadlineLocked && (
              <div className="flex items-start gap-2 rounded-lg border border-blue-200 bg-blue-50 p-3 text-xs text-blue-800 dark:border-blue-800/40 dark:bg-blue-950/30 dark:text-blue-300">
                <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {deadlineHelp}
              </div>
            )}

            <Input
              id="deadline-at"
              type="datetime-local"
              value={deadlineAtStr}
              onChange={(e) => {
                if (!isDeadlineLocked) {
                  setDeadlineAtStr(e.target.value);
                  setErrors((p) => ({ ...p, deadlineAt: undefined }));
                }
              }}
              disabled={isDeadlineLocked}
              aria-invalid={!!errors.deadlineAt}
              aria-describedby={
                errors.deadlineAt ? "deadline-error" : "deadline-help"
              }
            />
            {!isDeadlineLocked && (
              <p id="deadline-help" className="text-xs text-muted-foreground">
                {deadlineHelp}
              </p>
            )}
            {errors.deadlineAt && (
              <p id="deadline-error" className="text-xs text-destructive">
                {errors.deadlineAt}
              </p>
            )}
          </div>
        </fieldset>

        {/* ── Optional fields ── */}
        <fieldset className="space-y-4 rounded-xl border p-5">
          <legend className="px-1 text-sm font-medium">
            Optional settings
          </legend>

          {/* Participant cap */}
          <div className="space-y-1.5">
            <Label htmlFor="cap">Participant cap</Label>
            <p className="text-xs text-muted-foreground">
              Leave blank for no cap. When reached, registration closes
              immediately and teams are formed.
            </p>
            <Input
              id="cap"
              type="number"
              min={2}
              value={participantCap}
              onChange={(e) => {
                setParticipantCap(e.target.value);
                setErrors((p) => ({ ...p, participantCap: undefined }));
              }}
              placeholder="e.g. 30"
              className="max-w-40"
              aria-invalid={!!errors.participantCap}
              aria-describedby={errors.participantCap ? "cap-error" : undefined}
            />
            {errors.participantCap && (
              <p id="cap-error" className="text-xs text-destructive">
                {errors.participantCap}
              </p>
            )}
          </div>
        </fieldset>

        {/* ── Lock constraints ── */}
        <fieldset className="space-y-4 rounded-xl border p-5">
          <div className="flex items-center justify-between">
            <legend className="px-1 text-sm font-medium">
              Lock constraints
            </legend>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addLock}
              disabled={members.filter((m) => m.role === "student").length < 2}
            >
              <Lock className="mr-1.5 h-3.5 w-3.5" />
              Add lock
            </Button>
          </div>

          <p className="text-xs text-muted-foreground">
            Fix certain students relative to each other before team formation.
            Leave empty for no constraints.
          </p>

          {locks.length === 0 && (
            <p className="text-sm text-muted-foreground italic">
              No locks added.
            </p>
          )}

          {locks.map((lock) => (
            <LockRow
              key={lock.id}
              lock={lock}
              members={members}
              onChange={(updated) => updateLock(lock.id, updated)}
              onRemove={() => removeLock(lock.id)}
              otherLocks={locks.filter((l) => l.id !== lock.id)}
            />
          ))}

          {errors.locks && (
            <p className="text-xs text-destructive">{errors.locks}</p>
          )}
        </fieldset>

        {/* Submit */}
        {submitError && (
          <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            {submitError}
          </div>
        )}

        <div className="flex gap-3">
          <Button
            type="submit"
            disabled={submitting || !activeCohort}
            className="min-w-32"
          >
            {submitting ? (
              <>
                <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                Creating…
              </>
            ) : (
              <>
                <Plus className="mr-1.5 h-4 w-4" />
                Create activity
              </>
            )}
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() => router.push("/activities")}
            disabled={submitting}
          >
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
