"use client";

import { useEffect, useState } from "react";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  FileText,
  Download,
  TrendingUp,
  TrendingDown,
  Bug,
  CheckCircle2,
  AlertTriangle,
  BarChart3,
  Link2,
  Shuffle,
  Loader2,
  Plus,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import {
  getProjects,
  listExecutionJobs,
  getDefects,
  createDefect,
  getTraceabilityMatrix,
  getRequirementCoverage,
  getDashboard,
} from "@/lib/api";
import type {
  ExecutionJobSummary,
  Defect,
  TraceabilityMatrix,
  RequirementCoverageReport,
} from "@/lib/types";
import { useToast } from "@/components/ui/use-toast";

const SEV_TONE: Record<string, "rose" | "amber" | "blue" | "slate"> = {
  critical: "rose",
  major: "amber",
  minor: "blue",
  trivial: "slate",
};

const fmt = (iso?: string | null) => iso ? new Date(iso).toLocaleDateString() : "—";
const dur = (s?: number | null) => !s ? "—" : s < 60 ? `${Math.round(s)}s` : `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;

/* ── New Defect Dialog ── */
interface NewDefectDialogProps {
  open: boolean;
  onClose: () => void;
  projectId: string;
  onCreated: () => void;
}

function NewDefectDialog({ open, onClose, projectId, onCreated }: NewDefectDialogProps) {
  const { toast } = useToast();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState("major");
  const [steps, setSteps] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    try {
      await createDefect({
        project_id: projectId || "default",
        title: title.trim(),
        description,
        severity,
        steps_to_reproduce: steps,
      });
      toast({ title: "Defect created successfully." });
      onCreated();
      onClose();
      setTitle("");
      setDescription("");
      setSeverity("major");
      setSteps("");
    } catch (err: unknown) {
      toast({
        title: "Failed to create defect",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New Defect</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 mt-2">
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Title *</label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Defect title" required />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Severity</label>
            <select
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-300"
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
            >
              <option value="critical">Critical</option>
              <option value="major">Major</option>
              <option value="minor">Minor</option>
              <option value="trivial">Trivial</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Description</label>
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Describe the issue..." rows={3} />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Steps to Reproduce</label>
            <Textarea value={steps} onChange={(e) => setSteps(e.target.value)} placeholder="1. Go to...\n2. Click..." rows={3} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={saving || !title.trim()}>
              {saving && <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />}
              Create Defect
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ── Page ── */
export default function InsightsPage() {
  const { user } = useAuth();
  const { toast } = useToast();

  const [projectId, setProjectId] = useState<string>("");
  const [reports, setReports] = useState<ExecutionJobSummary[]>([]);
  const [failedJobs, setFailedJobs] = useState<ExecutionJobSummary[]>([]);
  const [defects, setDefects] = useState<Defect[]>([]);
  const [traceability, setTraceability] = useState<TraceabilityMatrix | null>(null);
  const [coverage, setCoverage] = useState<RequirementCoverageReport | null>(null);
  const [trends, setTrends] = useState<Array<{ date: string; passed: number; failed: number; pass_rate: number }>>([]);
  const [loading, setLoading] = useState(true);
  const [defectDialogOpen, setDefectDialogOpen] = useState(false);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const projects = await getProjects(user!.workspace_id || "");
        if (cancelled || !projects?.length) { setLoading(false); return; }
        const pid = projects[0].id;
        if (!cancelled) setProjectId(pid);

        const [allJobs, failJobs, defList, matrix, cov, dash] = await Promise.allSettled([
          listExecutionJobs({ limit: 20 }),
          listExecutionJobs({ status: "failed", limit: 20 }),
          getDefects({ limit: 50 }),
          getTraceabilityMatrix(pid),
          getRequirementCoverage(pid),
          getDashboard(pid, 30),
        ]);

        if (cancelled) return;

        if (allJobs.status === "fulfilled") setReports(allJobs.value);
        if (failJobs.status === "fulfilled") setFailedJobs(failJobs.value);
        if (defList.status === "fulfilled") setDefects(defList.value);
        if (matrix.status === "fulfilled") setTraceability(matrix.value);
        if (cov.status === "fulfilled") setCoverage(cov.value);
        if (dash.status === "fulfilled") setTrends(dash.value.execution_trends);
      } catch {
        // non-critical — tabs show empty states
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [user]);

  async function refreshDefects() {
    try {
      const d = await getDefects({ limit: 50 });
      setDefects(d);
    } catch {
      // silently ignore
    }
  }

  return (
    <ProtectedRoute>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Insights</h1>
          <p className="text-slate-500 mt-1">
            Quality analytics, defect trends, and traceability across your workspaces.
          </p>
        </div>

        {loading && <div className="flex items-center justify-center h-40"><Loader2 className="h-8 w-8 animate-spin text-slate-400" /></div>}

        {!loading && (
          <Tabs defaultValue="reports">
            <TabsList className="flex-wrap h-auto gap-1">
              <TabsTrigger value="reports" className="flex items-center gap-1.5">
                <FileText className="h-3.5 w-3.5" /> Reports
              </TabsTrigger>
              <TabsTrigger value="failures" className="flex items-center gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5" /> Failure Analysis
              </TabsTrigger>
              <TabsTrigger value="defects" className="flex items-center gap-1.5">
                <Bug className="h-3.5 w-3.5" /> Defects
              </TabsTrigger>
              <TabsTrigger value="traceability" className="flex items-center gap-1.5">
                <Link2 className="h-3.5 w-3.5" /> Jira Traceability
              </TabsTrigger>
              <TabsTrigger value="coverage" className="flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5" /> Coverage
              </TabsTrigger>
              <TabsTrigger value="flakiness" className="flex items-center gap-1.5">
                <Shuffle className="h-3.5 w-3.5" /> Flakiness
              </TabsTrigger>
              <TabsTrigger value="trends" className="flex items-center gap-1.5">
                <BarChart3 className="h-3.5 w-3.5" /> Trends
              </TabsTrigger>
            </TabsList>

            {/* Reports */}
            <TabsContent value="reports" className="mt-4 space-y-3">
              {reports.length === 0
                ? <Card><CardContent className="py-12 text-center text-sm text-slate-500">No execution reports found.</CardContent></Card>
                : reports.map((job) => (
                <Card key={job.id} className="hover:shadow-md transition-shadow">
                  <CardContent className="pt-4 pb-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-mono text-slate-400">{job.id.slice(0, 8)}</span>
                          <Badge tone={job.status === "passed" ? "green" : job.status === "failed" ? "rose" : "slate"}>
                            {job.status}
                          </Badge>
                          {job.browser && <Badge tone="slate" className="text-[10px]">{job.browser}</Badge>}
                        </div>
                        <p className="text-sm font-semibold text-slate-900 truncate">Script: {job.script_id.slice(0, 20)}</p>
                        <p className="text-xs text-slate-500 mt-0.5">{fmt(job.started_at ?? job.created_at)} · {dur(job.duration_seconds)}</p>
                      </div>
                      <Button variant="outline" size="sm" onClick={() => toast({ title: "Export started" })}>
                        <Download className="h-3.5 w-3.5 mr-1" /> Export
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </TabsContent>

            {/* Failure Analysis */}
            <TabsContent value="failures" className="mt-4 space-y-3">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-slate-700">Failed Execution Jobs</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  {failedJobs.length === 0 ? (
                    <p className="text-sm text-slate-500 px-6 py-4">No failed jobs found.</p>
                  ) : (
                    <div className="divide-y divide-slate-100">
                      {failedJobs.map((job) => (
                        <div key={job.id} className="flex items-center gap-4 px-6 py-3">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-slate-900 truncate">Run {job.id.slice(0, 8)}</p>
                            <p className="text-xs text-slate-500">Script: {job.script_id.slice(0, 20)}</p>
                          </div>
                          <Badge tone="rose">Failed</Badge>
                          <div className="text-right shrink-0">
                            <p className="text-xs text-slate-500">{dur(job.duration_seconds)} · {fmt(job.started_at)}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* Defects */}
            <TabsContent value="defects" className="mt-4 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-500">{defects.length} defect{defects.length !== 1 ? "s" : ""}</p>
                <Button size="sm" onClick={() => setDefectDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" /> New Defect
                </Button>
              </div>
              <Card>
                <CardContent className="p-0">
                  {defects.length === 0 ? (
                    <p className="text-sm text-slate-500 px-6 py-4">No defects found.</p>
                  ) : (
                    <div className="divide-y divide-slate-100">
                      {defects.map((d) => (
                        <div key={d.id} className="flex items-center gap-4 px-6 py-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                              <span className="text-xs font-mono text-slate-400">{d.id.slice(0, 8)}</span>
                              <Badge tone={SEV_TONE[d.severity] ?? "slate"}>{d.severity}</Badge>
                            </div>
                            <p className="text-sm font-medium text-slate-900 truncate">{d.title}</p>
                          </div>
                          <div className="flex items-center gap-3 shrink-0">
                            <span className="text-xs text-slate-400">{fmt(d.created_at)}</span>
                            <Badge tone={d.status === "open" ? "rose" : d.status === "in_progress" ? "amber" : "green"}>
                              {d.status}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
              <NewDefectDialog
                open={defectDialogOpen}
                onClose={() => setDefectDialogOpen(false)}
                projectId={projectId}
                onCreated={refreshDefects}
              />
            </TabsContent>

            {/* Traceability */}
            <TabsContent value="traceability" className="mt-4">
              {!traceability
                ? <Card><CardContent className="py-12 text-center"><Link2 className="h-10 w-10 mx-auto mb-3 text-slate-300" /><p className="text-sm text-slate-500">No traceability data. Connect Jira in Administration.</p></CardContent></Card>
                : (
                <div className="space-y-4">
                  <div className="flex gap-4 text-sm">
                    <span className="text-slate-500">Total Requirements: <strong>{traceability.total_requirements}</strong></span>
                    <span className="text-slate-500">Covered: <strong>{traceability.covered_requirements}</strong></span>
                    <span className="text-slate-500">Links: <strong>{traceability.total_links}</strong></span>
                  </div>
                  <Card>
                    <CardContent className="p-0">
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                          <thead className="border-b border-slate-100">
                            <tr className="text-left text-slate-500">
                              <th className="px-4 py-3 font-medium">Requirement</th>
                              <th className="px-4 py-3 font-medium">Test Suite</th>
                              <th className="px-4 py-3 font-medium">Test Case</th>
                              <th className="px-4 py-3 font-medium">Last Execution</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-50">
                            {traceability.links.slice(0, 30).map((link, i) => (
                              <tr key={i} className="hover:bg-slate-50">
                                <td className="px-4 py-2.5 text-slate-900 font-medium truncate max-w-[200px]">{link.requirement_title}</td>
                                <td className="px-4 py-2.5 text-slate-600 truncate max-w-[160px]">{link.test_suite_name ?? "—"}</td>
                                <td className="px-4 py-2.5 text-slate-600 truncate max-w-[160px]">{link.test_case_title ?? "—"}</td>
                                <td className="px-4 py-2.5">
                                  {link.last_execution_status ? (
                                    <Badge tone={link.last_execution_status === "passed" ? "green" : "rose"}>
                                      {link.last_execution_status}
                                    </Badge>
                                  ) : "—"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}
            </TabsContent>

            {/* Coverage */}
            <TabsContent value="coverage" className="mt-4 space-y-3">
              {!coverage
                ? <Card><CardContent className="py-8 text-center text-sm text-slate-500">No coverage data available.</CardContent></Card>
                : (
                <>
                  <div className="flex gap-6 text-sm">
                    <span className="text-slate-500">Requirements: <strong>{coverage.total_requirements}</strong></span>
                    <span className="text-slate-500">Covered: <strong>{coverage.covered_requirements}</strong></span>
                    <span className="font-semibold text-slate-900">{Math.round(coverage.coverage_percent)}% coverage</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
                    <div className="bg-green-400 h-full rounded-full transition-all" style={{ width: `${coverage.coverage_percent}%` }} />
                  </div>
                  <Card>
                    <CardContent className="p-0">
                      <div className="divide-y divide-slate-100">
                        {coverage.items.map((item) => (
                          <div key={item.requirement_id} className="flex items-center gap-4 px-6 py-3">
                            <div className="flex-1 min-w-0">
                              <p className="text-sm text-slate-900 truncate">{item.requirement_title ?? item.requirement_id}</p>
                            </div>
                            <div className="flex items-center gap-3 shrink-0">
                              {item.covered ? (
                                <Badge tone="green"><CheckCircle2 className="h-3 w-3 mr-1" />{item.test_case_count} tests</Badge>
                              ) : (
                                <Badge tone="rose">Not covered</Badge>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </>
              )}
            </TabsContent>

            {/* Flakiness */}
            <TabsContent value="flakiness" className="mt-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-slate-700">Flaky Test Detection</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="py-8 text-center">
                    <Shuffle className="h-10 w-10 mx-auto mb-3 text-slate-300" />
                    <p className="text-sm text-slate-500">No flakiness data yet.</p>
                    <p className="text-xs text-slate-400 mt-1">Flakiness detection requires at least 10 execution runs per script.</p>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Trends */}
            <TabsContent value="trends" className="mt-4 space-y-3">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-slate-700">Execution Trends (Last 30 Days)</CardTitle>
                </CardHeader>
                <CardContent>
                  {trends.length === 0 ? (
                    <p className="text-sm text-slate-500 py-4 text-center">No trend data available yet.</p>
                  ) : (
                    <div className="space-y-3">
                      {trends.map((t) => (
                        <div key={t.date} className="flex items-center gap-4">
                          <span className="text-xs text-slate-500 w-24 shrink-0">{t.date}</span>
                          <div className="flex-1 bg-slate-100 rounded-full h-4 overflow-hidden">
                            <div
                              className="bg-green-400 h-full rounded-full transition-all"
                              style={{ width: `${Math.min(t.pass_rate, 100)}%` }}
                            />
                          </div>
                          <div className="flex items-center gap-1 w-16 justify-end">
                            {t.pass_rate >= 80 ? (
                              <TrendingUp className="h-3 w-3 text-green-500" />
                            ) : (
                              <TrendingDown className="h-3 w-3 text-rose-500" />
                            )}
                            <span className="text-xs font-semibold text-slate-700">{Math.round(t.pass_rate)}%</span>
                          </div>
                          <span className="text-xs text-slate-400 w-16 text-right">
                            {t.passed}P / {t.failed}F
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </ProtectedRoute>
  );
}
