"use client";

import { useState, useCallback } from "react";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ScriptList } from "@/components/automation-studio/script-list";
import { ScriptEditor } from "@/components/automation-studio/script-editor";
import { VersionHistory } from "@/components/automation-studio/version-history";
import { ExecutionPanel } from "@/components/automation-studio/execution-panel";
import { ResultsViewer } from "@/components/automation-studio/results-viewer";
import { RecorderBrowser } from "@/components/automation-studio/recorder-browser";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Code2,
  History,
  Play,
  BarChart3,
  Video,
} from "lucide-react";

export default function AutomationStudioPage() {
  /* ── Script selection ── */
  const [selectedScriptId, setSelectedScriptId] = useState<string | null>(null);

  /* ── Right panel tab ── */
  const [rightTab, setRightTab] = useState("versions");

  /* ── Execution tracking ── */
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  /* ── Editor refresh key (bump to force re-fetch after version restore / recording generate) ── */
  const [editorKey, setEditorKey] = useState(0);
  const bumpEditor = useCallback(() => setEditorKey((k) => k + 1), []);

  /* ── Job completed → switch to results tab ── */
  const handleJobCompleted = useCallback((jobId: string) => {
    setActiveJobId(jobId);
    setRightTab("results");
  }, []);

  /* ── Run from editor → switch to execution tab ── */
  const handleRun = useCallback(() => {
    setRightTab("execution");
  }, []);

  return (
    <ProtectedRoute>
      <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
        {/* ── Left sidebar: Script list ── */}
        <aside className="w-64 shrink-0 border-r bg-background">
          <ScriptList
            selectedId={selectedScriptId}
            onSelect={setSelectedScriptId}
            onScriptCreated={(script) => {
              setSelectedScriptId(script.id);
              bumpEditor();
            }}
          />
        </aside>

        {/* ── Center: Script editor ── */}
        <main className="flex-1 min-w-0">
          {selectedScriptId ? (
            <ScriptEditor
              key={editorKey}
              scriptId={selectedScriptId}
              onRun={handleRun}
              onVersionCreated={() => setRightTab("versions")}
            />
          ) : (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              <div className="text-center space-y-2">
                <Code2 className="h-10 w-10 mx-auto text-muted-foreground/50" />
                <p className="text-sm">Select or create a script to begin</p>
              </div>
            </div>
          )}
        </main>

        {/* ── Right panel: Tabbed tools ── */}
        <aside className="w-80 shrink-0 border-l bg-background">
          <Tabs value={rightTab} onValueChange={setRightTab} className="flex h-full flex-col">
            <TabsList className="w-full justify-start rounded-none border-b bg-transparent px-1 py-0 h-9">
              <TabsTrigger value="versions" className="text-xs gap-1 data-[state=active]:bg-accent">
                <History className="h-3 w-3" /> Versions
              </TabsTrigger>
              <TabsTrigger value="execution" className="text-xs gap-1 data-[state=active]:bg-accent">
                <Play className="h-3 w-3" /> Run
              </TabsTrigger>
              <TabsTrigger value="results" className="text-xs gap-1 data-[state=active]:bg-accent">
                <BarChart3 className="h-3 w-3" /> Results
              </TabsTrigger>
              <TabsTrigger value="recorder" className="text-xs gap-1 data-[state=active]:bg-accent">
                <Video className="h-3 w-3" /> Record
              </TabsTrigger>
            </TabsList>

            <TabsContent value="versions" className="flex-1 overflow-y-auto mt-0">
              <VersionHistory
                scriptId={selectedScriptId}
                onVersionRestored={bumpEditor}
              />
            </TabsContent>

            <TabsContent value="execution" className="flex-1 overflow-y-auto mt-0">
              <ExecutionPanel
                scriptId={selectedScriptId}
                onJobCompleted={handleJobCompleted}
              />
            </TabsContent>

            <TabsContent value="results" className="flex-1 overflow-y-auto mt-0">
              <ResultsViewer jobId={activeJobId} />
            </TabsContent>

            <TabsContent value="recorder" className="flex-1 overflow-y-auto mt-0">
              <RecorderBrowser
                scriptId={selectedScriptId}
                onGenerated={bumpEditor}
              />
            </TabsContent>
          </Tabs>
        </aside>
      </div>
    </ProtectedRoute>
  );
}
