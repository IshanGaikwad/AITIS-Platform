"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { FileCode, Wand2, Save, Play, AlertCircle, Loader2, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/use-toast";
import {
  getTestSuites,
  getTestCases,
  runFullGeneration,
  createAutomationScript,
  updateTestCase,
} from "@/lib/api";
import type { TestCaseDB } from "@/lib/types";
import { cn } from "@/lib/utils";

interface GenFile {
  file_name: string;
  content: string;
  kind: "test" | "config";
}

const FRAMEWORKS = ["Playwright", "Cypress", "Selenium", "Robot Framework", "API Test"] as const;
type Framework = (typeof FRAMEWORKS)[number];

const FRAMEWORK_LANGUAGE: Record<string, string> = {
  Playwright: "typescript",
  Cypress: "javascript",
  Selenium: "python",
  "Robot Framework": "robotframework",
  "API Test": "javascript",
};

/* Auto-select a framework from a test case's tags, else default to Playwright. */
function detectFramework(testCase: TestCaseDB | undefined): Framework {
  const tags = (testCase?.tags ?? []).map((t) => t.toLowerCase());
  for (const fw of FRAMEWORKS) {
    if (tags.some((t) => t.includes(fw.toLowerCase().split(" ")[0]))) return fw;
  }
  return "Playwright";
}

/* Supporting files a framework needs to actually run, generated locally. */
function scaffoldFiles(framework: Framework, specName: string): GenFile[] {
  switch (framework) {
    case "Cypress":
      return [
        {
          file_name: "cypress.config.js",
          kind: "config",
          content:
            "const { defineConfig } = require('cypress');\n\nmodule.exports = defineConfig({\n  e2e: {\n    baseUrl: 'http://localhost:3000',\n    supportFile: false,\n  },\n});\n",
        },
        {
          file_name: "package.json",
          kind: "config",
          content:
            '{\n  "name": "aitis-cypress-suite",\n  "scripts": { "test": "cypress run" },\n  "devDependencies": { "cypress": "^13.0.0" }\n}\n',
        },
      ];
    case "Selenium":
      return [
        { file_name: "requirements.txt", kind: "config", content: "selenium>=4.0\npytest>=7.0\n" },
        {
          file_name: "conftest.py",
          kind: "config",
          content:
            "import pytest\nfrom selenium import webdriver\n\n\n@pytest.fixture\ndef driver():\n    d = webdriver.Chrome()\n    yield d\n    d.quit()\n",
        },
      ];
    case "Robot Framework":
      return [{ file_name: "requirements.txt", kind: "config", content: "robotframework>=6.0\nrobotframework-seleniumlibrary>=6.0\n" }];
    case "API Test":
      return [
        {
          file_name: "package.json",
          kind: "config",
          content:
            '{\n  "name": "aitis-api-suite",\n  "scripts": { "test": "jest" },\n  "devDependencies": { "jest": "^29.0.0", "supertest": "^6.0.0" }\n}\n',
        },
      ];
    case "Playwright":
    default:
      return [
        {
          file_name: "playwright.config.ts",
          kind: "config",
          content:
            "import { defineConfig } from '@playwright/test';\n\nexport default defineConfig({\n  testDir: './',\n  use: { baseURL: 'http://localhost:3000', headless: true },\n});\n",
        },
        {
          file_name: "package.json",
          kind: "config",
          content:
            '{\n  "name": "aitis-playwright-suite",\n  "scripts": { "test": "playwright test" },\n  "devDependencies": { "@playwright/test": "^1.45.0" }\n}\n',
        },
      ];
  }
}

export default function AutomationPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = params.projectId as string;
  const { toast } = useToast();

  const [cases, setCases] = useState<TestCaseDB[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [framework, setFramework] = useState<Framework>("Playwright");

  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [files, setFiles] = useState<GenFile[]>([]);
  const [selectedFileName, setSelectedFileName] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedReady, setSavedReady] = useState(false);

  const selectedCase = useMemo(() => cases.find((c) => c.id === selectedCaseId), [cases, selectedCaseId]);
  const selectedFile = files.find((f) => f.file_name === selectedFileName);

  /* Load automated test cases for the workspace */
  const loadCases = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const suites = await getTestSuites(workspaceId);
      const all = (await Promise.all(suites.map((s) => getTestCases(s.id)))).flat();
      setCases(all.filter((c) => c.status === "automated"));
    } catch {
      setLoadError("Failed to load test cases.");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  /* Auto-select framework when the test case changes */
  useEffect(() => {
    if (selectedCase) {
      setFramework(detectFramework(selectedCase));
      setFiles([]);
      setSelectedFileName("");
      setSavedReady(false);
      setGenError(null);
    }
  }, [selectedCase]);

  const handleGenerate = async () => {
    if (!selectedCase) return;
    setGenerating(true);
    setGenError(null);
    setSavedReady(false);
    try {
      const acceptanceCriteria =
        selectedCase.preconditions && selectedCase.preconditions.length > 0
          ? selectedCase.preconditions
          : [selectedCase.title];
      // framework may include "Robot Framework" (not in the strict Story union);
      // the backend accepts any framework string, so cast to the request type.
      const result = await runFullGeneration({
        jiraId: "",
        title: selectedCase.title,
        description: selectedCase.description || selectedCase.title,
        acceptanceCriteria,
        framework,
      } as Parameters<typeof runFullGeneration>[0]);
      const testFiles: GenFile[] = (result.automation ?? []).map((a) => ({
        file_name: a.file_name,
        content: a.content,
        kind: "test",
      }));
      const specName = testFiles[0]?.file_name ?? "test";
      const all = [...testFiles, ...scaffoldFiles(framework, specName)];
      setFiles(all);
      setSelectedFileName(all[0]?.file_name ?? "");
    } catch (err) {
      setGenError(err instanceof Error ? err.message : "Failed to generate automation files.");
    } finally {
      setGenerating(false);
    }
  };

  const handleSaveReady = async () => {
    if (!selectedCase || files.length === 0) return;
    setSaving(true);
    try {
      const language = FRAMEWORK_LANGUAGE[framework] ?? "typescript";
      // Persist each generated file as an automation script (execution-ready)
      await Promise.all(
        files.map((f) =>
          createAutomationScript({
            name: `${selectedCase.title} — ${f.file_name}`,
            framework: framework.toLowerCase().split(" ")[0],
            language,
            status: "ready",
            code: f.content,
            file_path: f.file_name,
            test_case_id: selectedCase.id,
          }).catch(() => null)
        )
      );
      // Keep the test case marked automated
      await updateTestCase(selectedCase.test_suite_id, selectedCase.id, { status: "automated" }).catch(() => null);
      setSavedReady(true);
      toast({ title: "Automation saved", description: "Files are ready for the Execution tab.", variant: "success" });
    } catch (err) {
      toast({
        title: "Failed to save",
        description: err instanceof Error ? err.message : "An error occurred.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Automation Studio</h2>
          <p className="text-sm text-slate-500">
            Generate the runnable files for an automated test case, ready for execution.
          </p>
        </div>
        {savedReady && (
          <Button size="sm" variant="outline" onClick={() => router.push(`/studio/${workspaceId}/execution`)}>
            <Play className="h-4 w-4" />
            Go to Execution
          </Button>
        )}
      </div>

      {/* Selectors */}
      <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-slate-600">Automated test case</label>
          <select
            value={selectedCaseId}
            onChange={(e) => setSelectedCaseId(e.target.value)}
            disabled={loading || cases.length === 0}
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 disabled:opacity-60"
          >
            <option value="">
              {loading ? "Loading…" : cases.length === 0 ? "No automated test cases" : "Select a test case"}
            </option>
            {cases.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-slate-600">Framework (auto-selected)</label>
          <select
            value={framework}
            onChange={(e) => {
              setFramework(e.target.value as Framework);
              setFiles([]);
              setSelectedFileName("");
              setSavedReady(false);
            }}
            disabled={!selectedCase}
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400 disabled:opacity-60"
          >
            {FRAMEWORKS.map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </div>
        <Button onClick={handleGenerate} disabled={!selectedCase || generating}>
          {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
          {generating ? "Generating…" : "Generate Files"}
        </Button>
      </div>

      {loadError && (
        <div className="flex items-center gap-2 rounded-lg border border-rose-100 bg-rose-50 p-3 text-sm text-rose-700">
          <AlertCircle className="h-4 w-4 shrink-0" /> {loadError}
        </div>
      )}
      {!loading && cases.length === 0 && !loadError && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          No automated test cases yet. In the{" "}
          <button
            onClick={() => router.push(`/studio/${workspaceId}/test-cases`)}
            className="font-medium text-slate-900 underline underline-offset-2"
          >
            Test Case Generator
          </button>
          , mark a saved test case as <span className="font-medium">Automated</span> and it will appear here.
        </div>
      )}
      {genError && (
        <div className="flex items-center gap-2 rounded-lg border border-rose-100 bg-rose-50 p-3 text-sm text-rose-700">
          <AlertCircle className="h-4 w-4 shrink-0" /> {genError}
        </div>
      )}

      {/* Files + content panes */}
      {files.length > 0 && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-600">
              <span className="font-medium text-slate-900">{files.length}</span> files generated for{" "}
              <Badge tone="blue">{framework}</Badge>
            </p>
            <Button size="sm" onClick={handleSaveReady} disabled={saving || savedReady}>
              {savedReady ? <CheckCircle2 className="h-4 w-4" /> : saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              {savedReady ? "Ready for execution" : saving ? "Saving…" : "Save & mark ready"}
            </Button>
          </div>

          <div
            className="grid overflow-hidden rounded-xl border border-slate-200"
            style={{ gridTemplateColumns: "240px 1fr", minHeight: "440px" }}
          >
            {/* Files pane */}
            <div className="border-r border-slate-200 bg-slate-50">
              <div className="border-b border-slate-200 px-3 py-2.5">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Files</p>
              </div>
              <div className="py-1">
                {files.map((file) => (
                  <button
                    key={file.file_name}
                    onClick={() => setSelectedFileName(file.file_name)}
                    className={cn(
                      "flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm transition-colors",
                      selectedFileName === file.file_name
                        ? "bg-white font-medium text-slate-900"
                        : "text-slate-600 hover:bg-white/70"
                    )}
                  >
                    <FileCode
                      className={cn("h-3.5 w-3.5 shrink-0", file.kind === "test" ? "text-blue-400" : "text-slate-400")}
                    />
                    <span className="min-w-0 flex-1 truncate">{file.file_name}</span>
                    {file.kind === "config" && (
                      <span className="text-[10px] uppercase tracking-wide text-slate-400">cfg</span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Content pane */}
            <div className="flex flex-col bg-white">
              {selectedFile ? (
                <>
                  <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50 px-4 py-2.5 text-sm">
                    <FileCode className="h-4 w-4 text-blue-400" />
                    <span className="font-medium text-slate-700">{selectedFile.file_name}</span>
                    <Badge tone={selectedFile.kind === "test" ? "green" : "slate"}>
                      {selectedFile.kind === "test" ? "Test" : "Config"}
                    </Badge>
                  </div>
                  <pre className="flex-1 overflow-auto bg-slate-950 p-4 text-xs leading-relaxed text-slate-100">
                    <code>{selectedFile.content}</code>
                  </pre>
                </>
              ) : (
                <div className="flex flex-1 items-center justify-center p-8 text-sm text-slate-400">
                  Select a file to view its content
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
