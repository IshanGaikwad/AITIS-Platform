"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Editor, { OnMount } from "@monaco-editor/react";
import {
  getAutomationScript,
  updateAutomationScript,
  createScriptVersion,
} from "@/lib/api";
import type { AutomationScriptDetail, AutomationScriptUpdate, ScriptVersionCreate } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import {
  Save,
  GitBranch,
  Play,
  Clock,
  Loader2,
  Check,
} from "lucide-react";

/* ── Language → Monaco language map ── */
const langMap: Record<string, string> = {
  typescript: "typescript",
  javascript: "javascript",
  python: "python",
  java: "java",
  csharp: "csharp",
};

/* ── Default template per framework ── */
const defaultTemplates: Record<string, Record<string, string>> = {
  playwright: {
    typescript: `import { test, expect } from '@playwright/test';

test.describe('New Test Suite', () => {
  test('example test', async ({ page }) => {
    await page.goto('https://example.com');
    await expect(page).toHaveTitle(/Example/);
  });
});
`,
    python: `import re
from playwright.sync_api import Page, expect

def test_example(page: Page) -> None:
    page.goto("https://example.com")
    expect(page).to_have_title(re.compile("Example"))
`,
  },
  selenium: {
    python: `from selenium import webdriver
from selenium.webdriver.common.by import By

def test_example():
    driver = webdriver.Chrome()
    driver.get("https://example.com")
    assert "Example" in driver.title
    driver.quit()
`,
  },
  cypress: {
    javascript: `describe('New Test Suite', () => {
  it('example test', () => {
    cy.visit('https://example.com')
    cy.title().should('include', 'Example')
  })
})
`,
  },
  pytest: {
    python: `import pytest

def test_example():
    assert True
`,
  },
};

function getTemplate(framework: string, language: string): string {
  return defaultTemplates[framework]?.[language] ?? "// Write your test script here\n";
}

interface ScriptEditorProps {
  scriptId: string | null;
  onRun?: () => void;
  onVersionCreated?: () => void;
}

export function ScriptEditor({ scriptId, onRun, onVersionCreated }: ScriptEditorProps) {
  const [script, setScript] = useState<AutomationScriptDetail | null>(null);
  const [code, setCode] = useState("");
  const [originalCode, setOriginalCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [showVersionDialog, setShowVersionDialog] = useState(false);
  const [versionSummary, setVersionSummary] = useState("");
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null);

  /* ── Load script ── */
  const loadScript = useCallback(async () => {
    if (!scriptId) {
      setScript(null);
      setCode("");
      setOriginalCode("");
      setDirty(false);
      return;
    }
    try {
      setLoading(true);
      const data = await getAutomationScript(scriptId);
      setScript(data);
      const content = data.code ?? getTemplate(data.framework, data.language);
      setCode(content);
      setOriginalCode(content);
      setDirty(false);
    } catch (err) {
      console.error("Failed to load script:", err);
    } finally {
      setLoading(false);
    }
  }, [scriptId]);

  useEffect(() => {
    loadScript();
  }, [loadScript]);

  /* ── Auto-save debounce ── */
  useEffect(() => {
    if (!dirty || !scriptId) return;
    const timer = setTimeout(() => {
      handleSave();
    }, 3000);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code, dirty]);

  /* ── Save handler ── */
  const handleSave = async () => {
    if (!scriptId || !script) return;
    try {
      setSaving(true);
      const update: AutomationScriptUpdate = { code };
      await updateAutomationScript(scriptId, update);
      // Also save the code as the latest version content
      setOriginalCode(code);
      setDirty(false);
    } catch (err) {
      console.error("Failed to save script:", err);
    } finally {
      setSaving(false);
    }
  };

  /* ── Create version ── */
  const handleCreateVersion = async () => {
    if (!scriptId || !versionSummary.trim()) return;
    try {
      setSaving(true);
      const data: ScriptVersionCreate = {
        code: code,
        change_summary: versionSummary.trim(),
      };
      await createScriptVersion(scriptId, data);
      setShowVersionDialog(false);
      setVersionSummary("");
      setOriginalCode(code);
      setDirty(false);
      onVersionCreated?.();
    } catch (err) {
      console.error("Failed to create version:", err);
    } finally {
      setSaving(false);
    }
  };

  /* ── Keyboard shortcut: Ctrl+S ── */
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        if (dirty) handleSave();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dirty, code]);

  const monacoLang = script ? langMap[script.language] ?? "plaintext" : "typescript";

  if (!scriptId) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <div className="text-center">
          <FileCode2Icon className="mx-auto h-12 w-12 mb-3 opacity-40" />
          <p className="text-sm">Select a script to start editing</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-2 border-b px-3 py-1.5">
        {script && (
          <>
            <span className="text-sm font-medium truncate flex-1">{script.name}</span>
            <Badge tone="slate" className="text-[10px]">{script.language}</Badge>
            <Badge tone="slate" className="text-[10px]">{script.framework}</Badge>
          </>
        )}

        {dirty && (
          <span className="text-xs text-amber-600 flex items-center gap-1">
            <Clock className="h-3 w-3" /> Unsaved
          </span>
        )}
        {saving && (
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Loader2 className="h-3 w-3 animate-spin" /> Saving…
          </span>
        )}
        {!dirty && !saving && script && (
          <span className="text-xs text-green-600 flex items-center gap-1">
            <Check className="h-3 w-3" /> Saved
          </span>
        )}

        <Button
          variant="ghost"
          size="sm"
          onClick={handleSave}
          disabled={!dirty || saving}
        >
          <Save className="h-3.5 w-3.5 mr-1" /> Save
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowVersionDialog(true)}
        >
          <GitBranch className="h-3.5 w-3.5 mr-1" /> Version
        </Button>

        {onRun && (
          <Button variant="outline" size="sm" onClick={onRun}>
            <Play className="h-3.5 w-3.5 mr-1" /> Run
          </Button>
        )}
      </div>

      {/* Editor */}
      <div className="flex-1 min-h-0">
        <Editor
          height="100%"
          language={monacoLang}
          value={code}
          onChange={(value) => {
            const v = value ?? "";
            setCode(v);
            setDirty(v !== originalCode);
          }}
          onMount={(editor) => {
            editorRef.current = editor;
          }}
          theme="vs-dark"
          options={{
            fontSize: 13,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            wordWrap: "on",
            tabSize: 2,
            automaticLayout: true,
            padding: { top: 8 },
          }}
        />
      </div>

      {/* Create Version Dialog */}
      <Dialog open={showVersionDialog} onOpenChange={setShowVersionDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create Version</DialogTitle>
          </DialogHeader>
          <div className="py-2">
            <label className="text-sm font-medium">Change Summary</label>
            <Textarea
              value={versionSummary}
              onChange={(e) => setVersionSummary(e.target.value)}
              placeholder="Describe what changed in this version…"
              className="mt-1"
              rows={3}
            />
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button
              onClick={handleCreateVersion}
              disabled={!versionSummary.trim() || saving}
            >
              {saving && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
              Create Version
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/* ── Placeholder icon ── */
function FileCode2Icon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
      <path d="M14 2v4a2 2 0 0 0 2 2h4" />
      <path d="m10 13-2 2 2 2" />
      <path d="m14 17 2-2-2-2" />
    </svg>
  );
}
