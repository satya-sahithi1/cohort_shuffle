"use client";

/**
 * FormedTeamsView — post-formation team display.
 *
 * Admin mode: shows every team in a grid.
 * Student mode: shows only the team the current user is on,
 *               plus a note that teams are locked.
 */

import { UserCircle2, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { FormedTeam, FormationResult } from "@/types";

// ─── Single team card ─────────────────────────────────────────────────────────

function TeamCard({
  team,
  highlight = false,
}: {
  team: FormedTeam;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border bg-card transition-shadow ${
        highlight
          ? "border-primary/40 ring-2 ring-primary/20 shadow-sm"
          : "hover:shadow-sm"
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium text-sm">Team {team.teamNumber}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Badge variant="secondary" className="text-xs">
            {team.members.length}{" "}
            {team.members.length === 1 ? "member" : "members"}
          </Badge>
          {highlight && (
            <Badge className="bg-primary/10 text-primary text-xs border-0">
              Your team
            </Badge>
          )}
        </div>
      </div>

      {/* Member list */}
      <ul className="divide-y">
        {team.members.map((member) => (
          <li
            key={member.id}
            className="flex items-center gap-3 px-4 py-2.5"
          >
            <UserCircle2 className="h-5 w-5 shrink-0 text-muted-foreground/50" />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{member.name}</p>
              <p className="truncate text-xs text-muted-foreground">
                {member.email}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface FormedTeamsViewProps {
  result: FormationResult;
  /** Current user's ID — used to find their team in student mode. */
  currentUserId?: string;
  /** If true, show all teams (admin). If false, show only the student's team. */
  isAdmin: boolean;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function FormedTeamsView({
  result,
  currentUserId,
  isAdmin,
}: FormedTeamsViewProps) {
  if (isAdmin) {
    // Admin: full grid of all teams
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {result.teams.length} team{result.teams.length !== 1 ? "s" : ""} ·{" "}
            {result.teams.reduce((n, t) => n + t.members.length, 0)} students
          </p>
          <span className="text-xs text-muted-foreground">
            Run #{result.runNumber}
          </span>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {result.teams.map((team) => (
            <TeamCard key={team.teamId} team={team} />
          ))}
        </div>
      </div>
    );
  }

  // Student: find their team
  const myTeam = result.teams.find((t) =>
    t.members.some((m) => m.id === currentUserId)
  );

  if (!myTeam) {
    return (
      <p className="text-sm text-muted-foreground italic">
        You were not placed on a team for this activity.
      </p>
    );
  }

  // Show their team and the other members (everyone except themselves)
  const teammates = myTeam.members.filter((m) => m.id !== currentUserId);

  return (
    <div className="space-y-3">
      <TeamCard team={myTeam} highlight />
      {teammates.length === 0 && (
        <p className="text-xs text-muted-foreground">
          You are the only member on this team.
        </p>
      )}
    </div>
  );
}
