"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Users,
  UserPlus,
  ArrowLeft,
  Loader2,
  RefreshCw,
  Search,
  Shield,
  GraduationCap,
  Copy,
  CheckCheck,
  Link as LinkIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { fetchCohortMembers, type CohortMember } from "@/lib/api/cohorts";
import { useCohort } from "@/contexts/CohortContext";
import { apiFetch } from "@/lib/api/client";

// ─── Invite link modal ─────────────────────────────────────────────────────────

function InviteLinkPanel({ cohortId }: { cohortId: string }) {
  const [link, setLink] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<{ invite_url: string }>(
        `/cohorts/${cohortId}/invite-link`,
        { method: "POST" }
      );
      setLink(data.invite_url);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to generate invite link.");
    } finally {
      setLoading(false);
    }
  };

  const copy = async () => {
    if (!link) return;
    await navigator.clipboard.writeText(link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl border bg-card p-4 space-y-3">
      <div className="flex items-center gap-2">
        <LinkIcon className="h-4 w-4 text-muted-foreground" />
        <p className="text-sm font-medium">Invite link</p>
      </div>
      <p className="text-xs text-muted-foreground">
        Generate a one-time join link to share with new members.
        The link is valid for 7 days.
      </p>
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
      {link ? (
        <div className="flex items-center gap-2">
          <Input
            value={link}
            readOnly
            className="text-xs font-mono h-8"
          />
          <Button size="sm" variant="outline" onClick={copy} className="shrink-0">
            {copied ? (
              <CheckCheck className="h-4 w-4 text-green-600" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
          </Button>
        </div>
      ) : (
        <Button size="sm" variant="outline" onClick={generate} disabled={loading}>
          {loading ? (
            <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
          ) : (
            <UserPlus className="mr-1.5 h-4 w-4" />
          )}
          Generate invite link
        </Button>
      )}
    </div>
  );
}

// ─── Member row ────────────────────────────────────────────────────────────────

function MemberRow({ member }: { member: CohortMember }) {
  return (
    <li className="flex items-center justify-between px-4 py-3">
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-medium uppercase text-muted-foreground">
          {member.name.charAt(0)}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{member.name}</p>
          <p className="truncate text-xs text-muted-foreground">{member.email}</p>
        </div>
      </div>
      <Badge
        variant={member.role === "admin" ? "default" : "secondary"}
        className="ml-3 shrink-0 gap-1"
      >
        {member.role === "admin" ? (
          <Shield className="h-3 w-3" />
        ) : (
          <GraduationCap className="h-3 w-3" />
        )}
        {member.role}
      </Badge>
    </li>
  );
}

// ─── Empty state ───────────────────────────────────────────────────────────────

function EmptyState({ filtered }: { filtered: boolean }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
      <Users className="h-10 w-10 text-muted-foreground/40" />
      <div className="space-y-1">
        <p className="text-sm font-medium text-muted-foreground">
          {filtered ? "No members match your search" : "No members yet"}
        </p>
        {!filtered && (
          <p className="text-xs text-muted-foreground">
            Generate an invite link to add students to this cohort.
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminMembersPage() {
  const { activeCohort } = useCohort();
  const [members, setMembers] = useState<CohortMember[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!activeCohort) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCohortMembers(activeCohort.id);
      setMembers(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load members.");
    } finally {
      setLoading(false);
    }
  }, [activeCohort]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = members.filter(
    (m) =>
      !query ||
      m.name.toLowerCase().includes(query.toLowerCase()) ||
      m.email.toLowerCase().includes(query.toLowerCase())
  );

  const adminCount = members.filter((m) => m.role === "admin").length;
  const studentCount = members.filter((m) => m.role === "student").length;

  return (
    <div className="space-y-6">
      {/* Back */}
      <Button variant="ghost" size="sm" asChild>
        <Link href="/admin">
          <ArrowLeft className="mr-1.5 h-4 w-4" />
          Back to admin
        </Link>
      </Button>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Cohort members
          </h1>
          <p className="text-sm text-muted-foreground">
            {activeCohort?.name ?? "Select a cohort"}
            {members.length > 0 && (
              <span>
                {" "}· {members.length} member{members.length !== 1 ? "s" : ""}
                {adminCount > 0 && ` (${adminCount} admin${adminCount !== 1 ? "s" : ""})`}
              </span>
            )}
          </p>
        </div>
        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-1.5 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Invite link panel */}
      {activeCohort && (
        <InviteLinkPanel cohortId={activeCohort.id} />
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Stats strip */}
      {!loading && members.length > 0 && (
        <div className="flex flex-wrap gap-3">
          <div className="rounded-lg border bg-card px-4 py-3 text-center min-w-[80px]">
            <p className="text-xl font-semibold">{members.length}</p>
            <p className="text-xs text-muted-foreground">total</p>
          </div>
          <div className="rounded-lg border bg-card px-4 py-3 text-center min-w-[80px]">
            <p className="text-xl font-semibold">{studentCount}</p>
            <p className="text-xs text-muted-foreground">students</p>
          </div>
          <div className="rounded-lg border bg-card px-4 py-3 text-center min-w-[80px]">
            <p className="text-xl font-semibold">{adminCount}</p>
            <p className="text-xs text-muted-foreground">admins</p>
          </div>
        </div>
      )}

      {/* Search */}
      {!loading && members.length > 0 && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name or email…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      )}

      {/* Member list */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState filtered={query.length > 0} />
      ) : (
        <div className="rounded-xl border bg-card overflow-hidden">
          {/* Admins section */}
          {filtered.some((m) => m.role === "admin") && (
            <>
              <div className="border-b bg-muted/40 px-4 py-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Admins
                </p>
              </div>
              <ul className="divide-y">
                {filtered
                  .filter((m) => m.role === "admin")
                  .map((m) => (
                    <MemberRow key={m.id} member={m} />
                  ))}
              </ul>
            </>
          )}

          {/* Students section */}
          {filtered.some((m) => m.role === "student") && (
            <>
              <div className={`${filtered.some((m) => m.role === "admin") ? "border-t" : ""} border-b bg-muted/40 px-4 py-2`}>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Students
                </p>
              </div>
              <ul className="divide-y">
                {filtered
                  .filter((m) => m.role === "student")
                  .map((m) => (
                    <MemberRow key={m.id} member={m} />
                  ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}
