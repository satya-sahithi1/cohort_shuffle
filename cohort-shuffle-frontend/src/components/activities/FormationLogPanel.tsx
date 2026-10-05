"use client";

/**
 * FormationLogPanel — formation run history.
 *
 * Shows each run as a row: run number, when it ran, who triggered it,
 * repeat pairs, saturation percentage, and score.
 * Used in the admin view of the activity detail page.
 */

import { History, Bot, User } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { FormationLog } from "@/types";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function saturationColor(saturation: number): string {
  if (saturation >= 0.8) return "text-red-600 dark:text-red-400";
  if (saturation >= 0.5) return "text-orange-600 dark:text-orange-400";
  return "text-green-700 dark:text-green-400";
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface FormationLogPanelProps {
  logs: FormationLog[];
}

// ─── Component ────────────────────────────────────────────────────────────────

export function FormationLogPanel({ logs }: FormationLogPanelProps) {
  if (logs.length === 0) {
    return (
      <p className="text-sm italic text-muted-foreground">
        No formation runs yet.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {logs.map((log, i) => (
        <div
          key={log.id}
          className={`rounded-lg border p-3 text-sm ${
            i === 0 ? "border-primary/30 bg-primary/5" : "bg-card"
          }`}
        >
          <div className="flex flex-wrap items-start justify-between gap-2">
            {/* Left: run info */}
            <div className="flex items-center gap-2 font-medium">
              <History className="h-4 w-4 shrink-0 text-muted-foreground" />
              Run #{log.runNumber}
              {i === 0 && (
                <Badge variant="secondary" className="text-xs">
                  Latest
                </Badge>
              )}
            </div>

            {/* Right: timestamp + who triggered */}
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              {log.triggeredBy === null ? (
                <Bot className="h-3.5 w-3.5 shrink-0" />
              ) : (
                <User className="h-3.5 w-3.5 shrink-0" />
              )}
              <span>
                {log.triggeredBy === null
                  ? "Auto"
                  : log.triggeredByName ?? "Admin"}
              </span>
              <span>·</span>
              <span>{formatDateTime(log.createdAt)}</span>
            </div>
          </div>

          {/* Stats row */}
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span>
              Score:{" "}
              <span className="font-medium text-foreground">{log.score}</span>
            </span>
            <span>
              Repeat pairs:{" "}
              <span
                className={`font-medium ${
                  log.repeatPairs === 0
                    ? "text-green-700 dark:text-green-400"
                    : "text-foreground"
                }`}
              >
                {log.repeatPairs}
              </span>
            </span>
            <span>
              Saturation:{" "}
              <span
                className={`font-medium ${saturationColor(log.saturation)}`}
              >
                {Math.round(log.saturation * 100)}%
              </span>
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
