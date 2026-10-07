"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Settings,
  ArrowLeft,
  Loader2,
  RefreshCw,
  Copy,
  CheckCheck,
  Link as LinkIcon,
  Globe,
  Building2,
  UserPlus,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCohort } from "@/contexts/CohortContext";
import { apiFetch } from "@/lib/api/client";

// ─── Backend shapes ────────────────────────────────────────────────────────────

interface CohortDetailBackend {
  id: string;
  name: string;
  allowed_domain: string | null;
  role: "admin" | "student";
  created_at: string;
}

interface JoinLinkBackend {
  token: string;
  url: string;
}

// ─── Invite link panel ─────────────────────────────────────────────────────────

function InviteLinkPanel({ cohortId }: { cohortId: string }) {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<JoinLinkBackend>(
        `/cohorts/${cohortId}/join-link`
      );
      setUrl(data.url);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to generate invite link.");
    } finally {
      setLoading(false);
    }
  };

  const copy = async () => {
    if (!url) return;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <LinkIcon className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-sm font-medium">Invite link</h3>
      </div>
      <p className="text-xs text-muted-foreground">
        Generate a shareable link for new students. The link is valid for 72
        hours and can be regenerated at any time.
      </p>

      {error && (
        <p className="flex items-center gap-1.5 text-xs text-destructive">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          {error}
        </p>
      )}

      {url ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Input
              value={url}
              readOnly
              className="text-xs font-mono h-8"
            />
            <Button
              size="sm"
              variant="outline"
              onClick={copy}
              className="shrink-0"
            >
              {copied ? (
                <CheckCheck className="h-4 w-4 text-green-600" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={generate}
            disabled={loading}
            className="text-xs h-7"
          >
            {loading && (
              <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
            )}
            Regenerate link
          </Button>
        </div>
      ) : (
        <Button
          size="sm"
          variant="outline"
          onClick={generate}
          disabled={loading}
        >
          {loading ? (
            <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
          ) : (
            <LinkIcon className="mr-1.5 h-4 w-4" />
          )}
          Generate invite link
        </Button>
      )}
    </div>
  );
}

// ─── Add member by email panel ────────────────────────────────────────────────

function AddMemberPanel({ cohortId }: { cohortId: string }) {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await apiFetch(`/cohorts/${cohortId}/members`, {
        method: "POST",
        body: JSON.stringify({ email: trimmed, role: "student" }),
      });
      setSuccess(`${trimmed} has been added to the cohort.`);
      setEmail("");
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Failed to add member."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <UserPlus className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-sm font-medium">Add member by email</h3>
      </div>
      <p className="text-xs text-muted-foreground">
        Add a student directly by their Google account email. They will appear
        in the roster once they sign in for the first time.
      </p>

      <form onSubmit={handleAdd} className="flex items-end gap-2">
        <div className="flex-1 space-y-1.5">
          <Label htmlFor="add-member-email" className="text-xs">
            Email address
          </Label>
          <Input
            id="add-member-email"
            type="email"
            placeholder="student@university.edu"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
            className="h-8 text-sm"
          />
        </div>
        <Button
          type="submit"
          size="sm"
          disabled={loading || !email.trim()}
          className="mb-0"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <UserPlus className="h-4 w-4" />
          )}
        </Button>
      </form>

      {success && (
        <p className="flex items-center gap-1.5 text-xs text-green-700 dark:text-green-400">
          <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
          {success}
        </p>
      )}
      {error && (
        <p className="flex items-center gap-1.5 text-xs text-destructive">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          {error}
        </p>
      )}
    </div>
  );
}

// ─── Cohort info card ──────────────────────────────────────────────────────────

function CohortInfoCard({ cohort }: { cohort: CohortDetailBackend }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Building2 className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-sm font-medium">Cohort details</h3>
      </div>
      <div className="rounded-lg border divide-y text-sm">
        <div className="flex items-center justify-between px-4 py-3">
          <span className="text-muted-foreground">Name</span>
          <span className="font-medium">{cohort.name}</span>
        </div>
        <div className="flex items-center justify-between gap-3 px-4 py-3">
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Globe className="h-3.5 w-3.5 shrink-0" />
            Domain restriction
          </span>
          {cohort.allowed_domain ? (
            <Badge variant="outline" className="font-mono text-xs">
              @{cohort.allowed_domain}
            </Badge>
          ) : (
            <span className="text-xs text-muted-foreground">
              None — any Google account
            </span>
          )}
        </div>
        <div className="flex items-center justify-between gap-3 px-4 py-3">
          <span className="text-muted-foreground">Cohort ID</span>
          <span className="font-mono text-xs text-muted-foreground truncate max-w-[160px] sm:max-w-none">
            {cohort.id}
          </span>
        </div>
        <div className="flex items-center justify-between px-4 py-3">
          <span className="text-muted-foreground">Created</span>
          <span className="text-xs">
            {new Date(cohort.created_at).toLocaleDateString(undefined, {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </span>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">
        To rename this cohort or change the domain restriction, update the
        database directly or contact your system administrator. These fields
        are not editable through the UI yet.
      </p>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AdminSettingsPage() {
  const { activeCohort } = useCohort();
  const [cohortDetail, setCohortDetail] =
    useState<CohortDetailBackend | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!activeCohort) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<CohortDetailBackend>(
        `/cohorts/${activeCohort.id}`
      );
      setCohortDetail(data);
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Failed to load cohort details."
      );
    } finally {
      setLoading(false);
    }
  }, [activeCohort]);

  useEffect(() => {
    load();
  }, [load]);

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
            Cohort settings
          </h1>
          <p className="text-sm text-muted-foreground">
            {activeCohort?.name ?? "Select a cohort"} — invite links, member
            management, and cohort details.
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={load}
          disabled={loading}
        >
          <RefreshCw
            className={`mr-1.5 h-4 w-4 ${loading ? "animate-spin" : ""}`}
          />
          Refresh
        </Button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* No cohort selected */}
      {!activeCohort && !loading && (
        <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed py-20 text-center">
          <Settings className="h-10 w-10 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">
            Select a cohort to manage its settings.
          </p>
        </div>
      )}

      {/* Loading */}
      {loading && activeCohort && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Content */}
      {!loading && activeCohort && cohortDetail && (
        <div className="grid gap-8 lg:grid-cols-2">
          {/* Left column — cohort info + invite link */}
          <div className="space-y-8">
            <CohortInfoCard cohort={cohortDetail} />
            <div className="border-t pt-6">
              <InviteLinkPanel cohortId={activeCohort.id} />
            </div>
          </div>

          {/* Right column — add member + manage members link */}
          <div className="space-y-8">
            <AddMemberPanel cohortId={activeCohort.id} />
            <div className="border-t pt-6 space-y-3">
              <div className="flex items-center gap-2">
                <Settings className="h-4 w-4 text-muted-foreground" />
                <h3 className="text-sm font-medium">Member roster</h3>
              </div>
              <p className="text-xs text-muted-foreground">
                View all members, archive departing students, and manage admin
                roles.
              </p>
              <Button size="sm" variant="outline" asChild>
                <Link href="/admin/members">Manage members →</Link>
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
