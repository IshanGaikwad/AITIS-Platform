"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getExecutionResult,
  getExecutionStepResults,
  getSuiteSummary,
} from "@/lib/api";
import type {
  ExecutionResultDetail,
  ExecutionStepResult,
  SuiteSummary,
  ArtifactLink,
} from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  CheckCircle2,
  XCircle,
  SkipForward,
  FileText,
  Image,
  Download,
  ChevronDown,
  ChevronRight,
  Loader2,
  BarChart3,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Step status icon ── */
function stepIcon(status: string) {
  switch (status) {
    case "passed":
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case "failed":
      return <XCircle className="h-4 w-4 text-rose-500" />;
    case "skipped":
      return <SkipForward className="h-4 w-4 text-amber-500" />;
    default:
      return <FileText className="h-4 w-4 text-muted-foreground" />;
  }
}

function stepTone(status: string): "green" | "rose" | "amber" | "slate" | "blue" | "purple" {
  switch (status) {
    case "passed":
      return "green";
    case "failed":
      return "rose";
    case "skipped":
      return "amber";
    default:
      return "slate";
  }
}

interface ResultsViewerProps {
  jobId: string | null;
}

export function ResultsViewer({ jobId }: ResultsViewerProps) {
  const [result, setResult] = useState<ExecutionResultDetail | null>(null);
  const [steps, setSteps] = useState<ExecutionStepResult[]>([]);
  const [summary, setSummary] = useState<SuiteSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedStep, setExpandedStep] = useState<string | null>(null);

  /* ── Fetch results ── */
  const fetchResults = useCallback(async () => {
    if (!jobId) {
      setResult(null);
      setSteps([]);
      setSummary(null);
      return;
    }
    try {
      setLoading(true);
      const [r, s, sum] = await Promise.all([
        getExecutionResult(jobId).catch(() => null),
        getExecutionStepResults(jobId).catch(() => []),
        getSuiteSummary(jobId).catch(() => null),
      ]);
      setResult(r);
      setSteps(s);
      setSummary(sum);
    } catch (err) {
      console.error("Failed to load results:", err);
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  if (!jobId) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
        Run an execution to view results
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header with summary */}
      <div className="border-b px-3 py-2">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold">Results</h3>
          {result && (
            <Badge tone={stepTone(result.status)} className="text-[10px] px-1.5 py-0 ml-auto">
              {result.status}
            </Badge>
          )}
        </div>

        {/* Suite summary bar */}
        {summary && (
          <div className="mt-2 flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1 text-green-600">
              <CheckCircle2 className="h-3 w-3" /> {summary.passed} passed
            </span>
            <span className="flex items-center gap-1 text-rose-600">
              <XCircle className="h-3 w-3" /> {summary.failed} failed
            </span>
            <span className="flex items-center gap-1 text-amber-600">
              <SkipForward className="h-3 w-3" /> {summary.skipped} skipped
            </span>
            <span className="text-muted-foreground">
              {summary.total_tests} total
            </span>
            {/* Progress bar */}
            <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
              {summary.total_tests > 0 && (
                <div className="flex h-full">
                  <div
                    className="bg-green-500"
                    style={{ width: `${(summary.passed / summary.total_tests) * 100}%` }}
                  />
                  <div
                    className="bg-rose-500"
                    style={{ width: `${(summary.failed / summary.total_tests) * 100}%` }}
                  />
                  <div
                    className="bg-amber-400"
                    style={{ width: `${(summary.skipped / summary.total_tests) * 100}%` }}
                  />
                </div>
              )}
            </div>
            {summary.total_duration_seconds != null && (
              <span className="text-muted-foreground whitespace-nowrap">
                {summary.total_duration_seconds.toFixed(1)}s
              </span>
            )}
          </div>
        )}
      </div>

      {/* Result metadata */}
      {result && (
        <div className="border-b px-3 py-2 space-y-1 text-xs text-muted-foreground">
          {result.created_at && (
            <p>Started: {new Date(result.created_at).toLocaleString()}</p>
          )}
          {result.duration_seconds != null && (
            <p>Duration: {result.duration_seconds.toFixed(1)}s</p>
          )}
          {result.error_message && (
            <p className="text-rose-600 break-all">{result.error_message}</p>
          )}
        </div>
      )}

      {/* Step results */}
      <div className="flex-1 overflow-y-auto">
        {steps.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
            No step results available
          </div>
        ) : (
          <ul className="divide-y">
            {steps.map((step) => (
              <li key={step.id}>
                <div
                  className="flex cursor-pointer items-center gap-2 px-3 py-2 hover:bg-accent"
                  onClick={() =>
                    setExpandedStep(expandedStep === step.id ? null : step.id)
                  }
                >
                  {expandedStep === step.id ? (
                    <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground" />
                  )}
                  {stepIcon(step.status)}
                  <span className="flex-1 text-sm truncate">{step.step_name}</span>
                  <Badge tone={stepTone(step.status)} className="text-[10px] px-1 py-0">
                    {step.status}
                  </Badge>
                  {step.duration_seconds != null && (
                    <span className="text-[10px] text-muted-foreground">
                      {(step.duration_seconds * 1000).toFixed(0)}ms
                    </span>
                  )}
                </div>

                {/* Expanded step detail */}
                {expandedStep === step.id && (
                  <div className="border-t bg-muted/20 px-3 py-2 space-y-2">
                    {step.error_message && (
                      <div className="rounded bg-rose-50 border border-rose-200 px-2 py-1.5 text-xs text-rose-700 font-mono break-all">
                        {step.error_message}
                      </div>
                    )}
                    {step.screenshot_url && (
                      <div>
                        <a
                          href={step.screenshot_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
                        >
                          <Image className="h-3 w-3" /> View screenshot
                        </a>
                      </div>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

/* ── Artifact row ── */
function ArtifactRow({ artifact }: { artifact: ArtifactLink }) {
  const icon = artifact.content_type?.startsWith("image/") ? (
    <Image className="h-3 w-3" />
  ) : (
    <FileText className="h-3 w-3" />
  );

  return (
    <span className="flex items-center gap-1.5 text-xs text-blue-600">
      {icon}
      <span className="truncate">{artifact.name || `Artifact`}</span>
      {artifact.size_bytes != null && (
        <span className="text-muted-foreground">
          ({(artifact.size_bytes / 1024).toFixed(1)} KB)
        </span>
      )}
    </span>
  );
}
