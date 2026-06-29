"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Play, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { getTestSuites, createExecution } from "@/lib/api";
import type { TestSuite } from "@/lib/types";
import { useAuth } from "@/lib/auth";

import { cn } from "@/lib/utils";

const ENVIRONMENT_OPTIONS = ["dev", "qa", "uat", "staging", "production"] as const;
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
  const projectId = params.workspaceId as string;
  const { toast } = useToast();

  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [suitesLoading, setSuitesLoading] = useState(true);
  const [suitesError, setSuitesError] = useState<string | null>(null);

  const [selectedSuiteId, setSelectedSuiteId] = useState("");
  const [environment, setEnvironment] = useState<string>("qa");
  const [executionType, setExecutionType] = useState<string>("manual");
  const [notes, setNotes] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const fetchSuites = useCallback(async () => {
    setSuitesLoading(true);
    setSuitesError(null);
    try {
      const data = await getTestSuites(projectId);
      setSuites(data);
      if (data.length > 0) setSelectedSuiteId(data[0].id);
    } catch {
      setSuitesError("Failed to load test suites.");
    } finally {
      setSuitesLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchSuites();
  }, [fetchSuites]);

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (!selectedSuiteId) {
      setValidationError("Please select a test suite before running.");
      return;
    }

    setSubmitting(true);
    try {
      const execution = await createExecution({
        test_suite_id: selectedSuiteId,
        environment,
        execution_type: executionType,
        notes: notes.trim() || undefined,
      });
      toast({
        title: "Execution started",
        description: `Run ${execution.id.slice(0, 8)} is now queued.`,
        variant: "success",
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
                      onClick={() => router.push(`/studio/${projectId}/test-suites`)}
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

              {/* Environment + Execution Type */}
              <div className="grid grid-cols-2 gap-4">
                <FormField label="Environment">
                  <select
                    value={environment}
                    onChange={(e) => setEnvironment(e.target.value)}
                    className={selectClass}
                  >
                    {ENVIRONMENT_OPTIONS.map((o) => (
                      <option key={o} value={o}>{o.toUpperCase()}</option>
                    ))}
                  </select>
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
