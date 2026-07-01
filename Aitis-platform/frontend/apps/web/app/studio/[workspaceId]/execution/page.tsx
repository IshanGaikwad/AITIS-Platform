"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Play, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { getTestSuites, createExecution, getWorkspaceEnvironments } from "@/lib/api";
import type { TestSuite, Environment } from "@/lib/types";
import { useAuth } from "@/lib/auth";

import { cn } from "@/lib/utils";

const EXECUTION_TYPE_OPTIONS = ["manual", "automated"] as const;

const selectClass =
  "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400";

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium text-slate-700">{label}</label>
      {children}
    </div>
  );
}

export default function ExecutionPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = params.workspaceId as string;
  const { toast } = useToast();

  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [suitesLoading, setSuitesLoading] = useState(true);
  const [suitesError, setSuitesError] = useState<string | null>(null);

  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [environmentsLoading, setEnvironmentsLoading] = useState(true);

  const [selectedSuiteId, setSelectedSuiteId] = useState("");
  const [environmentId, setEnvironmentId] = useState("");
  const [executionType, setExecutionType] = useState<string>("manual");
  const [notes, setNotes] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const fetchSuites = useCallback(async () => {
    setSuitesLoading(true);
    setSuitesError(null);
    try {
      const data = await getTestSuites(workspaceId);
      setSuites(data);
      if (data.length > 0) setSelectedSuiteId(data[0].id);
    } catch {
      setSuitesError("Failed to load test suites.");
    } finally {
      setSuitesLoading(false);
    }
  }, [workspaceId]);

  const fetchEnvironments = useCallback(async () => {
    setEnvironmentsLoading(true);
    try {
      const data = await getWorkspaceEnvironments(workspaceId);
      setEnvironments(data);
      if (data.length > 0) setEnvironmentId(data[0].id);
    } catch {
      // non-fatal — manual runs don't require a target
    } finally {
      setEnvironmentsLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    fetchSuites();
    fetchEnvironments();
  }, [fetchSuites, fetchEnvironments]);

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!selectedSuiteId) {
      setValidationError("Please select a test suite before running.");
      return;
    }
    if (executionType === "automated" && !environmentId) {
      setValidationError("Select a target environment for an automated run.");
      return;
    }

    setSubmitting(true);
    try {
      const selectedEnv = environments.find((e) => e.id === environmentId);
      const execution = await createExecution({
        test_suite_id: selectedSuiteId,
        environment: selectedEnv?.name,
        environment_id: environmentId || undefined,
        execution_type: executionType,
        notes: notes.trim() || undefined,
      });
      const summary = execution.summary;
      const description =
        executionType === "automated" && summary
          ? `${summary.passed ?? 0} passed, ${summary.failed ?? 0} failed, ${summary.errors ?? 0} errors` +
            (summary.target_url ? ` against ${summary.target_url}` : "")
          : `Run ${execution.id.slice(0, 8)} is now queued.`;
      toast({
        title: executionType === "automated" ? "Automated run completed" : "Execution started",
        description,
        variant: executionType === "automated" && (summary?.failed || summary?.errors) ? "destructive" : "success",
      });
      router.push("/runs");
    } catch (err) {
      toast({
        title: "Failed to start execution",
        description: err instanceof Error ? err.message : "An error occurred.",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-5">
      <h2 className="text-lg font-semibold text-slate-900">Execution Setup</h2>

      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-sm font-semibold text-slate-700">Run Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5 pt-0">
          {suitesLoading ? (
            <div className="space-y-3">
              <div className="h-9 animate-pulse rounded-lg bg-slate-100" />
              <div className="h-9 animate-pulse rounded-lg bg-slate-100" />
            </div>
          ) : suitesError ? (
            <div className="flex items-center gap-2 rounded-lg border border-rose-100 bg-rose-50 p-3">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-500" />
              <p className="text-sm text-rose-700">{suitesError}</p>
              <Button variant="outline" size="sm" className="ml-auto" onClick={fetchSuites}>
                Retry
              </Button>
            </div>
          ) : (
            <form onSubmit={handleRun} className="space-y-5">
              {/* Test Suite */}
              <FormField label="Test Suite">
                {suites.length === 0 ? (
                  <p className="text-sm text-slate-500">
                    No suites available.{" "}
                    <button
                      type="button"
                      onClick={() => router.push(`/studio/${workspaceId}/test-suites`)}
                      className="text-blue-600 underline"
                    >
                      Create one first.
                    </button>
                  </p>
                ) : (
                  <select
                    value={selectedSuiteId}
                    onChange={(e) => {
                      setSelectedSuiteId(e.target.value);
                      setValidationError(null);
                    }}
                    className={cn(selectClass, validationError ? "border-rose-400" : "")}
                  >
                    <option value="" disabled>Select a suite…</option>
                    {suites.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                )}
                {validationError && (
                  <p className="mt-1 text-xs text-rose-600">{validationError}</p>
                )}
              </FormField>

              {/* Target Environment + Execution Type */}
              <div className="grid grid-cols-2 gap-4">
                <FormField label="Target Environment">
                  {environmentsLoading ? (
                    <div className="h-9 animate-pulse rounded-lg bg-slate-100" />
                  ) : environments.length === 0 ? (
                    <p className="text-xs text-slate-500">
                      No target configured.{" "}
                      <Link
                        href={`/studio/${workspaceId}/target`}
                        className="text-blue-600 underline"
                      >
                        Set one up in Target.
                      </Link>
                    </p>
                  ) : (
                    <select
                      value={environmentId}
                      onChange={(e) => setEnvironmentId(e.target.value)}
                      className={selectClass}
                    >
                      {environments.map((env) => (
                        <option key={env.id} value={env.id}>
                          {env.name} ({env.environment_type}) — {env.base_url ?? "no URL"}
                        </option>
                      ))}
                    </select>
                  )}
                </FormField>
                <FormField label="Execution Type">
                  <select
                    value={executionType}
                    onChange={(e) => setExecutionType(e.target.value)}
                    className={selectClass}
                  >
                    {EXECUTION_TYPE_OPTIONS.map((o) => (
                      <option key={o} value={o}>{o.charAt(0).toUpperCase() + o.slice(1)}</option>
                    ))}
                  </select>
                </FormField>
              </div>
              {executionType === "automated" && (
                <p className="-mt-2 text-xs text-slate-500">
                  Automated runs execute against the target environment's URL above and report
                  real reachability per test case.
                </p>
              )}

              {/* Notes */}
              <FormField label="Notes (optional)">
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  placeholder="Any notes about this run..."
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 resize-none"
                />
              </FormField>

              {/* Actions */}
              <div className="flex gap-3 border-t border-slate-100 pt-2">
                <Button
                  type="submit"
                  className="flex-1"
                  disabled={submitting || suitesLoading || suites.length === 0}
                >
                  <Play className="h-4 w-4" />
                  {submitting ? "Starting..." : "Run Now"}
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
