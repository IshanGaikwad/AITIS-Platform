"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Plus, CheckCircle, Play, GitCommit, Code, FileCode } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type FileStatus = "Passing" | "Failing" | "Pending";

const mockFiles: Array<{
  id: string;
  name: string;
  tests: number;
  lastModified: string;
  status: FileStatus;
}> = [
  { id: "f-001", name: "auth.spec.ts", tests: 8, lastModified: "2h ago", status: "Passing" },
  { id: "f-002", name: "checkout.spec.ts", tests: 12, lastModified: "Yesterday", status: "Failing" },
  { id: "f-003", name: "profile.spec.ts", tests: 5, lastModified: "3 days ago", status: "Passing" },
  { id: "f-004", name: "dashboard.spec.ts", tests: 7, lastModified: "1 week ago", status: "Pending" },
];

const statusTone: Record<FileStatus, "green" | "rose" | "slate"> = {
  Passing: "green",
  Failing: "rose",
  Pending: "slate",
};

const statusDot: Record<FileStatus, string> = {
  Passing: "bg-emerald-500",
  Failing: "bg-rose-500",
  Pending: "bg-slate-300",
};

export default function AutomationPage() {
  const params = useParams();
  const [selectedFileId, setSelectedFileId] = useState<string>("f-001");

  const selectedFile = mockFiles.find((f) => f.id === selectedFileId);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-slate-900">Automation Studio</h2>
          <Badge tone="blue">Playwright TypeScript</Badge>
        </div>
        <Button size="sm">
          <Plus className="h-4 w-4" />
          New Script
        </Button>
      </div>

      {/* Toolbar */}
      <div className="flex gap-2">
        <Button variant="outline" size="sm" disabled={!selectedFileId}>
          <CheckCircle className="h-4 w-4" />
          Validate
        </Button>
        <Button variant="outline" size="sm" disabled={!selectedFileId}>
          <Play className="h-4 w-4" />
          Run Selected
        </Button>
        <Button variant="outline" size="sm" disabled={!selectedFileId}>
          <GitCommit className="h-4 w-4" />
          Commit
        </Button>
      </div>

      {/* Two-panel layout */}
      <div
        className="grid overflow-hidden rounded-xl border border-slate-200"
        style={{ gridTemplateColumns: "220px 1fr", minHeight: "440px" }}
      >
        {/* File list */}
        <div className="border-r border-slate-200 bg-slate-50">
          <div className="border-b border-slate-200 px-3 py-2.5">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Files</p>
          </div>
          <div className="py-1">
            {mockFiles.map((file) => (
              <button
                key={file.id}
                onClick={() => setSelectedFileId(file.id)}
                className={cn(
                  "flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm transition-colors",
                  selectedFileId === file.id
                    ? "bg-white font-medium text-slate-900"
                    : "text-slate-600 hover:bg-white/70",
                )}
              >
                <FileCode className="h-3.5 w-3.5 shrink-0 text-blue-400" />
                <span className="min-w-0 flex-1 truncate">{file.name}</span>
                <span
                  className={cn("h-1.5 w-1.5 shrink-0 rounded-full", statusDot[file.status])}
                />
              </button>
            ))}
          </div>
        </div>

        {/* Editor panel */}
        <div className="flex flex-col bg-white">
          {selectedFile ? (
            <>
              <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-4 py-2.5">
                <div className="flex items-center gap-2 text-sm">
                  <FileCode className="h-4 w-4 text-blue-400" />
                  <span className="font-medium text-slate-700">{selectedFile.name}</span>
                  <span className="text-slate-400">·</span>
                  <span className="text-xs text-slate-400">{selectedFile.tests} tests</span>
                  <span className="text-slate-400">·</span>
                  <span className="text-xs text-slate-400">{selectedFile.lastModified}</span>
                </div>
                <Badge tone={statusTone[selectedFile.status]}>{selectedFile.status}</Badge>
              </div>
              <div className="flex flex-1 items-center justify-center p-8 text-center">
                <div>
                  <Code className="mx-auto mb-3 h-10 w-10 text-slate-200" />
                  <p className="text-sm font-medium text-slate-400">Monaco Editor</p>
                  <p className="mt-1 text-xs text-slate-400">
                    Integrate Monaco or CodeMirror here to enable in-browser editing of{" "}
                    <span className="font-mono">{selectedFile.name}</span>
                  </p>
                </div>
              </div>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center p-8 text-center">
              <div>
                <Code className="mx-auto mb-3 h-10 w-10 text-slate-200" />
                <p className="text-sm text-slate-400">
                  Select a file to edit or use Monaco editor
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
