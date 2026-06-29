"use client";

import { useState, useEffect, useCallback } from "react";
import {
  listRecordingSessions,
  getRecordedActions,
  generateFromRecording,
} from "@/lib/api";
import type { RecordingSession, RecordedAction } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Video,
  MousePointerClick,
  Type,
  Scroll,
  Navigation,
  Loader2,
  Wand2,
  ChevronDown,
  ChevronRight,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Action type icon ── */
function actionIcon(type: string) {
  switch (type) {
    case "click":
      return <MousePointerClick className="h-3.5 w-3.5 text-blue-500" />;
    case "type":
    case "fill":
      return <Type className="h-3.5 w-3.5 text-green-500" />;
    case "scroll":
      return <Scroll className="h-3.5 w-3.5 text-amber-500" />;
    case "navigate":
    case "goto":
      return <Navigation className="h-3.5 w-3.5 text-purple-500" />;
    default:
      return <MousePointerClick className="h-3.5 w-3.5 text-muted-foreground" />;
  }
}

function actionTone(type: string): "blue" | "green" | "amber" | "purple" | "slate" | "rose" {
  switch (type) {
    case "click":
      return "blue";
    case "type":
    case "fill":
      return "green";
    case "scroll":
      return "amber";
    case "navigate":
    case "goto":
      return "purple";
    default:
      return "slate";
  }
}

interface RecorderBrowserProps {
  scriptId: string | null;
  onGenerated?: () => void;
}

export function RecorderBrowser({ scriptId, onGenerated }: RecorderBrowserProps) {
  const [sessions, setSessions] = useState<RecordingSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedSession, setExpandedSession] = useState<string | null>(null);
  const [actions, setActions] = useState<RecordedAction[]>([]);
  const [actionsLoading, setActionsLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  /* ── Fetch sessions ── */
  const fetchSessions = useCallback(async () => {
    try {
      setLoading(true);
      const data = await listRecordingSessions();
      setSessions(data);
    } catch (err) {
      console.error("Failed to load recording sessions:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  /* ── Toggle session expand / load actions ── */
  const handleToggleSession = async (sessionId: string) => {
    if (expandedSession === sessionId) {
      setExpandedSession(null);
      setActions([]);
      return;
    }
    setExpandedSession(sessionId);
    setActions([]);
    try {
      setActionsLoading(true);
      const data = await getRecordedActions(sessionId);
      setActions(data);
    } catch (err) {
      console.error("Failed to load recorded actions:", err);
    } finally {
      setActionsLoading(false);
    }
  };

  /* ── Generate script from recording ── */
  const handleGenerate = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!scriptId) return;
    try {
      setGenerating(true);
      await generateFromRecording(scriptId, sessionId);
      onGenerated?.();
    } catch (err) {
      console.error("Failed to generate from recording:", err);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <Video className="h-4 w-4 text-muted-foreground" />
        <h3 className="text-sm font-semibold">Recorder</h3>
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto h-6 w-6"
          onClick={fetchSessions}
        >
          <RefreshCw className="h-3 w-3" />
        </Button>
      </div>

      {/* Info banner */}
      <div className="border-b px-3 py-2 bg-muted/20">
        <p className="text-xs text-muted-foreground">
          Use the browser extension to record user interactions. Recorded sessions appear here and can be converted into Playwright test scripts.
        </p>
      </div>

      {/* Sessions list */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
            No recording sessions yet
          </div>
        ) : (
          <ul className="divide-y">
            {sessions.map((session) => (
              <li key={session.session_id}>
                {/* Session row */}
                <div
                  className="flex cursor-pointer items-center gap-2 px-3 py-2 hover:bg-accent"
                  onClick={() => handleToggleSession(session.session_id)}
                >
                  {expandedSession === session.session_id ? (
                    <ChevronDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  )}
                  <Video className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {`Session ${session.session_id.slice(0, 8)}`}
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      {session.action_count ?? 0} actions{session.created_at ? ` · ${new Date(session.created_at).toLocaleDateString()}` : ""}
                    </p>
                  </div>
                  {scriptId && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 text-xs"
                      onClick={(e) => handleGenerate(session.session_id, e)}
                      disabled={generating}
                    >
                      {generating ? (
                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                      ) : (
                        <Wand2 className="h-3 w-3 mr-1" />
                      )}
                      Generate
                    </Button>
                  )}
                </div>

                {/* Expanded actions list */}
                {expandedSession === session.session_id && (
                  <div className="border-t bg-muted/10 px-3 py-2">
                    {actionsLoading ? (
                      <div className="flex items-center justify-center py-4">
                        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                      </div>
                    ) : actions.length === 0 ? (
                      <p className="text-xs text-muted-foreground italic py-2">
                        No actions recorded in this session
                      </p>
                    ) : (
                      <ol className="space-y-1">
                        {actions.map((action, idx) => (
                          <li
                            key={action.id ?? idx}
                            className="flex items-center gap-2 text-xs py-0.5"
                          >
                            <span className="text-muted-foreground w-4 text-right shrink-0">
                              {idx + 1}
                            </span>
                            {actionIcon(action.action_type)}
                            <Badge tone={actionTone(action.action_type)} className="text-[10px] px-1 py-0">
                              {action.action_type}
                            </Badge>
                            <span className="flex-1 truncate text-muted-foreground">
                              {action.selector && (
                                <code className="text-[10px] bg-muted px-1 rounded">
                                  {action.selector}
                                </code>
                              )}
                              {action.value && (
                                <span className="ml-1 text-[10px]">
                                  → "{action.value.length > 30 ? action.value.slice(0, 30) + "…" : action.value}"
                                </span>
                              )}
                            </span>
                            {action.url && (
                              <span className="text-[10px] text-muted-foreground truncate max-w-[120px]">
                                {action.url}
                              </span>
                            )}
                          </li>
                        ))}
                      </ol>
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
