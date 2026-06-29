"use client";

import { useState, useEffect, useCallback } from "react";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  PlayCircle,
  Clock,
  User,
  Calendar,
  Filter,
  Loader2,
  XCircle,
  RefreshCw,
} from "lucide-react";
import { listExecutionJobs, cancelExecutionJob } from "@/lib/api";
import type { ExecutionJobSummary } from "@/lib/types";

/* ── Status config ── */
type StatusKey = "queued" | "running" | "provisioning" | "passed" | "failed" | "cancelled" | "timed_out" | "infrastructure_error";

const STATUS_CONFIG: Record<string, { tone: "green" | "rose" | "blue" | "slate" | "amber"; label: string }> = {
  running:               { tone: "blue",  label: "Running" },
  provisioning:          { tone: "blue",  label: "Provisioning" },
  queued:                { tone: "slate", label: "Queued" },
  passed:                { tone: "green", label: "Passed" },
  failed:                { tone: "rose",  label: "Failed" },
  cancelled:             { tone: "slate", label: "Cancelled" },
  timed_out:             { tone: "amber", label: "Timed Out" },
  infrastructure_error:  { tone: "rose",  label: "Error" },
};

const ACTIVE_STATUSES = new Set(["queued", "running", "provisioning"]);
const HISTORY_STATUSES = new Set(["passed", "failed", "cancelled", "timed_out", "infrastructure_error"]);

/* ── Helpers ── */
function formatDuration(seconds?: number | null): string {
  if (!seconds) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

function formatDate(iso?: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "short",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

/* ── JobCard ── */
function JobCard({
  job,
  onCancel,
  cancelling,
}: {
  job: ExecutionJobSummary;
  onCancel?: (id: string) => void;
  cancelling?: boolean;
}) {
  const cfg = STATUS_CONFIG[job.status] ?? { tone: "slate" as const, label: job.status };
  const isActive = ACTIVE_STATUSES.has(job.status);
  const date = job.started_at ?? job.queued_at ?? job.created_at;

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="pt-4 pb-4">
        <div className="flex items-start gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="text-xs font-mono text-slate-400">{job.id.slice(0, 8)}</span>
              <Badge tone={cfg.tone}>{cfg.label}</Badge>
              {job.browser && <Badge tone="slate" className="text-[10px]">{job.browser}</Badge>}
            </div>
            <p className="text-sm font-semibold text-slate-900 truncate">
              Script: {job.script_id.slice(0, 16)}
            </p>
            <div className="mt-2 flex items-center gap-4 text-xs text-slate-500 flex-wrap">
              <span className="flex items-center gap-1">
                <User className="h-3 w-3" /> Automation
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="h-3 w-3" /> {formatDate(date)}
              </span>
              {job.duration_seconds != null && (
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" /> {formatDuration(job.duration_seconds)}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {isActive && (
              <div className="flex items-center gap-1.5 text-blue-600">
                <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
                <span className="text-xs font-medium">Running</span>
              </div>
            )}
            {isActive && onCancel && (
              <Button
                variant="outline"
                size="sm"
                disabled={cancelling}
                onClick={() => onCancel(job.id)}
              >
                {cancelling ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Cancel"}
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/* ── Page ── */
export default function RunsPage() {
  const [jobs, setJobs] = useState<ExecutionJobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    try {
      const data = await listExecutionJobs({ limit: 50 });
      setJobs(data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load runs.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  // Poll every 5 seconds when there are active jobs
  useEffect(() => {
    const hasActive = jobs.some((j) => ACTIVE_STATUSES.has(j.status));
    if (!hasActive) return;
    const timer = setInterval(fetchJobs, 5000);
    return () => clearInterval(timer);
  }, [jobs, fetchJobs]);

  async function handleCancel(id: string) {
    setCancellingId(id);
    try {
      await cancelExecutionJob(id);
      await fetchJobs();
    } catch {
      // silently refresh
    } finally {
      setCancellingId(null);
    }
  }

  // Client-side status filter
  const filtered = statusFilter === "all"
    ? jobs
    : jobs.filter((j) => j.status === statusFilter);

  const activeJobs = filtered.filter((j) => ACTIVE_STATUSES.has(j.status));
  const historyJobs = filtered.filter((j) => HISTORY_STATUSES.has(j.status));

  return (
    <ProtectedRoute>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Runs</h1>
            <p className="text-slate-500 mt-1">
              Monitor test execution runs across all workspaces.
            </p>
          </div>
          <Button variant="outline" onClick={() => fetchJobs()} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 flex items-center gap-3">
            <XCircle className="h-4 w-4 text-rose-500 shrink-0" />
            <p className="text-sm text-rose-700">{error}</p>
            <Button variant="outline" size="sm" className="ml-auto" onClick={fetchJobs}>Retry</Button>
          </div>
        )}

        {/* Filter Bar */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Filter className="h-4 w-4" />
            <span>Filter:</span>
          </div>
          <select
            className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-300"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="running">Running</option>
            <option value="queued">Queued</option>
            <option value="passed">Passed</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
            <option value="timed_out">Timed Out</option>
          </select>
        </div>

        {/* Loading skeleton */}
        {loading && (
          <div className="flex items-center justify-center h-48">
            <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
          </div>
        )}

        {/* Tabs */}
        {!loading && (
          <Tabs defaultValue="active">
            <TabsList>
              <TabsTrigger value="active">
                Active ({activeJobs.length})
              </TabsTrigger>
              <TabsTrigger value="scheduled">
                Scheduled (0)
              </TabsTrigger>
              <TabsTrigger value="history">
                History ({historyJobs.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="active" className="space-y-3 mt-4">
              {activeJobs.length === 0 ? (
                <Card>
                  <CardContent className="py-12 text-center">
                    <PlayCircle className="h-10 w-10 mx-auto mb-3 text-slate-300" />
                    <p className="text-sm text-slate-500">No active runs.</p>
                  </CardContent>
                </Card>
              ) : (
                activeJobs.map((job) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    onCancel={handleCancel}
                    cancelling={cancellingId === job.id}
                  />
                ))
              )}
            </TabsContent>

            <TabsContent value="scheduled" className="space-y-3 mt-4">
              <Card>
                <CardContent className="py-12 text-center">
                  <Calendar className="h-10 w-10 mx-auto mb-3 text-slate-300" />
                  <p className="text-sm font-medium text-slate-600">No scheduled runs</p>
                  <p className="text-xs text-slate-400 mt-1">
                    Scheduled execution is managed via CI/CD pipeline triggers.
                  </p>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="history" className="space-y-3 mt-4">
              {historyJobs.length === 0 ? (
                <Card>
                  <CardContent className="py-12 text-center">
                    <Clock className="h-10 w-10 mx-auto mb-3 text-slate-300" />
                    <p className="text-sm text-slate-500">No run history yet.</p>
                  </CardContent>
                </Card>
              ) : (
                historyJobs.map((job) => <JobCard key={job.id} job={job} />)
              )}
            </TabsContent>
          </Tabs>
        )}
      </div>
    </ProtectedRoute>
  );
}
