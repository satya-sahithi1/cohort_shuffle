"use client";

/**
 * TeamEditView — admin manual team editor.
 *
 * Interaction model (click-to-move, works on desktop + mobile):
 *   1. Admin clicks a student name → that student is "selected" (highlighted).
 *   2. A "Move here" button appears on every OTHER team.
 *   3. Admin clicks "Move here" on the destination team → move happens.
 *   4. Clicking the same student again deselects.
 *   5. Clicking a different student switches selection.
 *
 * Each move calls onMove(studentId, targetTeamId) which is async.
 * While a move is in-flight the UI is locked (buttons disabled, spinner shown).
 */

import { useState } from "react";
import {
  UserCircle2,
  Users,
  ArrowRight,
  Loader2,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { FormedTeam, FormationResult } from "@/types";

// ─── Props ────────────────────────────────────────────────────────────────────

interface TeamEditViewProps {
  result: FormationResult;
  /** Called when the admin moves a student. Should call the API and
   *  return the updated FormationResult. */
  onMove: (studentId: string, targetTeamId: string) => Promise<FormationResult>;
  /** Called when the admin clicks "Done editing". */
  onDone: () => void;
  /** Called whenever a move succeeds (parent updates its state). */
  onResultUpdate: (updated: FormationResult) => void;
}

// ─── Single team column ───────────────────────────────────────────────────────

interface TeamColumnProps {
  team: FormedTeam;
  selectedStudentId: string | null;
  moving: boolean;
  onSelectStudent: (id: string) => void;
  onMoveHere: (teamId: string) => void;
}

function TeamColumn({
  team,
  selectedStudentId,
  moving,
  onSelectStudent,
  onMoveHere,
}: TeamColumnProps) {
  // Is the selected student already on this team?
  const selectedIsHere = team.members.some((m) => m.id === selectedStudentId);
  const canReceive = selectedStudentId !== null && !selectedIsHere;

  return (
    <div
      className={`flex flex-col rounded-xl border bg-card transition-all ${
        canReceive
          ? "border-primary/40 ring-2 ring-primary/20"
          : ""
      }`}
    >
      {/* Team header */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium text-sm">Team {team.teamNumber}</span>
        </div>
        <Badge variant="secondary" className="text-xs">
          {team.members.length}
        </Badge>
      </div>

      {/* Members */}
      <ul className="flex flex-col divide-y flex-1">
        {team.members.map((member) => {
          const isSelected = member.id === selectedStudentId;
          return (
            <li key={member.id}>
              <button
                disabled={moving}
                onClick={() => onSelectStudent(member.id)}
                aria-pressed={isSelected}
                className={`flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors disabled:opacity-50 ${
                  isSelected
                    ? "bg-primary/10 text-primary"
                    : "hover:bg-muted/50"
                }`}
              >
                <UserCircle2
                  className={`h-5 w-5 shrink-0 ${
                    isSelected ? "text-primary" : "text-muted-foreground/50"
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{member.name}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {member.email}
                  </p>
                </div>
                {isSelected && (
                  <span className="shrink-0 text-xs font-semibold text-primary">
                    Selected
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>

      {/* "Move here" footer — only shown when a student from another team is selected */}
      {canReceive && (
        <div className="border-t p-3">
          <Button
            size="sm"
            className="w-full"
            disabled={moving}
            onClick={() => onMoveHere(team.teamId)}
          >
            {moving ? (
              <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
            ) : (
              <ArrowRight className="mr-1.5 h-4 w-4" />
            )}
            Move here
          </Button>
        </div>
      )}
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function TeamEditView({
  result,
  onMove,
  onDone,
  onResultUpdate,
}: TeamEditViewProps) {
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(
    null
  );
  const [moving, setMoving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Keep a local copy of teams so the UI updates immediately after a move
  const [localResult, setLocalResult] = useState<FormationResult>(result);

  // Find the selected student's name for the instruction banner
  const selectedStudent = localResult.teams
    .flatMap((t) => t.members)
    .find((m) => m.id === selectedStudentId);

  const handleSelectStudent = (id: string) => {
    setError(null);
    setSelectedStudentId((prev) => (prev === id ? null : id));
  };

  const handleMoveHere = async (targetTeamId: string) => {
    if (!selectedStudentId) return;
    setMoving(true);
    setError(null);
    try {
      const updated = await onMove(selectedStudentId, targetTeamId);
      setLocalResult(updated);
      onResultUpdate(updated);
      setSelectedStudentId(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Move failed. Please try again.");
    } finally {
      setMoving(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Edit teams</span>
          <Badge variant="outline" className="text-xs">
            {localResult.teams.length} teams ·{" "}
            {localResult.teams.reduce((n, t) => n + t.members.length, 0)}{" "}
            students
          </Badge>
        </div>
        <Button size="sm" variant="outline" onClick={onDone} disabled={moving}>
          <X className="mr-1.5 h-4 w-4" />
          Done editing
        </Button>
      </div>

      {/* Instruction banner */}
      {selectedStudentId === null ? (
        <div className="rounded-lg border border-dashed bg-muted/40 px-4 py-2.5 text-sm text-muted-foreground">
          Click a student to select them, then click "Move here" on the
          destination team.
        </div>
      ) : (
        <div className="flex items-center justify-between rounded-lg border border-primary/30 bg-primary/5 px-4 py-2.5">
          <span className="text-sm">
            <span className="font-medium text-primary">
              {selectedStudent?.name ?? "Student"}
            </span>{" "}
            selected — click "Move here" on any other team.
          </span>
          <button
            onClick={() => setSelectedStudentId(null)}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="text-sm text-destructive flex items-center gap-1.5">
          <span>⚠</span> {error}
        </p>
      )}

      {/* Team grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {localResult.teams.map((team) => (
          <TeamColumn
            key={team.teamId}
            team={team}
            selectedStudentId={selectedStudentId}
            moving={moving}
            onSelectStudent={handleSelectStudent}
            onMoveHere={handleMoveHere}
          />
        ))}
      </div>
    </div>
  );
}
