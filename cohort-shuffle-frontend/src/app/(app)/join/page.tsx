"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Users, ArrowRight, Loader2, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { Cohort } from "@/types";
import {
  fetchEligibleCohorts,
  joinCohort,
  validateJoinToken,
} from "@/lib/mocks/cohorts";
import { useCohort } from "@/contexts/CohortContext";

// ─── Join-link flow ────────────────────────────────────────────────────────────

function JoinByToken({ token }: { token: string }) {
  const router = useRouter();
  const { refreshCohorts, setActiveCohort } = useCohort();
  const [cohort, setCohort] = useState<Cohort | null>(null);
  const [status, setStatus] = useState<
    "loading" | "ready" | "joining" | "done" | "invalid"
  >("loading");

  useEffect(() => {
    validateJoinToken(token).then((c) => {
      if (c) {
        setCohort(c);
        setStatus("ready");
      } else {
        setStatus("invalid");
      }
    });
  }, [token]);

  const handleJoin = async () => {
    if (!cohort) return;
    setStatus("joining");
    await joinCohort(cohort.id);
    await refreshCohorts();
    setActiveCohort(cohort);
    setStatus("done");
    setTimeout(() => router.push("/dashboard"), 1200);
  };

  if (status === "loading") {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-muted-foreground">
        <Loader2 className="h-6 w-6 animate-spin" />
        <p className="text-sm">Validating join link…</p>
      </div>
    );
  }

  if (status === "invalid") {
    return (
      <div className="rounded-xl border bg-card p-8 text-center space-y-2">
        <p className="font-medium text-destructive">
          This join link is invalid or has expired.
        </p>
        <p className="text-sm text-muted-foreground">
          Ask your admin for a new link.
        </p>
      </div>
    );
  }

  if (status === "done") {
    return (
      <div className="rounded-xl border bg-card p-8 text-center space-y-2">
        <CheckCircle2 className="mx-auto h-8 w-8 text-green-500" />
        <p className="font-medium">Joined! Redirecting…</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border bg-card p-8 space-y-4">
      <div className="space-y-1">
        <p className="text-sm text-muted-foreground">You've been invited to join</p>
        <h2 className="text-xl font-semibold">{cohort?.name}</h2>
      </div>
      <Button
        onClick={handleJoin}
        disabled={status === "joining"}
        className="w-full"
      >
        {status === "joining" ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <ArrowRight className="mr-2 h-4 w-4" />
        )}
        Join cohort
      </Button>
    </div>
  );
}

// ─── Eligible cohorts flow ─────────────────────────────────────────────────────

function EligibleCohorts() {
  const router = useRouter();
  const { refreshCohorts, setActiveCohort } = useCohort();
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [joiningId, setJoiningId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchEligibleCohorts().then((data) => {
      setCohorts(data);
      setIsLoading(false);
    });
  }, []);

  const handleJoin = async (cohort: Cohort) => {
    setJoiningId(cohort.id);
    await joinCohort(cohort.id);
    await refreshCohorts();
    setActiveCohort(cohort);
    router.push("/dashboard");
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-muted-foreground">
        <Loader2 className="h-6 w-6 animate-spin" />
        <p className="text-sm">Looking for cohorts you can join…</p>
      </div>
    );
  }

  if (cohorts.length === 0) {
    return (
      <div className="rounded-xl border border-dashed p-10 text-center space-y-2">
        <Users className="mx-auto h-8 w-8 text-muted-foreground" />
        <p className="font-medium">No cohorts available to join</p>
        <p className="text-sm text-muted-foreground">
          Ask your admin to share a join link or invite you directly.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {cohorts.map((cohort) => (
        <div
          key={cohort.id}
          className="flex items-center justify-between rounded-xl border bg-card p-4"
        >
          <div className="space-y-0.5">
            <p className="font-medium">{cohort.name}</p>
            {cohort.allowedDomains && (
              <p className="text-xs text-muted-foreground">
                {cohort.allowedDomains.join(", ")}
              </p>
            )}
          </div>
          <Button
            size="sm"
            onClick={() => handleJoin(cohort)}
            disabled={joiningId === cohort.id}
          >
            {joiningId === cohort.id ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              "Join"
            )}
          </Button>
        </div>
      ))}
    </div>
  );
}

// ─── Inner page content (reads search params — must be inside Suspense) ────────

function JoinPageContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  return (
    <div className="flex min-h-[calc(100vh-56px)] items-center justify-center px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Join a cohort</h1>
          <p className="text-muted-foreground text-sm">
            {token
              ? "You've been invited to join a cohort."
              : "Select a cohort to get started."}
          </p>
        </div>

        <Badge variant="secondary" className="text-xs">
          You can join multiple cohorts — histories are kept separate.
        </Badge>

        {token ? <JoinByToken token={token} /> : <EligibleCohorts />}
      </div>
    </div>
  );
}

// ─── Page (exported) ───────────────────────────────────────────────────────────

export default function JoinPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[calc(100vh-56px)] items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      }
    >
      <JoinPageContent />
    </Suspense>
  );
}
