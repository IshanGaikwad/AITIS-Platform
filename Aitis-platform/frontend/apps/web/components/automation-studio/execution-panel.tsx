"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  submitExecutionJob,
  listExecutionJobs,
  getExecutionJob,
  cancelExecutionJob,
  createExecutionStatusSocket,
} from "@/lib/api";
import type {
  ExecutionJobCreate,
  ExecutionJobSummary,
  ExecutionJob,
  ExecutionStatusEvent,
} from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Play,
  Square,
  Loader2,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Activity,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Job status helpers ── */
function statusIcon(status: string) {
  switch (status) {
    case "pending":
      return <Clock className="h-3.5 w-3.5 text-amber-500" />;
    case "running":
      return <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-500" />;
    case "completed":
      return <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />;
    case "failed":
      return <XCircle className="h-3.5 w-3.5 text-rose-500" />;
    case "cancelled":
      return <AlertTriangle className="h-3.5 w-3.5 text-muted-foreground" />;
    default:
      return <Clock className="h-3.5 w-3.5 text-muted-foreground" />;
  }
}

function statusTone(status: string): "green" | "amber" | "rose" | "slate" | "blue" | "purple" {
  switch (status) {
    case "pending":
      return "amber";
    case "running":
      return "blue";
    case "completed":
      return "green";
    case "failed":
      return "rose";
    case "cancelled":
      return "slate";
    default:
      return "slate";
  }
}

interface ExecutionPanelProps {
  scriptId: string | null;
  onJobCompleted?: (jobId: string) => void;
}

export function ExecutionPanel({ scriptId, onJobCompleted }: ExecutionPanelProps) {
  /* ── Form state ── */
  const [browser, setBrowser] = useState("chromium");
  const [headless, setHeadless] = useState(true);
  const [timeout, setTimeout_] = useState(60);
  const [baseUrl, setBaseUrl] = useState("");
  const [environmentId, setEnvironmentId] = useState("");
  const [submitting, setSubmitting] = useState(false);

  /* ── Jobs list ── */
  const [jobs, setJobs] = useState<ExecutionJobSummary[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);

  /* ── Live status ── */
  const [liveStatus, setLiveStatus] = useState<Record<string, ExecutionStatusEvent>>({});
  const wsRef = useRef<WebSocket | null>(null);

  /* ── Selected job detail ── */
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<ExecutionJob | null>(null);

  /* ── Fetch jobs ── */
  const fetchJobs = useCallback(async () => {
    try {
      setJobsLoading(true);
      const params: Record<string, string> = {};
      if (scriptId) params.script_id = scriptId;
      const data = await listExecutionJobs(params);
      setJobs(data);
    } catch (err) {
      console.error("Failed to load jobs:", err);
    } finally {
      setJobsLoading(false);
    }
  }, [scriptId]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  /* ── WebSocket for live status ── */
  useEffect(() => {
    const ws = createExecutionStatusSocket();
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const evt: ExecutionStatusEvent = JSON.parse(event.data);
        setLiveStatus((prev) => ({
          ...prev,
          [evt.job_id]: evt,
        }));

        // If a job completed, refresh the list
        if (evt.status === "completed" || evt.status === "failed" || evt.status === "cancelled") {
          fetchJobs();
          onJobCompleted?.(evt.job_id);
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      // Attempt reconnect after 3s
      setTimeout(() => {
        // The effect cleanup will handle reconnection
      }, 3000);
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [fetchJobs, onJobCompleted]);

  /* ── Submit job ── */
  const handleSubmit = async () => {
    if (!scriptId) return;
    try {
      setSubmitting(true);
      const data: ExecutionJobCreate = {
        script_id: scriptId,
        browser,
        headless,
        timeout_seconds: timeout,
        base_url: baseUrl || undefined,
        environment_id: environmentId || undefined,
      };
      const job = await submitExecutionJob(data);
      fetchJobs();
      setSelectedJobId(job.id);
    } catch (err) {
      console.error("Failed to submit job:", err);
    } finally {
      setSubmitting(false);
    }
  };

  /* ── Cancel job ── */
  const handleCancel = async (jobId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Cancel this execution?")) return;
    try {
      await cancelExecutionJob(jobId);
      fetchJobs();
    } catch (err) {
      console.error("Failed to cancel job:", err);
    }
  };

  /* ── Load selected job detail ── */
  useEffect(() => {
    if (!selectedJobId) {
      setSelectedJob(null);
      return;
    }
    const load = async () => {
      try {
        const data = await getExecutionJob(selectedJobId);
        setSelectedJob(data);
      } catch (err) {
        console.error("Failed to load job:", err);
      }
    };
    load();
  }, [selectedJobId]);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <Activity className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-sm font-semibold">Execution</h3>
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto h-6 w-6"
          onClick={fetchJobs}
        >
          <RefreshCw className="h-3 w-3" />
        </Button>
      </div>

      {/* Submit form */}
      {scriptId && (
        <div className="border-b px-3 py-3 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Browser</label>
              <Select value={browser} onValueChange={setBrowser}>
                <SelectTrigger className="h-7 text-xs mt-0.5">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="chromium">Chromium</SelectItem>
                  <SelectItem value="firefox">Firefox</SelectItem>
                  <SelectItem value="webkit">WebKit</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Timeout (s)</label>
              <Input
                type="number"
                value={timeout}
                onChange={(e) => setTimeout_(Number(e.target.value))}
                className="h-7 text-xs mt-0.5"
                min={10}
                max={600}
              />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Base URL</label>
            <Input
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://staging.example.com"
              className="h-7 text-xs mt-0.5"
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={headless}
                onChange={(e) => setHeadless(e.target.checked)}
                className="rounded"
              />
              Headless
            </label>
            <Button
              size="sm"
              className="ml-auto"
              onClick={handleSubmit}
              disabled={submitting}
            >
              {submitting ? (
                <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
              ) : (
                <Play className="h-3.5 w-3.5 mr-1" />
              )}
              Run
            </Button>
          </div>
        </div>
      )}

      {/* Jobs list */}
      <div className="flex-1 overflow-y-auto">
        {jobsLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : jobs.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
            No execution jobs yet
          </div>
        ) : (
          <ul className="divide-y">
            {jobs.map((job) => {
              const live = liveStatus[job.id];
              const displayStatus = live?.status ?? job.status;
              const progress = live?.progress;

              return (
                <li
                  key={job.id}
                  className={cn(
                    "flex cursor-pointer items-center gap-2 px-3 py-2 hover:bg-accent",
                    selectedJobId === job.id && "bg-accent"
                  )}
                  onClick={() => setSelectedJobId(job.id)}
                >
                  {statusIcon(displayStatus)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-medium truncate">
                        Job {job.id.slice(0, 8)}
                      </span>
                      <Badge tone={statusTone(displayStatus)} className="text-[10px] px-1 py-0">
                        {displayStatus}
                      </Badge>
                    </div>
                    {progress !== undefined && (
                      <div className="mt-0.5 h-1 w-full rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full bg-blue-500 transition-all"
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                    )}
                    <span className="text-[10px] text-muted-foreground">
                      {new Date(job.created_at).toLocaleString()}
                    </span>
                  </div>
                  {(displayStatus === "pending" || displayStatus === "running") && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={(e) => handleCancel(job.id, e)}
                    >
                      <Square className="h-3 w-3 text-rose-500" />
                    </Button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Selected job detail */}
      {selectedJob && (
        <div className="border-t px-3 py-2 bg-muted/20 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium">Job Details</span>
            <Badge tone={statusTone(selectedJob.status)} className="text-[10px] px-1 py-0">
              {selectedJob.status}
            </Badge>
          </div>
          {selectedJob.container_id && (
            <p className="text-[10px] text-muted-foreground">
              Container: {selectedJob.container_id.slice(0, 12)}
            </p>
          )}
          {selectedJob.started_at && (
            <p className="text-[10px] text-muted-foreground">
              Started: {new Date(selectedJob.started_at).toLocaleString()}
            </p>
          )}
          {selectedJob.finished_at && (
            <p className="text-[10px] text-muted-foreground">
              Completed: {new Date(selectedJob.finished_at).toLocaleString()}
            </p>
          )}
          {selectedJob.error_message && (
            <p className="text-[10px] text-rose-600 break-all">{selectedJob.error_message}</p>
          )}
        </div>
      )}
    </div>
  );
}
