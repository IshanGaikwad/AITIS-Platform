"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Plus,
  Search,
  FlaskConical,
  Pencil,
  Trash2,
  AlertCircle,
  Wand2,
  FileText,
  Code2,
  ListChecks,
  Check,
  ChevronsUpDown,
  Cpu,
  Save,
} from "lucide-react";
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
} from "@/components/ui/dialog";
import { useToast } from "@/components/ui/use-toast";
import {
  getStories,
  runFullGeneration,
  getTestSuites,
  createTestSuite,
  getTestCases,
  createTestCase,
  updateTestCase,
  deleteTestCase,
} from "@/lib/api";
import type {
  SavedStory,
  TestSuite,
  TestCaseDB,
  TestStepCreateInput,
  Story,
  Framework,
  TestCase as GeneratedTestCase,
  Scenario,
  AutomationArtifact,
  CoverageSummary,
} from "@/lib/types";
import { cn } from "@/lib/utils";

/* ── Constants ── */
const FRAMEWORKS: Framework[] = ["Playwright", "Cypress", "Selenium", "API Test"];
type GenFormat = "manual" | "automation";

const STATUS_TABS = ["All", "draft", "in_review", "approved", "automated", "deprecated"] as const;
type StatusTab = (typeof STATUS_TABS)[number];

const STATUS_LABEL: Record<string, string> = {
  All: "All",
  draft: "Draft",
  in_review: "In Review",
  approved: "Approved",
  automated: "Automated",
  deprecated: "Deprecated",
};

const STATUS_TONE: Record<string, "slate" | "amber" | "green" | "blue" | "rose"> = {
  draft: "slate",
  in_review: "amber",
  approved: "green",
  automated: "blue",
  deprecated: "rose",
};

const TYPE_TONE: Record<string, "green" | "rose" | "amber" | "blue" | "slate"> = {
  functional: "green",
  happy: "green",
  negative: "rose",
  boundary: "amber",
  edge: "amber",
  security: "blue",
};

const TYPE_OPTIONS = ["functional", "negative", "boundary", "security"] as const;
const PRIORITY_OPTIONS = ["high", "medium", "low"] as const;

// Scope is persisted as the test case's first tag (no dedicated DB column —
// see [[scope-field-gap]] discovery: tags is the existing extensible field).
const SCOPE_OPTIONS = ["Regression", "SIT", "UAT", "Ad-Hoc"] as const;
const SCOPE_TONE: Record<string, "blue" | "amber" | "green" | "slate"> = {
  Regression: "blue",
  SIT: "amber",
  UAT: "green",
  "Ad-Hoc": "slate",
};

interface CaseForm {
  title: string;
  type: string;
  priority: string;
  description: string;
  preconditions: string;
  scope: string;
  requirementId: number | "";
}

const EMPTY_FORM: CaseForm = {
  title: "",
  type: "functional",
  priority: "medium",
  description: "",
  preconditions: "",
  scope: "",
  requirementId: "",
};

const GENERATED_TYPE_TO_CASE_TYPE: Record<string, string> = {
  Happy: "functional",
  Negative: "negative",
  Edge: "boundary",
  Security: "security",
};

function storyToGenerationInput(story: SavedStory, framework: Framework): Story {
  return {
    jiraId: story.jiraId ?? "",
    title: story.title,
    description: story.description ?? "",
    acceptanceCriteria: story.acceptanceCriteria ?? [],
    framework,
  };
}

function generatedTestToPayload(
  test: GeneratedTestCase,
  title: string,
  scope: string,
  requirementId: number | "",
): Partial<Omit<TestCaseDB, "steps">> & { steps?: TestStepCreateInput[] } {
  return {
    title,
    type: GENERATED_TYPE_TO_CASE_TYPE[test.type] ?? test.type.toLowerCase(),
    priority: test.priority.toLowerCase(),
    description: test.rationale || undefined,
    tags: scope ? [scope] : undefined,
    requirement_ids: requirementId ? [String(requirementId)] : undefined,
    steps: test.steps.map((action, i) => ({
      order: i + 1,
      type: "action",
      action,
      expected_result: i === test.steps.length - 1 ? test.expectedResult : undefined,
    })),
  };
}

export default function TestCaseGeneratorPage() {
  const params = useParams();
  const workspaceId = params.projectId as string;
  const { toast } = useToast();

  /* ── Generation state ── */
  const [stories, setStories] = useState<SavedStory[]>([]);
  const [storiesLoading, setStoriesLoading] = useState(true);
  const [selectedStoryId, setSelectedStoryId] = useState<number | "">("");
  const [selectedFrameworks, setSelectedFrameworks] = useState<Framework[]>(["Playwright"]);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [genFormat, setGenFormat] = useState<GenFormat>("manual");

  const [genTests, setGenTests] = useState<GeneratedTestCase[]>([]);
  const [genScenarios, setGenScenarios] = useState<Scenario[]>([]);
  const [genAutomationByFramework, setGenAutomationByFramework] = useState<Record<string, AutomationArtifact[]>>({});
  const [genFrameworks, setGenFrameworks] = useState<Framework[]>([]);
  const [activeAutomationFramework, setActiveAutomationFramework] = useState<Framework>("Playwright");
  const [genCoverage, setGenCoverage] = useState<CoverageSummary | null>(null);
  const [generatedFor, setGeneratedFor] = useState<string | null>(null);

  /* ── Save generated test case(s) ── */
  const [savedGenIds, setSavedGenIds] = useState<Set<string>>(new Set());
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [saveMode, setSaveMode] = useState<"single" | "all">("single");
  const [saveSingleTarget, setSaveSingleTarget] = useState<GeneratedTestCase | null>(null);
  const [saveTitle, setSaveTitle] = useState("");
  const [saveScope, setSaveScope] = useState<string>(SCOPE_OPTIONS[0]);
  const [savingGen, setSavingGen] = useState(false);
  const [saveGenError, setSaveGenError] = useState<string | null>(null);

  /* ── Saved (DB) test cases state ── */
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [cases, setCases] = useState<TestCaseDB[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [activeStatus, setActiveStatus] = useState<StatusTab>("All");

  const [modalOpen, setModalOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<TestCaseDB | null>(null);
  const [form, setForm] = useState<CaseForm>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  /* ── Loaders ── */
  const fetchStories = useCallback(async () => {
    setStoriesLoading(true);
    try {
      const data = await getStories();
      setStories(data);
    } catch {
      // non-fatal — generation panel will show an empty hint
    } finally {
      setStoriesLoading(false);
    }
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const fetchedSuites = await getTestSuites(workspaceId);
      setSuites(fetchedSuites);
      const allCases = await Promise.all(fetchedSuites.map((s) => getTestCases(s.id)));
      setCases(allCases.flat());
    } catch {
      setError("Failed to load test cases.");
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    fetchStories();
    fetchData();
  }, [fetchStories, fetchData]);

  /* ── Generation ── */
  const toggleFramework = (fw: Framework) => {
    setSelectedFrameworks((prev) =>
      prev.includes(fw) ? prev.filter((f) => f !== fw) : [...prev, fw],
    );
  };

  const handleGenerate = async () => {
    const story = analyzedStories.find((s) => s.id === selectedStoryId);
    if (!story) {
      setGenError("Select an analyzed requirement to generate from.");
      return;
    }
    if (selectedFrameworks.length === 0) {
      setGenError("Select at least one automation framework.");
      return;
    }
    setGenerating(true);
    setGenError(null);
    try {
      const frameworks = [...selectedFrameworks];
      // One generation per framework — automation code is framework-specific
      const results = await Promise.all(
        frameworks.map((fw) => runFullGeneration(storyToGenerationInput(story, fw))),
      );
      // Manual tests, Gherkin scenarios, and coverage are framework-independent
      setGenTests(results[0].tests ?? []);
      setGenScenarios(results[0].scenarios ?? []);
      setGenCoverage(results[0].coverage ?? null);
      // Automation code grouped by framework
      const byFramework: Record<string, AutomationArtifact[]> = {};
      frameworks.forEach((fw, i) => {
        byFramework[fw] = results[i].automation ?? [];
      });
      setGenAutomationByFramework(byFramework);
      setGenFrameworks(frameworks);
      setActiveAutomationFramework(frameworks[0]);
      setGeneratedFor(story.title);
      setGenFormat("manual");
      setSavedGenIds(new Set());
    } catch (err) {
      setGenError(err instanceof Error ? err.message : "Failed to generate test cases.");
    } finally {
      setGenerating(false);
    }
  };

  /* ── Save generated test case(s) into a suite ── */
  const ensureSuite = async (): Promise<string> => {
    if (suites.length > 0) return suites[0].id;
    const created = await createTestSuite({ workspace_id: workspaceId, name: "Generated Tests" });
    setSuites((prev) => [created, ...prev]);
    return created.id;
  };

  const openSaveSingle = (test: GeneratedTestCase) => {
    setSaveMode("single");
    setSaveSingleTarget(test);
    setSaveTitle(test.title);
    setSaveScope(SCOPE_OPTIONS[0]);
    setSaveGenError(null);
    setSaveDialogOpen(true);
  };

  const openSaveAll = () => {
    setSaveMode("all");
    setSaveSingleTarget(null);
    setSaveTitle("");
    setSaveScope(SCOPE_OPTIONS[0]);
    setSaveGenError(null);
    setSaveDialogOpen(true);
  };

  const handleConfirmSaveGenerated = async () => {
    setSavingGen(true);
    setSaveGenError(null);
    try {
      const suiteId = await ensureSuite();
      const targets =
        saveMode === "single" && saveSingleTarget
          ? [saveSingleTarget]
          : genTests.filter((t) => !savedGenIds.has(t.id));
      const created = await Promise.all(
        targets.map((test) =>
          createTestCase(
            suiteId,
            generatedTestToPayload(
              test,
              saveMode === "single" ? saveTitle.trim() || test.title : test.title,
              saveScope,
              selectedStoryId,
            ),
          ),
        ),
      );
      setCases((prev) => [...created, ...prev]);
      setSavedGenIds((prev) => {
        const next = new Set(prev);
        targets.forEach((t) => next.add(t.id));
        return next;
      });
      toast({
        title: created.length > 1 ? `${created.length} test cases saved` : "Test case saved",
        variant: "success",
      });
      setSaveDialogOpen(false);
    } catch (err) {
      setSaveGenError(err instanceof Error ? err.message : "Failed to save test case(s).");
    } finally {
      setSavingGen(false);
    }
  };

  /* ── Saved test case CRUD ── */
  const filtered = cases.filter((tc) => {
    const matchStatus = activeStatus === "All" || tc.status === activeStatus;
    const q = search.toLowerCase();
    const matchSearch = tc.title.toLowerCase().includes(q) || tc.id.toLowerCase().includes(q);
    return matchStatus && matchSearch;
  });

  const openAdd = () => {
    setEditTarget(null);
    setForm(EMPTY_FORM);
    setFormError(null);
    setModalOpen(true);
  };

  const openEdit = (tc: TestCaseDB) => {
    setEditTarget(tc);
    setForm({
      title: tc.title,
      type: tc.type,
      priority: tc.priority,
      description: tc.description ?? "",
      preconditions: (tc.preconditions ?? []).join("\n"),
      scope: tc.tags?.[0] ?? "",
      requirementId: tc.requirement_ids?.[0] ? (tc.requirement_ids[0] as unknown as number) : "",
    });
    setFormError(null);
    setModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim()) {
      setFormError("Title is required.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      const payload: Partial<TestCaseDB> = {
        title: form.title.trim(),
        type: form.type,
        priority: form.priority,
        description: form.description.trim() || undefined,
        preconditions: form.preconditions.split("\n").map((l) => l.trim()).filter(Boolean),
        tags: form.scope ? [form.scope] : [],
        requirement_ids: form.requirementId ? [String(form.requirementId)] : [],
      };

      if (editTarget) {
        const updated = await updateTestCase(editTarget.test_suite_id, editTarget.id, payload);
        setCases((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
        toast({ title: "Test case updated", variant: "success" });
      } else {
        const suiteId = await ensureSuite();
        const created = await createTestCase(suiteId, payload);
        setCases((prev) => [created, ...prev]);
        toast({ title: "Test case created", variant: "success" });
      }
      setModalOpen(false);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Operation failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (tc: TestCaseDB) => {
    setDeleting(true);
    try {
      await deleteTestCase(tc.test_suite_id, tc.id);
      setCases((prev) => prev.filter((c) => c.id !== tc.id));
      setDeleteConfirmId(null);
      toast({ title: "Test case deleted" });
    } catch {
      toast({ title: "Failed to delete test case", variant: "destructive" });
    } finally {
      setDeleting(false);
    }
  };

  const handleToggleAutomated = async (tc: TestCaseDB) => {
    const next = tc.status === "automated" ? "draft" : "automated";
    try {
      const updated = await updateTestCase(tc.test_suite_id, tc.id, { status: next });
      setCases((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      toast({
        title: next === "automated" ? "Marked automated" : "Marked draft",
        description: next === "automated" ? "Available in the Automation tab." : undefined,
        variant: "success",
      });
    } catch {
      toast({ title: "Failed to update status", variant: "destructive" });
    }
  };

  const hasGenerated = genTests.length > 0 || genScenarios.length > 0 || genFrameworks.length > 0;

  // Only requirements marked "approved" (Analyzed) are ready for test generation.
  const analyzedStories = stories.filter((s) => (s.status ?? "draft").toLowerCase() === "approved");

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Test Case Generator</h2>
        <p className="text-sm text-slate-500">
          Generate manual and automation test cases from a requirement, then manage your saved cases.
        </p>
      </div>

      {/* ── Generation panel ── */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <Wand2 className="h-4 w-4 text-slate-700" />
          <h3 className="text-sm font-semibold text-slate-900">Generate from a requirement</h3>
        </div>

        {!storiesLoading && stories.length === 0 ? (
          <div className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600">
            No requirements yet. Import or add one in the{" "}
            <Link
              href={`/studio/${workspaceId}/requirements`}
              className="font-medium text-slate-900 underline underline-offset-2"
            >
              Requirements
            </Link>{" "}
            tab first.
          </div>
        ) : !storiesLoading && analyzedStories.length === 0 ? (
          <div className="rounded-lg bg-amber-50 p-4 text-sm text-amber-800">
            None of your requirements have been marked Analyzed yet. Mark a requirement as Analyzed in the{" "}
            <Link
              href={`/studio/${workspaceId}/requirements`}
              className="font-medium underline underline-offset-2"
            >
              Requirements
            </Link>{" "}
            tab before generating test cases from it.
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-600">Requirement</label>
                <RequirementCombobox
                  stories={analyzedStories}
                  value={selectedStoryId}
                  onChange={setSelectedStoryId}
                  loading={storiesLoading}
                />
              </div>
              <Button onClick={handleGenerate} disabled={generating || !selectedStoryId}>
                <Wand2 className="h-4 w-4" />
                {generating ? "Generating..." : "Generate"}
              </Button>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-600">
                Automation frameworks{" "}
                <span className="font-normal text-slate-400">(select one or more)</span>
              </label>
              <div className="flex flex-wrap gap-2">
                {FRAMEWORKS.map((fw) => {
                  const active = selectedFrameworks.includes(fw);
                  return (
                    <button
                      key={fw}
                      type="button"
                      onClick={() => toggleFramework(fw)}
                      className={cn(
                        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                        active
                          ? "border-slate-900 bg-slate-900 text-white"
                          : "border-slate-200 text-slate-600 hover:border-slate-300",
                      )}
                    >
                      {active && <Check className="h-3.5 w-3.5" />}
                      {fw}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {genError && <p className="mt-3 text-sm text-rose-600">{genError}</p>}

        {genCoverage && (
          <div className="mt-4 flex flex-wrap gap-2 text-xs">
            <Badge tone="blue">Coverage: {genCoverage.coveragePercent ?? 0}%</Badge>
            <Badge tone="green">
              Covered: {genCoverage.coveredAcceptanceCriteria ?? 0}/
              {genCoverage.totalAcceptanceCriteria ?? 0}
            </Badge>
            {genTests.length > 0 && <Badge tone="slate">{genTests.length} test cases</Badge>}
          </div>
        )}
      </div>

      {/* ── Generated results ── */}
      {hasGenerated && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slate-600">
              Generated for <span className="font-medium text-slate-900">{generatedFor}</span>
            </p>
            <div className="flex flex-wrap items-center gap-2">
              {genFormat === "manual" && genTests.length > 0 && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={openSaveAll}
                  disabled={savedGenIds.size === genTests.length}
                >
                  <Save className="h-3.5 w-3.5" />
                  Save All
                </Button>
              )}
              <div className="inline-flex rounded-lg border border-slate-200 p-0.5">
                <button
                  onClick={() => setGenFormat("manual")}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                    genFormat === "manual" ? "bg-slate-900 text-white" : "text-slate-600 hover:text-slate-900",
                  )}
                >
                  <FileText className="h-3.5 w-3.5" /> Manual
                </button>
                <button
                  onClick={() => setGenFormat("automation")}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                    genFormat === "automation" ? "bg-slate-900 text-white" : "text-slate-600 hover:text-slate-900",
                  )}
                >
                  <Code2 className="h-3.5 w-3.5" /> Automation
                </button>
              </div>
            </div>
          </div>

          {genFormat === "manual" ? (
            <ManualView tests={genTests} savedIds={savedGenIds} onSave={openSaveSingle} />
          ) : (
            <AutomationView
              scenarios={genScenarios}
              frameworks={genFrameworks}
              automationByFramework={genAutomationByFramework}
              activeFramework={activeAutomationFramework}
              onSelectFramework={setActiveAutomationFramework}
            />
          )}
        </div>
      )}

      {/* ── Saved test cases ── */}
      <div className="space-y-4 border-t border-slate-200 pt-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <ListChecks className="h-4 w-4 text-slate-700" />
            <h3 className="text-sm font-semibold text-slate-900">Saved test cases</h3>
          </div>
          <Button size="sm" onClick={openAdd}>
            <Plus className="h-4 w-4" />
            New Test Case
          </Button>
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search test cases..."
            className="w-full rounded-lg border border-slate-200 py-2 pl-9 pr-4 text-sm outline-none focus:border-slate-400"
          />
        </div>

        <div className="flex overflow-x-auto border-b border-slate-200">
          {STATUS_TABS.map((status) => (
            <button
              key={status}
              onClick={() => setActiveStatus(status)}
              className={cn(
                "whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition-colors",
                activeStatus === status
                  ? "border-slate-900 text-slate-900"
                  : "border-transparent text-slate-500 hover:text-slate-700",
              )}
            >
              {STATUS_LABEL[status]}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-14 animate-pulse rounded-lg border border-slate-100 bg-slate-50" />
            ))}
          </div>
        ) : error ? (
          <div className="flex flex-col items-center py-16 text-center">
            <AlertCircle className="mb-3 h-8 w-8 text-rose-300" />
            <p className="text-sm text-slate-500">{error}</p>
            <Button variant="outline" size="sm" className="mt-3" onClick={fetchData}>
              Retry
            </Button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center text-slate-500">
            <FlaskConical className="mx-auto mb-3 h-8 w-8 text-slate-300" />
            <p className="text-sm">No saved test cases yet.</p>
          </div>
        ) : (
          <div className="space-y-1">
            <div className="flex items-center gap-3 border-b border-slate-100 px-4 py-2 text-xs font-medium uppercase tracking-wide text-slate-400">
              <span className="flex-1">Title</span>
              <span className="hidden w-24 sm:block">Type</span>
              <span className="hidden w-16 md:block">Priority</span>
              <span className="hidden w-24 lg:block">Status</span>
              <span className="hidden w-24 lg:block">Scope</span>
              <span className="w-20 text-right">Actions</span>
            </div>

            {filtered.map((tc) => (
              <div
                key={tc.id}
                className="flex items-center gap-3 rounded-lg border border-slate-100 bg-white px-4 py-3 transition-colors hover:border-slate-200"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-slate-800">{tc.title}</p>
                  <p className="font-mono text-xs text-slate-400">{tc.id.slice(0, 8)}…</p>
                </div>
                <span className="hidden w-24 sm:block">
                  <Badge tone={TYPE_TONE[tc.type?.toLowerCase()] ?? "slate"}>{tc.type}</Badge>
                </span>
                <span className="hidden w-16 text-xs font-medium capitalize text-slate-500 md:block">
                  {tc.priority}
                </span>
                <span className="hidden w-24 lg:block">
                  <Badge tone={STATUS_TONE[tc.status] ?? "slate"}>
                    {STATUS_LABEL[tc.status] ?? tc.status}
                  </Badge>
                </span>
                <span className="hidden w-24 lg:block">
                  {tc.tags?.[0] && <Badge tone={SCOPE_TONE[tc.tags[0]] ?? "slate"}>{tc.tags[0]}</Badge>}
                </span>
                <div className="flex w-20 justify-end gap-1">
                  {deleteConfirmId === tc.id ? (
                    <div className="flex items-center gap-1">
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 border-rose-200 px-2 text-xs text-rose-600"
                        onClick={() => handleDelete(tc)}
                        disabled={deleting}
                      >
                        Yes
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-xs"
                        onClick={() => setDeleteConfirmId(null)}
                      >
                        No
                      </Button>
                    </div>
                  ) : (
                    <>
                      <Button
                        variant="ghost"
                        size="icon"
                        className={cn(
                          "h-7 w-7",
                          tc.status === "automated" ? "text-blue-600" : "text-slate-400 hover:text-blue-600"
                        )}
                        title={tc.status === "automated" ? "Automated — click to unmark" : "Mark automated"}
                        onClick={() => handleToggleAutomated(tc)}
                      >
                        <Cpu className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEdit(tc)}>
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-rose-400 hover:text-rose-600"
                        onClick={() => setDeleteConfirmId(tc.id)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* New / Edit manual test case */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editTarget ? "Edit Test Case" : "New Test Case"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">
                Title <span className="text-rose-500">*</span>
              </label>
              <Input
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                placeholder="Test case title"
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-slate-700">Type</label>
                <select
                  value={form.type}
                  onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400"
                >
                  {TYPE_OPTIONS.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-slate-700">Priority</label>
                <select
                  value={form.priority}
                  onChange={(e) => setForm((f) => ({ ...f, priority: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400"
                >
                  {PRIORITY_OPTIONS.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-slate-700">Scope</label>
                <select
                  value={form.scope}
                  onChange={(e) => setForm((f) => ({ ...f, scope: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400"
                >
                  <option value="">No scope</option>
                  {SCOPE_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-slate-700">Linked requirement</label>
                <RequirementCombobox
                  stories={stories}
                  value={form.requirementId}
                  onChange={(id) => setForm((f) => ({ ...f, requirementId: id }))}
                  loading={storiesLoading}
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Description</label>
              <Textarea
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                rows={2}
                placeholder="Optional description..."
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Preconditions</label>
              <Textarea
                value={form.preconditions}
                onChange={(e) => setForm((f) => ({ ...f, preconditions: e.target.value }))}
                rows={2}
                placeholder="One precondition per line..."
              />
            </div>
            {formError && <p className="text-sm text-rose-600">{formError}</p>}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setModalOpen(false)} disabled={submitting}>
                Cancel
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Saving..." : editTarget ? "Save Changes" : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Save generated test case(s) */}
      <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {saveMode === "single"
                ? "Save Test Case"
                : `Save All (${genTests.filter((t) => !savedGenIds.has(t.id)).length})`}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-2">
            {saveMode === "single" && (
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-slate-700">Script name</label>
                <Input
                  value={saveTitle}
                  onChange={(e) => setSaveTitle(e.target.value)}
                  placeholder="Test case title"
                />
              </div>
            )}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Scope</label>
              <div className="flex flex-wrap gap-2">
                {SCOPE_OPTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setSaveScope(s)}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                      saveScope === s
                        ? "border-slate-900 bg-slate-900 text-white"
                        : "border-slate-200 text-slate-600 hover:border-slate-300",
                    )}
                  >
                    {saveScope === s && <Check className="h-3.5 w-3.5" />}
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Linked requirement</label>
              <div className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-600">
                {generatedFor ?? "—"}
              </div>
            </div>
            {saveGenError && <p className="text-sm text-rose-600">{saveGenError}</p>}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setSaveDialogOpen(false)}
              disabled={savingGen}
            >
              Cancel
            </Button>
            <Button type="button" onClick={handleConfirmSaveGenerated} disabled={savingGen}>
              {savingGen ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/* ── Manual format: generated test case cards ── */
function ManualView({
  tests,
  savedIds,
  onSave,
}: {
  tests: GeneratedTestCase[];
  savedIds: Set<string>;
  onSave: (test: GeneratedTestCase) => void;
}) {
  if (tests.length === 0) {
    return (
      <div className="rounded-lg bg-slate-50 p-8 text-center text-sm text-slate-500">
        No manual test cases were generated.
      </div>
    );
  }
  return (
    <div className="space-y-4">
      {tests.map((test) => {
        const saved = savedIds.has(test.id);
        return (
        <div key={test.id} className="rounded-xl border border-slate-200 p-5">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-base font-semibold text-slate-900">{test.title}</h4>
            <Badge
              tone={
                test.type === "Happy"
                  ? "green"
                  : test.type === "Negative"
                  ? "rose"
                  : test.type === "Security"
                  ? "blue"
                  : "amber"
              }
            >
              {test.type}
            </Badge>
            <Badge tone="slate">{test.id}</Badge>
            <Badge tone="blue">Priority: {test.priority}</Badge>
            <Button
              size="sm"
              variant="outline"
              className="ml-auto h-7 px-2 text-xs"
              onClick={() => onSave(test)}
              disabled={saved}
            >
              <Save className="h-3.5 w-3.5" />
              {saved ? "Saved" : "Save"}
            </Button>
          </div>

          {test.rationale && <p className="mt-2 text-sm text-slate-500">{test.rationale}</p>}

          <div className="mt-3 flex flex-wrap gap-2">
            {test.coversAcceptanceCriteria?.map((ac) => (
              <Badge key={ac} tone="green">
                Covers {ac}
              </Badge>
            ))}
            {test.riskTags?.map((tag) => (
              <Badge key={tag} tone="amber">
                {tag}
              </Badge>
            ))}
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div>
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Steps</div>
              <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-700">
                {test.steps.map((step, index) => (
                  <li key={index}>{step}</li>
                ))}
              </ol>
            </div>
            <div>
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Expected Result
              </div>
              <div className="rounded-lg bg-slate-50 p-4 text-sm text-slate-700">
                {test.expectedResult}
              </div>
            </div>
          </div>
        </div>
        );
      })}
    </div>
  );
}

/* ── Automation format: Gherkin scenarios + per-framework code ── */
function AutomationView({
  scenarios,
  frameworks,
  automationByFramework,
  activeFramework,
  onSelectFramework,
}: {
  scenarios: Scenario[];
  frameworks: Framework[];
  automationByFramework: Record<string, AutomationArtifact[]>;
  activeFramework: Framework;
  onSelectFramework: (fw: Framework) => void;
}) {
  if (scenarios.length === 0 && frameworks.length === 0) {
    return (
      <div className="rounded-lg bg-slate-50 p-8 text-center text-sm text-slate-500">
        No automation artifacts were generated.
      </div>
    );
  }

  const activeArtifacts = automationByFramework[activeFramework] ?? [];

  return (
    <div className="space-y-6">
      {scenarios.length > 0 && (
        <div className="space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Gherkin Scenarios <span className="font-normal normal-case text-slate-400">(framework-agnostic)</span>
          </div>
          {scenarios.map((scenario) => (
            <div key={scenario.id} className="rounded-xl bg-slate-950 p-5 text-sm text-slate-100">
              <div className="mb-2 flex items-center gap-2">
                <Badge tone="blue">{scenario.id}</Badge>
                <span className="text-slate-300">{scenario.title}</span>
              </div>
              <pre className="overflow-x-auto whitespace-pre-wrap">{scenario.gherkin}</pre>
            </div>
          ))}
        </div>
      )}

      {frameworks.length > 0 && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Automation Code
            </span>
            <div className="ml-auto inline-flex flex-wrap gap-0.5 rounded-lg border border-slate-200 p-0.5">
              {frameworks.map((fw) => (
                <button
                  key={fw}
                  onClick={() => onSelectFramework(fw)}
                  className={cn(
                    "rounded-md px-3 py-1 text-xs font-medium transition-colors",
                    fw === activeFramework
                      ? "bg-slate-900 text-white"
                      : "text-slate-600 hover:text-slate-900",
                  )}
                >
                  {fw}
                </button>
              ))}
            </div>
          </div>

          {activeArtifacts.length === 0 ? (
            <div className="rounded-lg bg-slate-50 p-6 text-center text-sm text-slate-500">
              No code was generated for {activeFramework}.
            </div>
          ) : (
            activeArtifacts.map((artifact) => (
              <div key={artifact.id} className="overflow-hidden rounded-xl border border-slate-200">
                <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
                  <span>{artifact.file_name}</span>
                  <Badge tone="slate">{activeFramework}</Badge>
                </div>
                <div className="bg-slate-950 p-5 text-sm text-slate-100">
                  <pre className="overflow-x-auto whitespace-pre-wrap">{artifact.content}</pre>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

/* ── Scalable searchable requirement selector ── */
function RequirementCombobox({
  stories,
  value,
  onChange,
  loading,
}: {
  stories: SavedStory[];
  value: number | "";
  onChange: (id: number | "") => void;
  loading?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  const selected = stories.find((s) => s.id === value);
  const q = query.trim().toLowerCase();
  const filtered = q
    ? stories.filter((s) => `${s.jiraId ?? ""} ${s.title}`.toLowerCase().includes(q))
    : stories;

  useEffect(() => {
    if (!open) return;
    function onDocMouseDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocMouseDown);
    return () => document.removeEventListener("mousedown", onDocMouseDown);
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        disabled={loading}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-sm outline-none transition-colors focus:border-slate-400 disabled:opacity-60"
      >
        <span className={cn("truncate", !selected && "text-slate-400")}>
          {selected
            ? `${selected.jiraId ? selected.jiraId + " — " : ""}${selected.title}`
            : loading
            ? "Loading requirements..."
            : "Select a requirement"}
        </span>
        <ChevronsUpDown className="h-4 w-4 shrink-0 text-slate-400" />
      </button>

      {open && (
        <div className="absolute z-20 mt-1 w-full rounded-lg border border-slate-200 bg-white shadow-lg">
          <div className="border-b border-slate-100 p-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search requirements..."
                className="w-full rounded-md border border-slate-200 py-1.5 pl-8 pr-2 text-sm outline-none focus:border-slate-400"
              />
            </div>
          </div>
          <div className="max-h-64 overflow-y-auto p-1">
            {filtered.length === 0 ? (
              <p className="px-3 py-4 text-center text-sm text-slate-400">No matches.</p>
            ) : (
              filtered.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => {
                    onChange(s.id);
                    setOpen(false);
                    setQuery("");
                  }}
                  className={cn(
                    "flex w-full items-start gap-2 rounded-md px-3 py-2 text-left text-sm hover:bg-slate-50",
                    s.id === value && "bg-slate-50",
                  )}
                >
                  <Check
                    className={cn(
                      "mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-700",
                      s.id !== value && "invisible",
                    )}
                  />
                  <span className="min-w-0">
                    <span className="block truncate font-medium text-slate-800">{s.title}</span>
                    {s.jiraId && <span className="block truncate text-xs text-slate-400">{s.jiraId}</span>}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
