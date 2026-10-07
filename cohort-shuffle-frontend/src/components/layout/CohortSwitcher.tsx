"use client";

import { ChevronsUpDown } from "lucide-react";
import { useCohort } from "@/contexts/CohortContext";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";

export function CohortSwitcher() {
  const { cohorts, activeCohort, setActiveCohort, isLoading } = useCohort();

  if (isLoading) {
    return (
      <div className="h-8 w-48 animate-pulse rounded-md bg-muted" />
    );
  }

  if (!activeCohort) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Switch cohort"
        className="flex max-w-[140px] sm:max-w-[208px] items-center justify-between gap-2 rounded-md border bg-background px-3 py-1.5 text-sm font-medium shadow-sm transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <span className="truncate">{activeCohort.name}</span>
        <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="center" className="w-52">
        <DropdownMenuLabel className="text-xs text-muted-foreground">
          Your cohorts
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {cohorts.map((cohort) => (
          <DropdownMenuItem
            key={cohort.id}
            onClick={() => setActiveCohort(cohort)}
            className="flex items-center justify-between gap-2"
          >
            <span className="truncate">{cohort.name}</span>
            <div className="flex items-center gap-1">
              {cohort.id === activeCohort.id && (
                <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              )}
              {cohort.role === "admin" && (
                <Badge variant="secondary" className="text-xs px-1 py-0">
                  Admin
                </Badge>
              )}
            </div>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
