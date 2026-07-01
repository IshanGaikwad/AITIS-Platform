"use client";

import { useEffect, useState } from "react";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Bug,
  Shield,
  PlayCircle,
  TrendingUp,
  ArrowRight,
  AlertCircle,
  Loader2,
} from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import {
  getWorkspaces,
  getDashboard,
  getReleaseReadiness,
  getDefectSummary,
} from "@/lib/api";
import type {
  DashboardResponse,
  ReleaseReadiness,
  DefectSummary,
  Workspace,
} from "@/lib/types";

/* ── Health helpers ── */
function getHealthStatus(score: number): { label: string; tone: "green" | "amber" | "rose" | "slate" } {
  if (score >= 90) return { label: "Healthy", tone: "green" };
  if (score >= 75) return { label: "At Risk", tone: "amber" };
  if (score >= 50) return { label: "Unhealthy", tone: "rose" };
  return { label: "Critical", tone: "rose" };
}

function getReleaseStatusTone(status: string): "green" | "amber" | "rose" {
  if (status === "go") return "green";
  if (status === "caution") return "amber";
  return "rose";
}

/* ── Alert helpers ── */
function AlertIcon({ type }: { type: "error" | "warning" | "info" }) {
  if (type === "error") return <XCircle className="h-4 w-4 text-rose-500 shrink-0 mt-0.5" />;
  if (type === "warning") return <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />;
  return <AlertCircle className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />;
}

function alertBorderClass(type: "error" | "warning" | "info") {
  if (type === "error") return "border-rose-200 bg-rose-50";
  if (type === "warning") return "border-amber-200 bg-amber-50";
  return "border-blue-200 bg-blue-50";
}

interface Alert {
  type: "error" | "warning" | "info";
  title: string;
  detail: string;
}

function buildAlerts(
  rr: ReleaseReadiness | null,
  defects: DefectSummary | null,
): Alert[] {
  const alerts: Alert[] = [];
  if (!rr) return alerts;

  if (rr.blocker_count > 0) {
    alerts.push({
      type: "error",
      title: `${rr.blocker_count} blocker${rr.blocker_count !== 1 ? "s" : ""} detected`,
      detail: "Blockers must be resolved before release sign-off.",
    });
  }
  if (rr.critical_count > 0) {
    alerts.push({
      type: "error",
      title: `${rr.critical_count} critical defect${rr.critical_count !== 1 ? "s" : ""} open`,
      detail: "Critical defects are blocking the release pipeline.",
    });
  }
  if (rr.test_pass_rate < 80) {
    alerts.push({
      type: "warning",
      title: `Test pass rate at ${Math.round(rr.test_pass_rate)}%`,
      detail: "Below the 80% threshold required for release sign-off.",
    });
  }
  if (defects && defects.open > 10) {
    alerts.push({
      type: "warning",
      title: `${defects.open} open defects`,
      detail: "High defect count may delay the release.",
    });
  }
  rr.recommendations.slice(0, 2).forEach((rec) => {
    alerts.push({ type: "info", title: rec, detail: "" });
  });
  return alerts;
}

/* ── Page ── */
export default function DashboardPage() {
  const { user } = useAuth();

  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [releaseReadiness, setReleaseReadiness] = useState<ReleaseReadiness | null>(null);
  const [defectSummary, setDefectSummary] = useState<DefectSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noProject, setNoProject] = useState(false);
  const [noWorkspaces, setNoWorkspaces] = useState(false);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      setNoProject(false);
      setNoWorkspaces(false);
      try {
        // No project selected yet (e.g. a fresh demo account) — prompt to create one.
        if (!user!.project_id) {
          setNoProject(true);
          setLoading(false);
          return;
        }
        const workspaces = await getWorkspaces(user!.project_id);
        if (cancelled) return;
        if (!workspaces || workspaces.length === 0) {
          setNoWorkspaces(true);
          setLoading(false);
          return;
        }
        const proj = workspaces[0];
        setWorkspace(proj);

        const [dash, rr, ds] = await Promise.all([
          getDashboard(proj.id, 30),
          getReleaseReadiness(proj.id),
          getDefectSummary(proj.id),
        ]);
        if (cancelled) return;
        setDashboard(dash);
        setReleaseReadiness(rr);
        setDefectSummary(ds);
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load dashboard data.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [user]);

  if (loading) {
    return (
      <ProtectedRoute>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
        </div>
      </ProtectedRoute>
    );
  }

  if (noProject) {
    return (
      <ProtectedRoute>
        <div className="flex flex-col items-center justify-center h-64 text-center max-w-md mx-auto">
          <Shield className="h-12 w-12 text-slate-300 mb-4" />
          <h2 className="text-lg font-semibold text-slate-700 mb-1">Welcome to AITIS</h2>
          <p className="text-slate-500 text-sm mb-4">
            You don&apos;t have any projects yet. Create your first project from the switcher
            (top-left) to start building test assets.
          </p>
          <Button asChild>
            <Link href="/studio">Get started in Studio</Link>
          </Button>
        </div>
      </ProtectedRoute>
    );
  }

  if (noWorkspaces) {
    return (
      <ProtectedRoute>
        <div className="flex flex-col items-center justify-center h-64 text-center max-w-md mx-auto">
          <Shield className="h-12 w-12 text-slate-300 mb-4" />
          <h2 className="text-lg font-semibold text-slate-700 mb-1">No workspaces in this project yet</h2>
          <p className="text-slate-500 text-sm mb-4">
            Your project is selected, but the dashboard summarizes a workspace&apos;s requirements,
            tests, and runs. Create a workspace inside it to start tracking quality metrics.
          </p>
          <Button asChild>
            <Link href="/studio">Open Studio to create a workspace</Link>
          </Button>
        </div>
      </ProtectedRoute>
    );
  }

  if (error) {
    return (
      <ProtectedRoute>
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-6 text-center">
          <XCircle className="h-8 w-8 text-rose-400 mx-auto mb-2" />
          <p className="text-sm font-medium text-rose-700">{error}</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={() => window.location.reload()}>
            Retry
          </Button>
        </div>
      </ProtectedRoute>
    );
  }

  const rr = releaseReadiness;
  const ds = defectSummary;
  const metrics = dashboard?.metrics;

  const healthScore = rr ? Math.round(rr.overall_score) : 0;
  const healthStatus = getHealthStatus(healthScore);
  const alerts = buildAlerts(rr, ds);

  const passRate = rr ? Math.round(rr.test_pass_rate) : 0;
  const passRateColor = passRate >= 90 ? "text-green-600" : passRate >= 70 ? "text-amber-600" : "text-rose-600";

  const defectRows = [
    { severity: "Critical", count: ds?.critical ?? 0, tone: "rose" as const },
    { severity: "Major", count: ds?.major ?? 0, tone: "amber" as const },
    { severity: "Minor", count: ds?.minor ?? 0, tone: "blue" as const },
    { severity: "Trivial", count: ds?.trivial ?? 0, tone: "slate" as const },
  ];

  const totalCases = metrics?.total_test_cases ?? 0;
  const passedCases = totalCases > 0 ? Math.round((passRate / 100) * totalCases) : 0;
  const failedCases = totalCases - passedCases;

  const testRows = [
    { status: "Passed", count: passedCases, tone: "green" as const },
    { status: "Failed", count: failedCases > 0 ? failedCases : 0, tone: "rose" as const },
  ];

  return (
    <ProtectedRoute>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
            <p className="text-slate-500 mt-1">
              {workspace ? `${workspace.name} — project overview` : "Project overview"}
            </p>
          </div>
          <Button variant="outline" asChild>
            <Link href="/insights">
              View Insights <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>

        {/* Top row */}
        <div className="grid gap-4 lg:grid-cols-3">
          {/* Health Score */}
          <Card className="lg:col-span-1">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-500 flex items-center gap-2">
                <Shield className="h-4 w-4" /> Project Health Score
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-end gap-2">
                <span className="text-4xl font-bold text-slate-900">{healthScore}</span>
                <span className="text-slate-400 mb-1">/ 100</span>
                <Badge tone={healthStatus.tone} className="ml-auto mb-1">{healthStatus.label}</Badge>
              </div>
              <p className="text-xs text-slate-500 mt-3 leading-relaxed">
                {rr && rr.recommendations.length > 0
                  ? rr.recommendations[0]
                  : "Overall quality score based on test pass rate, coverage, and open defects."}
              </p>
            </CardContent>
          </Card>

          {/* Release Readiness */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-500 flex items-center gap-2">
                <TrendingUp className="h-4 w-4" /> Release Readiness
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-semibold text-slate-900 truncate">
                  {workspace?.name ?? "Current Release"}
                </p>
                {rr && (
                  <Badge tone={getReleaseStatusTone(rr.status)}>
                    {rr.status === "go" ? "Go" : rr.status === "caution" ? "Caution" : "No Go"}
                  </Badge>
                )}
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Pass Rate</span>
                  <span className={`font-semibold ${passRateColor}`}>{passRate}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Open Blockers</span>
                  <span className="font-semibold text-rose-600">{rr?.blocker_count ?? 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Coverage</span>
                  <span className="font-medium text-slate-700">{Math.round(rr?.coverage_score ?? 0)}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Automation</span>
                  <span className="font-medium text-slate-700">{Math.round(rr?.automation_score ?? 0)}%</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Latest Execution */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-500 flex items-center gap-2">
                <PlayCircle className="h-4 w-4" /> Test Overview
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Total Cases</span>
                  <span className="font-semibold text-slate-900">{totalCases}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Last Pass Rate</span>
                  <span className={`font-semibold ${passRateColor}`}>{passRate}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Total Scripts</span>
                  <span className="font-medium text-slate-700">{metrics?.total_automation_scripts ?? 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Requirements</span>
                  <span className="font-medium text-slate-700">{metrics?.total_requirements ?? 0}</span>
                </div>
              </div>
              <div className="mt-3">
                <Button variant="outline" size="sm" className="w-full" asChild>
                  <Link href="/runs">View All Runs <ArrowRight className="ml-1 h-3 w-3" /></Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Bottom row */}
        <div className="grid gap-4 lg:grid-cols-2">
          {/* Test Case Status */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-slate-700 flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4" /> Test Case Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2.5">
                {testRows.map((row) => {
                  const pct = totalCases > 0 ? Math.round((row.count / totalCases) * 100) : 0;
                  return (
                    <div key={row.status} className="flex items-center gap-3">
                      <span className="w-20 text-xs text-slate-500 shrink-0">{row.status}</span>
                      <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${row.tone === "green" ? "bg-green-400" : "bg-rose-400"}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="w-8 text-xs font-semibold text-slate-700 text-right shrink-0">
                        {row.count}
                      </span>
                    </div>
                  );
                })}
              </div>
              <p className="text-xs text-slate-400 mt-3">Total: {totalCases} test cases</p>
            </CardContent>
          </Card>

          {/* Defect Status */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-slate-700 flex items-center gap-2">
                <Bug className="h-4 w-4" /> Defect Status by Severity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3">
                {defectRows.map((row) => (
                  <div
                    key={row.severity}
                    className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 px-3 py-2.5"
                  >
                    <div>
                      <p className="text-xs text-slate-500">{row.severity}</p>
                      <p className="text-xl font-bold text-slate-900 mt-0.5">{row.count}</p>
                    </div>
                    <Badge tone={row.tone}>{row.severity[0]}</Badge>
                  </div>
                ))}
              </div>
              <p className="text-xs text-slate-400 mt-3">
                Total open: {ds?.open ?? 0} defects
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Risks and Alerts */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-slate-700 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" /> Risks and Alerts
            </CardTitle>
          </CardHeader>
          <CardContent>
            {alerts.length === 0 ? (
              <div className="flex items-center gap-2 text-sm text-slate-500 py-2">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                No active risks or alerts. Project is in good shape.
              </div>
            ) : (
              <div className="space-y-2">
                {alerts.map((alert, i) => (
                  <div
                    key={i}
                    className={`flex items-start gap-3 rounded-lg border p-3 ${alertBorderClass(alert.type)}`}
                  >
                    <AlertIcon type={alert.type} />
                    <div>
                      <p className="text-sm font-medium text-slate-900">{alert.title}</p>
                      {alert.detail && <p className="text-xs text-slate-600 mt-0.5">{alert.detail}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  );
}
