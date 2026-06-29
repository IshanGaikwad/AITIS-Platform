"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Play,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  ChevronRight,
  ChevronDown,
  Save,
  FileText,
  Plus,
  ArrowLeft,
  SkipForward,
  Ban,
  Camera,
  MessageSquare,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  getExecution,
  recordStepResult,
  completeExecution,
  createExecution,
  getCaseExecutions,
  createCaseExecutions,
} from "@/lib/api";
import type { TestExecution, TestCaseExecution, StepExecution } from "@/lib/types";
import { cn } from "@/lib/utils";
import Link from "next/link";

/* ── Status helpers ──────────────────────────────────────────────── */

const STEP_STATUSES = ["pending", "passed", "failed", "blocked", "skipped"] as const;
type StepStatus = (typeof STEP_STATUSES)[number];

const STATUS_LABEL: Record<string, string> = {
  pending: "Pending",
  passed: "Passed",
  failed: "Failed",
  blocked: "Blocked",
  skipped: "Skipped",
  in_progress: "In Progress",
  completed: "Completed",
};

const STATUS_TONE: Record<string, "green" | "rose" | "amber" | "slate" | "blue" | "purple"> = {
  pending: "slate",
  passed: "green",
  failed: "rose",
  blocked: "amber",
  skipped: "slate",
  in_progress: "blue",
  completed: "purple",
};

/* ── Main Page ───────────────────────────────────────────────────── */

export default function ManualExecutionPage() {
  const searchParams = useSearchParams();
  const executionIdParam = searchParams.get("executionId") ?? undefined;
  const suiteIdParam = searchParams.get("suiteId") ?? undefined;

  const [execution, setExecution] = useState<TestExecution | null>(null);
  const [caseExecutions, setCaseExecutions] = useState<TestCaseExecution[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /* ── Load case executions ──────────────────────────────────────── */

  const loadCaseExecutions = useCallback(async (execId: string) => {
    try {
      const cases = await getCaseExecutions(execId);
      setCaseExecutions(cases);
      // Auto-select first case if none selected
      if (cases.length > 0 && !selectedCaseId) {
        setSelectedCaseId(cases[0].id);
      }
    } catch (err) {
      console.error("Failed to load case executions:", err);
    }
  }, [selectedCaseId]);

  /* ── Initial load ──────────────────────────────────────────────── */

  useEffect(() => {
    if (executionIdParam) {
      loadExistingExecution(executionIdParam);
    } else if (suiteIdParam) {
      startNewExecution();
    } else {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [executionIdParam, suiteIdParam]);

  async function loadExistingExecution(id: string) {
    setLoading(true);
    setError(null);
    try {
      const data = await getExecution(id);
      setExecution(data);
      await loadCaseExecutions(id);
    } catch (err) {
      console.error("Failed to load execution:", err);
      setError("Failed to load execution session.");
    } finally {
      setLoading(false);
    }
  }

  async function startNewExecution() {
    setLoading(true);
    setError(null);
    try {
      const newExec = await createExecution({
        test_suite_id: suiteIdParam!,
        execution_type: "manual",
      });
      setExecution(newExec);
      // Create case + step execution records
      const cases = await createCaseExecutions(newExec.id);
      setCaseExecutions(cases);
      if (cases.length > 0) {
        setSelectedCaseId(cases[0].id);
      }
    } catch (err) {
      console.error("Failed to start execution:", err);
      setError("Failed to start execution session.");
    } finally {
      setLoading(false);
    }
  }

  /* ── Step update handler ───────────────────────────────────────── */

  async function handleStepUpdate(stepExecutionId: string, updates: Partial<StepExecution>) {
    setSaving(true);
    try {
      const updated = await recordStepResult(stepExecutionId, updates);
      // Update local state
      setCaseExecutions(prev =>
        prev.map(ce => {
          if (!ce.step_executions) return ce;
          return {
            ...ce,
            step_executions: ce.step_executions.map(se =>
              se.id === stepExecutionId ? { ...se, ...updated } : se
            ),
          };
        })
      );
    } catch (err) {
      console.error("Failed to update step:", err);
    } finally {
      setSaving(false);
    }
  }

  /* ── Complete session ──────────────────────────────────────────── */

  async function handleComplete() {
    if (!execution) return;
    setSaving(true);
    try {
      const completed = await completeExecution(execution.id);
      setExecution(completed);
    } catch (err) {
      console.error("Failed to complete execution:", err);
    } finally {
      setSaving(false);
    }
  }

  /* ── Derived state ─────────────────────────────────────────────── */

  const selectedCase = caseExecutions.find(ce => ce.id === selectedCaseId) ?? null;
  const steps = selectedCase?.step_executions ?? [];
  const sortedSteps = [...steps].sort((a, b) => (a.step_order ?? 0) - (b.step_order ?? 0));

  const isCompleted = execution?.status === "completed";

  /* ── Render ────────────────────────────────────────────────────── */

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-4">
          <AlertCircle className="h-12 w-12 text-rose-400 mx-auto" />
          <p className="text-slate-600">{error}</p>
          <Button variant="outline" asChild>
            <Link href="/test-suites">Back to Test Suites</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* Left Sidebar: Test Case List */}
      <div className="w-80 border-r bg-white flex flex-col">
        <div className="p-4 border-b flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
              <Link href="/test-suites">
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
            <h2 className="font-semibold text-sm">Execution Session</h2>
          </div>
          <Badge tone={STATUS_TONE[execution?.status ?? "pending"] ?? "slate"} className="text-[10px]">
            {STATUS_LABEL[execution?.status ?? "pending"] ?? execution?.status}
          </Badge>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {caseExecutions.length === 0 ? (
            <div className="text-center py-10 px-4">
              <FileText className="h-8 w-8 text-slate-300 mx-auto mb-2" />
              <p className="text-xs text-slate-500">No test cases in this session.</p>
            </div>
          ) : (
            caseExecutions.map(ce => (
              <div
                key={ce.id}
                onClick={() => setSelectedCaseId(ce.id)}
                className={cn(
                  "p-3 rounded-lg cursor-pointer transition-all border text-sm",
                  selectedCaseId === ce.id
                    ? "bg-blue-50 border-blue-200 text-blue-700 ring-1 ring-blue-200"
                    : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium truncate">
                    {ce.test_case_title ?? ce.test_case_id.slice(0, 8)}
                  </span>
                  <Badge tone={STATUS_TONE[ce.status] ?? "slate"} className="text-[10px] px-1 py-0">
                    {STATUS_LABEL[ce.status] ?? ce.status}
                  </Badge>
                </div>
                {/* Mini progress bar */}
                {ce.step_executions && ce.step_executions.length > 0 && (
                  <div className="flex gap-0.5 mt-1.5">
                    {ce.step_executions.map(se => (
                      <div
                        key={se.id}
                        className={cn(
                          "h-1.5 flex-1 rounded-full",
                          se.status === "passed" && "bg-green-400",
                          se.status === "failed" && "bg-rose-400",
                          se.status === "blocked" && "bg-amber-400",
                          se.status === "skipped" && "bg-slate-300",
                          se.status === "pending" && "bg-slate-100"
                        )}
                      />
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        <div className="p-4 border-t bg-slate-50">
          <Button
            className="w-full"
            onClick={handleComplete}
            disabled={isCompleted || saving}
          >
            {saving ? "Saving..." : isCompleted ? "Session Completed" : "Complete Session"}
          </Button>
        </div>
      </div>

      {/* Main Content: Step Execution */}
      <div className="flex-1 overflow-y-auto p-8">
        {!selectedCase ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400">
            <Play className="h-12 w-12 mb-4 opacity-20" />
            <p>Select a test case from the sidebar to begin execution</p>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-slate-900">
                  {selectedCase.test_case_title ?? "Test Case"}
                </h1>
                <p className="text-slate-500">
                  Record actual results and evidence for each step.
                </p>
              </div>
              <Badge tone={STATUS_TONE[selectedCase.status] ?? "slate"}>
                {STATUS_LABEL[selectedCase.status] ?? selectedCase.status}
              </Badge>
            </div>

            {/* Steps */}
            <Card>
              <CardHeader className="border-b bg-slate-50/50">
                <CardTitle className="text-lg">Test Steps</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {sortedSteps.length === 0 ? (
                  <div className="p-8 text-center text-slate-400">
                    <FileText className="h-8 w-8 mx-auto mb-2 opacity-30" />
                    <p className="text-sm">No steps defined for this test case.</p>
                  </div>
                ) : (
                  <div className="divide-y">
                    {sortedSteps.map((se, idx) => (
                      <StepRow
                        key={se.id}
                        stepExecution={se}
                        stepNumber={se.step_order ?? idx + 1}
                        disabled={isCompleted}
                        onUpdate={(updates) => handleStepUpdate(se.id, updates)}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── StepRow Component ───────────────────────────────────────────── */

function StepRow({
  stepExecution,
  stepNumber,
  disabled,
  onUpdate,
}: {
  stepExecution: StepExecution;
  stepNumber: number;
  disabled: boolean;
  onUpdate: (updates: Partial<StepExecution>) => void;
}) {
  const [actualResult, setActualResult] = useState(stepExecution.actual_result ?? "");
  const [comment, setComment] = useState(stepExecution.comment ?? "");
  const [screenshotUrl, setScreenshotUrl] = useState(stepExecution.screenshot_url ?? "");

  // Sync local state when stepExecution changes from server
  useEffect(() => {
    setActualResult(stepExecution.actual_result ?? "");
    setComment(stepExecution.comment ?? "");
    setScreenshotUrl(stepExecution.screenshot_url ?? "");
  }, [stepExecution.actual_result, stepExecution.comment, stepExecution.screenshot_url]);

  const statusIcon = {
    pending: <Clock className="h-3.5 w-3.5 text-slate-400" />,
    passed: <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />,
    failed: <XCircle className="h-3.5 w-3.5 text-rose-500" />,
    blocked: <Ban className="h-3.5 w-3.5 text-amber-500" />,
    skipped: <SkipForward className="h-3.5 w-3.5 text-slate-400" />,
  };

  return (
    <div className="p-4 flex gap-6 hover:bg-slate-50/50 transition-colors">
      {/* Step number + connector */}
      <div className="flex flex-col items-center gap-1">
        <div
          className={cn(
            "h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold border-2",
            stepExecution.status === "passed" && "bg-green-100 border-green-300 text-green-700",
            stepExecution.status === "failed" && "bg-rose-100 border-rose-300 text-rose-700",
            stepExecution.status === "blocked" && "bg-amber-100 border-amber-300 text-amber-700",
            stepExecution.status === "skipped" && "bg-slate-100 border-slate-300 text-slate-500",
            stepExecution.status === "pending" && "bg-slate-50 border-slate-200 text-slate-400"
          )}
        >
          {stepNumber}
        </div>
        <div className="w-px flex-1 bg-slate-200" />
      </div>

      {/* Step content */}
      <div className="flex-1 space-y-4 pb-2">
        {/* Action & Expected Result */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1">
            <Label className="text-xs text-slate-500">Action</Label>
            <p className="text-sm text-slate-700 bg-slate-100 p-2 rounded border">
              {stepExecution.step_action ?? "—"}
            </p>
          </div>
          <div className="space-y-1">
            <Label className="text-xs text-slate-500">Expected Result</Label>
            <p className="text-sm text-slate-700 bg-slate-100 p-2 rounded border">
              {stepExecution.step_expected_result ?? "—"}
            </p>
          </div>
        </div>

        {/* Actual Result */}
        <div className="space-y-1">
          <Label className="text-xs text-slate-500">Actual Result</Label>
          <Textarea
            placeholder="What actually happened?"
            className="text-sm min-h-[60px]"
            value={actualResult}
            onChange={(e) => setActualResult(e.target.value)}
            onBlur={() => {
              if (actualResult !== (stepExecution.actual_result ?? "")) {
                onUpdate({ actual_result: actualResult || undefined });
              }
            }}
            disabled={disabled}
          />
        </div>

        {/* Status buttons + evidence */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Label className="text-xs text-slate-500 mr-1">Status:</Label>
            <div className="flex gap-1">
              <StatusButton
                label="Pass"
                active={stepExecution.status === "passed"}
                onClick={() => onUpdate({ status: "passed" })}
                color="green"
                icon={<CheckCircle2 className="h-3 w-3" />}
                disabled={disabled}
              />
              <StatusButton
                label="Fail"
                active={stepExecution.status === "failed"}
                onClick={() => onUpdate({ status: "failed" })}
                color="rose"
                icon={<XCircle className="h-3 w-3" />}
                disabled={disabled}
              />
              <StatusButton
                label="Block"
                active={stepExecution.status === "blocked"}
                onClick={() => onUpdate({ status: "blocked" })}
                color="amber"
                icon={<Ban className="h-3 w-3" />}
                disabled={disabled}
              />
              <StatusButton
                label="Skip"
                active={stepExecution.status === "skipped"}
                onClick={() => onUpdate({ status: "skipped" })}
                color="slate"
                icon={<SkipForward className="h-3 w-3" />}
                disabled={disabled}
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Camera className="h-3.5 w-3.5 text-slate-400" />
            <Input
              placeholder="Screenshot URL"
              className="h-8 text-xs w-48"
              value={screenshotUrl}
              onChange={(e) => setScreenshotUrl(e.target.value)}
              onBlur={() => {
                if (screenshotUrl !== (stepExecution.screenshot_url ?? "")) {
                  onUpdate({ screenshot_url: screenshotUrl || undefined });
                }
              }}
              disabled={disabled}
            />
          </div>
        </div>

        {/* Comment */}
        <div className="space-y-1">
          <Label className="text-xs text-slate-500 flex items-center gap-1">
            <MessageSquare className="h-3 w-3" /> Comment
          </Label>
          <Input
            placeholder="Optional comment or note"
            className="h-8 text-xs"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            onBlur={() => {
              if (comment !== (stepExecution.comment ?? "")) {
                onUpdate({ comment: comment || undefined });
              }
            }}
            disabled={disabled}
          />
        </div>
      </div>
    </div>
  );
}

/* ── StatusButton Component ──────────────────────────────────────── */

function StatusButton({
  label,
  active,
  onClick,
  color,
  icon,
  disabled,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  color: "green" | "rose" | "amber" | "slate";
  icon: React.ReactNode;
  disabled?: boolean;
}) {
  const colorClasses = {
    green: active
      ? "bg-green-100 text-green-700 border-green-300"
      : "hover:bg-green-50 hover:text-green-600 border-slate-200 text-slate-500",
    rose: active
      ? "bg-rose-100 text-rose-700 border-rose-300"
      : "hover:bg-rose-50 hover:text-rose-600 border-slate-200 text-slate-500",
    amber: active
      ? "bg-amber-100 text-amber-700 border-amber-300"
      : "hover:bg-amber-50 hover:text-amber-600 border-slate-200 text-slate-500",
    slate: active
      ? "bg-slate-100 text-slate-700 border-slate-300"
      : "hover:bg-slate-50 hover:text-slate-600 border-slate-200 text-slate-500",
  };

  return (
    <Button
      variant="outline"
      size="sm"
      className={cn("h-7 px-2 text-[10px] gap-1 transition-colors", colorClasses[color])}
      onClick={onClick}
      disabled={disabled}
    >
      {icon}
      {label}
    </Button>
  );
}
