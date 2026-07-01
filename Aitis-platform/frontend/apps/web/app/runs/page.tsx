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
  Calendar,
  Filter,
  Loader2,
  XCircle,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { listAllExecutions } from "@/lib/api";
import type { TestExecution } from "@/lib/types";

/* ── Status config ── */
const STATUS_CONFIG: Record<string, { tone: "green" | "rose" | "blue" | "slate" | "amber"; label: string }> = {
  running:     { tone: "blue",  label: "Running" },
  in_progress: { tone: "blue",  label: "Running" },
  pending:     { tone: "slate", label: "Pending" },
  passed:      { tone: "green", label: "Passed" },
  completed:   { tone: "green", label: "Passed" },
  failed:      { tone: "rose",  label: "Failed" },
  error:       { tone: "rose",  label: "Error" },
  blocked:     { tone: "amber", label: "Blocked" },
  skipped:     { tone: "slate", label: "Skipped" },
  cancelled:   { tone: "slate", label: "Cancelled" },
};

const ACTIVE_STATUSES = new Set(["pending", "running", "in_progress"]);

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

/* ── ExecutionCard ── */
function ExecutionCard({ run }: { run: TestExecution }) {
  const cfg = STATUS_CONFIG[run.status] ?? { tone: "slate" as const, label: run.status };
  const isActive = ACTIVE_STATUSES.has(run.status);
  const date = run.started_at ?? run.created_at;
  const title = run.test_suite_name ?? `Suite ${run.test_suite_id.slice(0, 8)}`;

  const summary = run.summary;
  const passed = summary?.passed ?? 0;
  const failed = summary?.failed ?? 0;
  const total = summary?.total ?? summary?.total_cases;

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="pt-4 pb-4">
        <div className="flex items-start gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="text-xs font-mono text-slate-400">{run.id.slice(0, 8)}</span>
              <Badge tone={cfg.tone}>{cfg.label}</Badge>
              <Badge tone="slate" className="text-[10px] capitalize">{run.execution_type}</Badge>
              {run.environment && (
                <Badge tone="slate" className="text-[10px]">{run.environment}</Badge>
              )}
            </div>
            <p className="text-sm font-semibold text-slate-900 truncate">{title}</p>
            <div className="mt-2 flex items-center gap-4 text-xs text-slate-500 flex-wrap">
              <span className="flex items-center gap-1">
                <Calendar className="h-3 w-3" /> {formatDate(date)}
              </span>
              {run.duration_seconds != null && (
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" /> {formatDuration(run.duration_seconds)}
                </span>
              )}
              {summary && (
                <>
                  <span className="flex items-center gap-1 text-emerald-600">
                    <CheckCircle2 className="h-3 w-3" /> {passed} passed
                  </span>
                  {failed > 0 && (
                    <span className="flex items-center gap-1 text-rose-600">
                      <AlertTriangle className="h-3 w-3" /> {failed} failed
                    </span>
                  )}
                  {total != null && <span className="text-slate-400">of {total}</span>}
                </>
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
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/* ── Page ── */
export default function RunsPage() {
  const [runs, setRuns] = useState<TestExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");

  const fetchRuns = useCallback(async () => {
    try {
      const data = await listAllExecutions({ limit: 50 });
      setRuns(data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load runs.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  // Poll every 5 seconds while there are active runs
  useEffect(() => {
    const hasActive = runs.some((r) => ACTIVE_STATUSES.has(r.status));
    if (!hasActive) return;
    const timer = setInterval(fetchRuns, 5000);
    return () => clearInterval(timer);
  }, [runs, fetchRuns]);

  // Client-side status filter
  const filtered = statusFilter === "all"
    ? runs
    : runs.filter((r) => r.status === statusFilter);

  const activeRuns = filtered.filter((r) => ACTIVE_STATUSES.has(r.status));
  const historyRuns = filtered.filter((r) => !ACTIVE_STATUSES.has(r.status));

  return (
    <ProtectedRoute>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Runs</h1>
            <p className="text-slate-500 mt-1">
              Monitor test execution runs across all projects.
            </p>
          </div>
          <Button variant="outline" onClick={() => fetchRuns()} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 flex items-center gap-3">
            <XCircle className="h-4 w-4 text-rose-500 shrink-0" />
            <p className="text-sm text-rose-700">{error}</p>
            <Button variant="outline" size="sm" className="ml-auto" onClick={fetchRuns}>Retry</Button>
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
            <option value="pending">Pending</option>
            <option value="passed">Passed</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="error">Error</option>
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
          <Tabs defaultValue="history">
            <TabsList>
              <TabsTrigger value="active">
                Active ({activeRuns.length})
              </TabsTrigger>
              <TabsTrigger value="scheduled">
                Scheduled (0)
              </TabsTrigger>
              <TabsTrigger value="history">
                History ({historyRuns.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="active" className="space-y-3 mt-4">
              {activeRuns.length === 0 ? (
                <Card>
                  <CardContent className="py-12 text-center">
                    <PlayCircle className="h-10 w-10 mx-auto mb-3 text-slate-300" />
                    <p className="text-sm text-slate-500">No active runs.</p>
                  </CardContent>
                </Card>
              ) : (
                activeRuns.map((run) => <ExecutionCard key={run.id} run={run} />)
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
              {historyRuns.length === 0 ? (
                <Card>
                  <CardContent className="py-12 text-center">
                    <Clock className="h-10 w-10 mx-auto mb-3 text-slate-300" />
                    <p className="text-sm text-slate-500">No run history yet.</p>
                  </CardContent>
                </Card>
              ) : (
                historyRuns.map((run) => <ExecutionCard key={run.id} run={run} />)
              )}
            </TabsContent>
          </Tabs>
        )}
      </div>
    </ProtectedRoute>
  );
}
