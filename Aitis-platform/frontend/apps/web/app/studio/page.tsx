"use client";

import { useEffect, useMemo, useState } from "react";

import { AcceptanceCriteriaEditor } from "@/components/acceptance-criteria-editor";
import { Badge } from "@/components/ui/badge";
import { Section } from "@/components/ui/section";
import { extractAcceptanceCriteriaCandidates } from "@/lib/ac-mapper";
import {
  createStory,
  deleteStory,
  getApiBaseUrl,
  getJiraIssue,
  getStories,
  importJiraIssue,
  runFullGeneration,
  searchJiraIssues,
  updateStory,
} from "@/lib/api";
import type { JiraIssue, SavedStory } from "@/lib/api";
import type {
  AutomationArtifact,
  CoverageSummary,
  Framework,
  Intent,
  Scenario,
  Story,
  TestCase,
} from "@/lib/types";

type TabKey = "story" | "intent" | "tests" | "gherkin" | "automation";

const emptyStory: Story = {
  jiraId: "",
  title: "",
  description: "",
  acceptanceCriteria: [],
  framework: "Playwright",
};

function textToCriteria(text: string): string[] {
  return text
    .split(/\n+/)
    .map((line) => line.replace(/^\s*\d+[.)-]?\s*/, "").trim())
    .filter(Boolean);
}

function criteriaToText(criteria: string[]): string {
  return criteria.map((item, index) => `${index + 1}. ${item}`).join("\n");
}

export default function HomePage() {
  const [story, setStory] = useState<Story>(emptyStory);
  const [stories, setStories] = useState<SavedStory[]>([]);
  const [selectedStoryId, setSelectedStoryId] = useState<number | null>(null);

  const [acceptanceCriteriaText, setAcceptanceCriteriaText] = useState("");
  const [activeTab, setActiveTab] = useState<TabKey>("story");

  const [intent, setIntent] = useState<Intent | null>(null);
  const [tests, setTests] = useState<TestCase[]>([]);
  const [coverage, setCoverage] = useState<CoverageSummary | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [automation, setAutomation] = useState<AutomationArtifact[]>([]);

  const [loading, setLoading] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);

  const [jiraIssueKey, setJiraIssueKey] = useState("");
  const [jiraJql, setJiraJql] = useState('issuetype = Story ORDER BY updated DESC');
  const [jiraResults, setJiraResults] = useState<JiraIssue[]>([]);
  const [jiraSearchLoading, setJiraSearchLoading] = useState(false);
  const [jiraImportingKey, setJiraImportingKey] = useState<string | null>(null);
  const [jiraNextPageToken, setJiraNextPageToken] = useState<string | null>(null);

  const [acDraftItems, setAcDraftItems] = useState<string[]>([]);
  const [showAcEditor, setShowAcEditor] = useState(false);

  const tabs: { id: TabKey; label: string }[] = [
    { id: "story", label: "Jira Story" },
    { id: "intent", label: "Intent Model" },
    { id: "tests", label: "Test Cases" },
    { id: "gherkin", label: "Gherkin" },
    { id: "automation", label: "Automation Code" },
  ];

  const stats = useMemo(
    () => ({
      acceptanceCriteriaCount: textToCriteria(acceptanceCriteriaText).length,
      artifactsGenerated: intent ? "Intent, Tests, Gherkin, Code" : "Pending",
      coveragePercent: coverage?.coveragePercent ?? 0,
    }),
    [acceptanceCriteriaText, intent, coverage],
  );

  function applyStoryToForm(nextStory: Story) {
    const mappedCriteria =
      nextStory.acceptanceCriteria && nextStory.acceptanceCriteria.length > 0
        ? nextStory.acceptanceCriteria
        : extractAcceptanceCriteriaCandidates(nextStory.description ?? "");

    setStory({
      jiraId: nextStory.jiraId ?? "",
      title: nextStory.title ?? "",
      description: nextStory.description ?? "",
      acceptanceCriteria: mappedCriteria,
      framework: nextStory.framework ?? "Playwright",
    });

    setAcceptanceCriteriaText(criteriaToText(mappedCriteria));
    setAcDraftItems(mappedCriteria);
  }

  function resetArtifacts() {
    setIntent(null);
    setTests([]);
    setCoverage(null);
    setScenarios([]);
    setAutomation([]);
    setGeneratedAt(null);
  }

  function handleNewStory() {
    setSelectedStoryId(null);
    applyStoryToForm(emptyStory);
    resetArtifacts();
    setActiveTab("story");
    setShowAcEditor(false);
    setError(null);
  }

  function handleApplyAcMapping() {
    const cleaned = acDraftItems.map((item) => item.trim()).filter(Boolean);

    setAcDraftItems(cleaned);
    setAcceptanceCriteriaText(criteriaToText(cleaned));

    setStory((current) => ({
      ...current,
      acceptanceCriteria: cleaned,
    }));
  }

  function updateStoryField<K extends keyof Story>(field: K, value: Story[K]) {
    setStory((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function loadStories(selectId?: number | null) {
    const savedStories = await getStories();
    setStories(savedStories);

    if (savedStories.length === 0) {
      setSelectedStoryId(null);
      applyStoryToForm(emptyStory);
      return;
    }

    const selected =
      typeof selectId === "number"
        ? savedStories.find((item) => item.id === selectId) ?? savedStories[0]
        : savedStories[0];

    setSelectedStoryId(selected.id);
    applyStoryToForm(selected);
  }

  useEffect(() => {
    async function bootstrap() {
      setBootstrapping(true);
      setError(null);

      try {
        await loadStories();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load stories from backend");
      } finally {
        setBootstrapping(false);
      }
    }

    bootstrap();
  }, []);

  async function handleSelectStory(storyId: number) {
    if (!storyId) {
      handleNewStory();
      return;
    }

    const selected = stories.find((item) => item.id === storyId);
    if (!selected) return;

    setSelectedStoryId(selected.id);
    applyStoryToForm(selected);
    resetArtifacts();
    setActiveTab("story");
    setError(null);
  }

  async function handleSaveStory() {
    setSaving(true);
    setError(null);

    try {
      const payload: Story = {
        ...story,
        acceptanceCriteria: textToCriteria(acceptanceCriteriaText),
      };

      if (selectedStoryId) {
        const updated = await updateStory(selectedStoryId, payload);
        setSelectedStoryId(updated.id);
        applyStoryToForm(updated);
        await loadStories(updated.id);
      } else {
        const created = await createStory(payload);
        setSelectedStoryId(created.id);
        applyStoryToForm(created);
        await loadStories(created.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save story");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteStory() {
    if (!selectedStoryId) return;

    setSaving(true);
    setError(null);

    try {
      await deleteStory(selectedStoryId);
      resetArtifacts();
      await loadStories();
      setActiveTab("story");
      setShowAcEditor(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete story");
    } finally {
      setSaving(false);
    }
  }

  async function handleGenerate() {
    setLoading(true);
    setError(null);

    try {
      const normalizedStory: Story = {
        ...story,
        acceptanceCriteria: textToCriteria(acceptanceCriteriaText),
      };

      setStory(normalizedStory);

      const result = await runFullGeneration(normalizedStory);
      setIntent(result.intent);
      setTests(result.tests);
      setCoverage(result.coverage);
      setScenarios(result.scenarios);
      setAutomation(result.automation);
      setGeneratedAt(new Date().toLocaleString());
      setActiveTab("intent");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate test artifacts");
    } finally {
      setLoading(false);
    }
  }

  async function handleSearchJira(resetResults: boolean = true) {
    if (!jiraJql.trim()) {
      setError("Please enter a JQL query.");
      return;
    }

    setJiraSearchLoading(true);
    setError(null);

    try {
      const result = await searchJiraIssues(
        jiraJql,
        10,
        resetResults ? undefined : jiraNextPageToken ?? undefined,
      );

      setJiraResults((current) =>
        resetResults ? result.issues ?? [] : [...current, ...(result.issues ?? [])],
      );
      setJiraNextPageToken(result.nextPageToken ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to search Jira");
    } finally {
      setJiraSearchLoading(false);
    }
  }

  async function handleFetchJiraIssue() {
    if (!jiraIssueKey.trim()) {
      setError("Please enter a Jira issue key.");
      return;
    }

    setJiraSearchLoading(true);
    setError(null);

    try {
      const issue = await getJiraIssue(jiraIssueKey.trim());
      setJiraResults([issue]);
      setJiraNextPageToken(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch Jira issue");
    } finally {
      setJiraSearchLoading(false);
    }
  }

  async function handleImportJiraIssue(issueKey: string) {
    setJiraImportingKey(issueKey);
    setError(null);

    try {
      const imported = await importJiraIssue(issueKey);
      await loadStories(imported.id);
      setSelectedStoryId(imported.id);
      applyStoryToForm(imported);
      setShowAcEditor(true);
      setActiveTab("story");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to import Jira issue");
    } finally {
      setJiraImportingKey(null);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Badge tone="blue">AI Test Intelligence</Badge>
              <Badge tone="green">Jira Import Enabled</Badge>
              <Badge tone="amber">Coverage Aware</Badge>
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-slate-950">
              AI Test Intelligence Studio
            </h1>
            <p className="mt-3 max-w-3xl text-base text-slate-600">
              Search Jira, import stories into the platform, refine acceptance criteria, and generate
              coverage-aware test artifacts.
            </p>
            <p className="mt-2 text-sm text-slate-500">
              API base URL: <span className="font-medium text-slate-700">{getApiBaseUrl()}</span>
            </p>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Jira to Test Workflow
            </h2>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              {[
                "1. Search Jira",
                "2. Import Story",
                "3. Refine ACs",
                "4. Save / Select Story",
                "5. Generate Coverage-Aware Tests",
                "6. Generate Automation",
              ].map((step) => (
                <div key={step} className="rounded-2xl bg-slate-50 p-3 text-slate-700">
                  {step}
                </div>
              ))}
            </div>
            <div className="mt-4 rounded-2xl bg-emerald-50 p-4 text-sm text-emerald-800">
              <strong>Status:</strong> {bootstrapping ? "Loading stories..." : "Backend ready"}
            </div>
          </div>
        </div>

        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
          <div className="space-y-6">
            <Section
              title="Jira Import"
              subtitle="Fetch a single issue by key or search stories with JQL"
            >
              <div className="space-y-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Jira Issue Key
                  </label>
                  <div className="flex gap-2">
                    <input
                      value={jiraIssueKey}
                      onChange={(event) => setJiraIssueKey(event.target.value)}
                      placeholder="AUTH-123"
                      className="w-full rounded-2xl border border-slate-200 px-4 py-2.5 outline-none transition focus:border-slate-400"
                    />
                    <button
                      onClick={handleFetchJiraIssue}
                      disabled={jiraSearchLoading}
                      className="rounded-2xl bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:bg-slate-400"
                    >
                      Fetch
                    </button>
                  </div>
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">JQL Search</label>
                  <textarea
                    value={jiraJql}
                    onChange={(event) => setJiraJql(event.target.value)}
                    rows={4}
                    className="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-slate-400"
                  />
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => handleSearchJira(true)}
                    disabled={jiraSearchLoading}
                    className="rounded-2xl bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:bg-slate-400"
                  >
                    {jiraSearchLoading ? "Searching..." : "Search Jira"}
                  </button>

                  {jiraNextPageToken ? (
                    <button
                      onClick={() => handleSearchJira(false)}
                      disabled={jiraSearchLoading}
                      className="rounded-2xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                    >
                      Load More
                    </button>
                  ) : null}
                </div>

                {jiraResults.length ? (
                  <div className="space-y-3">
                    {jiraResults.map((issue) => (
                      <div key={issue.key} className="rounded-2xl border border-slate-200 p-4">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge tone="blue">{issue.key}</Badge>
                          {issue.fields.issuetype?.name ? (
                            <Badge tone="green">{issue.fields.issuetype.name}</Badge>
                          ) : null}
                          {issue.fields.status?.name ? (
                            <Badge tone="amber">{issue.fields.status.name}</Badge>
                          ) : null}
                          {issue.fields.priority?.name ? (
                            <Badge tone="rose">{issue.fields.priority.name}</Badge>
                          ) : null}
                        </div>

                        <div className="mt-2 text-sm font-medium text-slate-900">
                          {issue.fields.summary || "(No summary)"}
                        </div>

                        <button
                          onClick={() => handleImportJiraIssue(issue.key)}
                          disabled={jiraImportingKey === issue.key}
                          className="mt-3 rounded-2xl bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:bg-slate-400"
                        >
                          {jiraImportingKey === issue.key ? "Importing..." : "Import to Stories"}
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-500">
                    No Jira results yet. Search Jira or fetch by issue key.
                  </div>
                )}
              </div>
            </Section>

            {showAcEditor ? (
              <AcceptanceCriteriaEditor
                sourceText={story.description}
                items={acDraftItems}
                onChange={setAcDraftItems}
                onApply={handleApplyAcMapping}
              />
            ) : null}

            <Section
              title="Story Workspace"
              subtitle="Create, edit, save, and generate from backend-managed stories"
            >
              <div className="mb-4 flex flex-wrap gap-2">
                <button
                  onClick={handleNewStory}
                  className="rounded-2xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  New
                </button>

                <button
                  onClick={handleSaveStory}
                  disabled={saving}
                  className="rounded-2xl bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:bg-slate-400"
                >
                  {saving ? "Saving..." : "Save"}
                </button>

                <button
                  onClick={handleDeleteStory}
                  disabled={!selectedStoryId || saving}
                  className="rounded-2xl border border-rose-200 px-3 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                >
                  Delete
                </button>

                <button
                  onClick={() => setShowAcEditor((current) => !current)}
                  className="rounded-2xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  {showAcEditor ? "Hide AC Editor" : "Edit ACs"}
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Saved Stories
                  </label>
                  <select
                    value={selectedStoryId ?? ""}
                    onChange={(event) => handleSelectStory(Number(event.target.value))}
                    className="w-full rounded-2xl border border-slate-200 px-4 py-2.5 outline-none transition focus:border-slate-400"
                  >
                    <option value="">Select a saved story</option>
                    {stories.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.title}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">Jira ID</label>
                  <input
                    value={story.jiraId}
                    onChange={(event) => updateStoryField("jiraId", event.target.value)}
                    className="w-full rounded-2xl border border-slate-200 px-4 py-2.5 outline-none transition focus:border-slate-400"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">Title</label>
                  <input
                    value={story.title}
                    onChange={(event) => updateStoryField("title", event.target.value)}
                    className="w-full rounded-2xl border border-slate-200 px-4 py-2.5 outline-none transition focus:border-slate-400"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Description
                  </label>
                  <textarea
                    value={story.description}
                    onChange={(event) => updateStoryField("description", event.target.value)}
                    rows={4}
                    className="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-slate-400"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Acceptance Criteria
                  </label>
                  <textarea
                    value={acceptanceCriteriaText}
                    onChange={(event) => setAcceptanceCriteriaText(event.target.value)}
                    rows={6}
                    className="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-slate-400"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Automation Framework
                  </label>
                  <select
                    value={story.framework}
                    onChange={(event) => updateStoryField("framework", event.target.value as Framework)}
                    className="w-full rounded-2xl border border-slate-200 px-4 py-2.5 outline-none transition focus:border-slate-400"
                  >
                    <option>Playwright</option>
                    <option>Cypress</option>
                    <option>Selenium</option>
                    <option>API Test</option>
                  </select>
                </div>

                <button
                  onClick={handleGenerate}
                  disabled={loading || bootstrapping}
                  className="w-full rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                >
                  {loading ? "Generating via backend..." : "Generate Test Artifacts"}
                </button>
              </div>
            </Section>

            <Section
              title="Coverage Snapshot"
              subtitle="Acceptance criteria coverage from generated tests"
            >
              <div className="space-y-3 text-sm text-slate-700">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>Total ACs:</strong> {coverage?.totalAcceptanceCriteria ?? stats.acceptanceCriteriaCount}
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>Covered ACs:</strong> {coverage?.coveredAcceptanceCriteria ?? 0}
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>Coverage %:</strong> {coverage?.coveragePercent ?? 0}%
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>Uncovered ACs:</strong>{" "}
                  {coverage?.uncoveredAcceptanceCriteria?.length
                    ? coverage.uncoveredAcceptanceCriteria.join(", ")
                    : "None"}
                </div>
              </div>
            </Section>

            <Section
              title="Traceability Snapshot"
              subtitle="How the platform links requirements to generated assets"
            >
              <div className="space-y-3 text-sm text-slate-700">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>Story:</strong> {story.jiraId || "N/A"}
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>Acceptance Criteria:</strong> {stats.acceptanceCriteriaCount}
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>Artifacts Generated:</strong> {stats.artifactsGenerated}
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>Automation Target:</strong> {story.framework}
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>Saved Stories:</strong> {stories.length}
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>Last Run:</strong> {generatedAt || "Not generated yet"}
                </div>
              </div>
            </Section>
          </div>

          <div className="space-y-6">
            <div className="rounded-3xl border border-slate-200 bg-white p-2 shadow-sm">
              <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`rounded-2xl px-4 py-3 text-sm font-medium transition ${
                      activeTab === tab.id ? "bg-slate-950 text-white" : "text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {activeTab === "story" && (
              <Section
                title="Normalized Story Payload"
                subtitle="The API-ready representation sent to the backend"
              >
                <div className="rounded-3xl bg-slate-950 p-5 text-sm text-slate-100">
                  <pre className="overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(
                      {
                        ...story,
                        acceptanceCriteria: textToCriteria(acceptanceCriteriaText),
                      },
                      null,
                      2,
                    )}
                  </pre>
                </div>
              </Section>
            )}

            {activeTab === "intent" && (
              <Section
                title="Intent Model"
                subtitle="Response from the backend intent generation service"
              >
                {intent ? (
                  <div className="rounded-3xl bg-slate-950 p-5 text-sm text-slate-100">
                    <pre className="overflow-x-auto whitespace-pre-wrap">
                      {JSON.stringify(intent, null, 2)}
                    </pre>
                  </div>
                ) : (
                  <div className="rounded-3xl bg-slate-50 p-8 text-center text-slate-500">
                    Generate artifacts to view the intent model.
                  </div>
                )}
              </Section>
            )}

            {activeTab === "tests" && (
              <Section
                title="Generated Test Cases"
                subtitle="Now includes AC mapping, priority, and risk tags"
              >
                {tests.length ? (
                  <div className="space-y-4">
                    {tests.map((test) => (
                      <div key={test.id} className="rounded-3xl border border-slate-200 p-5">
                        <div className="flex flex-wrap items-center gap-3">
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
                        </div>

                        <p className="mt-2 text-sm text-slate-500">{test.rationale}</p>

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
                            <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                              Steps
                            </div>
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
                            <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
                              {test.expectedResult}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-3xl bg-slate-50 p-8 text-center text-slate-500">
                    Generate artifacts to view test cases.
                  </div>
                )}
              </Section>
            )}

            {activeTab === "gherkin" && (
              <Section
                title="Automation Scenarios"
                subtitle="Gherkin returned by the scenario generation endpoint"
              >
                {scenarios.length ? (
                  <div className="space-y-4">
                    {scenarios.map((scenario) => (
                      <div
                        key={scenario.id}
                        className="rounded-3xl bg-slate-950 p-5 text-sm text-slate-100"
                      >
                        <div className="mb-2 flex items-center gap-2">
                          <Badge tone="blue">{scenario.id}</Badge>
                          <span className="text-slate-300">{scenario.title}</span>
                        </div>
                        <pre className="overflow-x-auto whitespace-pre-wrap">
                          {scenario.gherkin}
                        </pre>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-3xl bg-slate-50 p-8 text-center text-slate-500">
                    Generate artifacts to view Gherkin scenarios.
                  </div>
                )}
              </Section>
            )}

            {activeTab === "automation" && (
              <Section
                title="Automation Code Skeleton"
                subtitle="Framework-ready code returned by the automation endpoint"
              >
                {automation.length ? (
                  <div className="space-y-4">
                    {automation.map((artifact) => (
                      <div
                        key={artifact.id}
                        className="rounded-3xl border border-slate-200 overflow-hidden"
                      >
                        <div className="border-b border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700">
                          {artifact.file_name}
                        </div>
                        <div className="bg-slate-950 p-5 text-sm text-slate-100">
                          <pre className="overflow-x-auto whitespace-pre-wrap">
                            {artifact.content}
                          </pre>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-3xl bg-slate-50 p-8 text-center text-slate-500">
                    Generate artifacts to view automation code.
                  </div>
                )}
              </Section>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}