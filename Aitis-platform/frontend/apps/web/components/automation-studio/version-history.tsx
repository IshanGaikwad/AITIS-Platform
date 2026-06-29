"use client";

import { useState, useEffect, useCallback } from "react";
import Editor from "@monaco-editor/react";
import {
  listScriptVersions,
  getScriptVersionDiff,
  approveScriptVersion,
  restoreScriptVersion,
} from "@/lib/api";
import type { ScriptVersionSummary, ScriptVersionDiff } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  GitBranch,
  CheckCircle2,
  RotateCcw,
  ThumbsUp,
  ChevronDown,
  ChevronRight,
  Loader2,
  ArrowLeftRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Version status badge ── */
function versionStatusTone(status: string): "green" | "amber" | "slate" | "blue" | "purple" | "rose" {
  switch (status) {
    case "approved":
      return "green";
    case "pending":
      return "amber";
    case "superseded":
      return "slate";
    case "rejected":
      return "rose";
    default:
      return "slate";
  }
}

interface VersionHistoryProps {
  scriptId: string | null;
  onVersionRestored?: () => void;
}

export function VersionHistory({ scriptId, onVersionRestored }: VersionHistoryProps) {
  const [versions, setVersions] = useState<ScriptVersionSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [diff, setDiff] = useState<ScriptVersionDiff | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  /* ── Fetch versions ── */
  const fetchVersions = useCallback(async () => {
    if (!scriptId) {
      setVersions([]);
      return;
    }
    try {
      setLoading(true);
      const data = await listScriptVersions(scriptId);
      setVersions(data);
    } catch (err) {
      console.error("Failed to load versions:", err);
    } finally {
      setLoading(false);
    }
  }, [scriptId]);

  useEffect(() => {
    fetchVersions();
  }, [fetchVersions]);

  /* ── Toggle version expand / load diff ── */
  const handleToggle = async (versionId: string) => {
    if (expandedId === versionId) {
      setExpandedId(null);
      setDiff(null);
      return;
    }
    setExpandedId(versionId);
    setDiff(null);

    if (!scriptId) return;
    try {
      setDiffLoading(true);
      const version = versions.find(v => v.id === versionId);
      if (version) {
        const data = await getScriptVersionDiff(scriptId, version.version, version.version - 1);
        setDiff(data);
      }
    } catch (err) {
      console.error("Failed to load diff:", err);
    } finally {
      setDiffLoading(false);
    }
  };

  /* ── Approve version ── */
  const handleApprove = async (versionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!scriptId) return;
    try {
      setActionLoading(versionId);
      await approveScriptVersion(scriptId, versionId);
      fetchVersions();
    } catch (err) {
      console.error("Failed to approve version:", err);
    } finally {
      setActionLoading(null);
    }
  };

  /* ── Restore version ── */
  const handleRestore = async (versionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!scriptId || !confirm("Restore this version as the current content?")) return;
    try {
      setActionLoading(versionId);
      await restoreScriptVersion(scriptId, versionId);
      fetchVersions();
      onVersionRestored?.();
    } catch (err) {
      console.error("Failed to restore version:", err);
    } finally {
      setActionLoading(null);
    }
  };

  if (!scriptId) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground text-sm">
        Select a script to view version history
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <GitBranch className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-sm font-semibold">Version History</h3>
        <span className="text-xs text-muted-foreground ml-auto">{versions.length} versions</span>
      </div>

      {/* Version list */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : versions.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
            No versions yet
          </div>
        ) : (
          <ul className="divide-y">
            {versions.map((v) => (
              <li key={v.id}>
                {/* Version row */}
                <div
                  className="flex cursor-pointer items-center gap-2 px-3 py-2 hover:bg-accent"
                  onClick={() => handleToggle(v.id)}
                >
                  {expandedId === v.id ? (
                    <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  )}
                  <span className="text-sm font-medium">v{v.version}</span>
                  <Badge tone={versionStatusTone(v.status)} className="text-[10px] px-1.5 py-0">
                    {v.status}
                  </Badge>
                  <span className="flex-1 truncate text-xs text-muted-foreground">
                    {v.change_summary}
                  </span>
                  <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                    {new Date(v.created_at).toLocaleDateString()}
                  </span>

                  {/* Actions */}
                  {v.status === "pending" && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={(e) => handleApprove(v.id, e)}
                      disabled={actionLoading === v.id}
                    >
                      {actionLoading === v.id ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <ThumbsUp className="h-3 w-3 text-green-600" />
                      )}
                    </Button>
                  )}
                  {v.status !== "current" && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={(e) => handleRestore(v.id, e)}
                      disabled={actionLoading === v.id}
                    >
                      <RotateCcw className="h-3 w-3 text-muted-foreground" />
                    </Button>
                  )}
                </div>

                {/* Expanded diff view */}
                {expandedId === v.id && (
                  <div className="border-t bg-muted/20 px-3 py-2">
                    {diffLoading ? (
                      <div className="flex items-center justify-center py-4">
                        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      </div>
                    ) : diff ? (
                      <div className="space-y-2">
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <ArrowLeftRight className="h-3 w-3" />
                          Diff from previous version
                        </div>
                        {diff.unified_diff ? (
                          <Editor
                            height="200px"
                            language="diff"
                            value={diff.unified_diff}
                            theme="vs-dark"
                            options={{
                              readOnly: true,
                              fontSize: 12,
                              minimap: { enabled: false },
                              scrollBeyondLastLine: false,
                              lineNumbers: "on",
                            }}
                          />
                        ) : (
                          <p className="text-xs text-muted-foreground italic">
                            No diff available (first version or no previous version to compare)
                          </p>
                        )}
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">Failed to load diff</p>
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
