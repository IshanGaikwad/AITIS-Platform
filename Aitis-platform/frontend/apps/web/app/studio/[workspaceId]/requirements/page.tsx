"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Plus, Download, Search, FileText, ExternalLink, Pencil, Trash2, AlertCircle, ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
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
  createStory,
  updateStory,
  deleteStory,
  importJiraIssue,
  getJiraIssue,
  searchJiraIssues,
} from "@/lib/api";
import type { SavedStory, JiraIssue } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

// Backend RequirementStatus enum values → display metadata. "approved" === fully
// analyzed (the gate for test-case generation).
const STATUS_META: Record<string, { label: string; tone: "slate" | "amber" | "green" | "rose" }> = {
  draft: { label: "Draft", tone: "slate" },
  reviewed: { label: "In Review", tone: "amber" },
  approved: { label: "Analyzed", tone: "green" },
  deprecated: { label: "Deprecated", tone: "rose" },
};
const STATUS_TABS = ["All", "draft", "reviewed", "approved", "deprecated"] as const;
type StatusTab = (typeof STATUS_TABS)[number];

const normStatus = (s?: string | null) => (s ?? "draft").toLowerCase();

const PRIORITY_OPTIONS = ["High", "Medium", "Low"] as const;
const PRIORITY_TONE: Record<string, "rose" | "amber" | "blue"> = {
  High: "rose",
  Medium: "amber",
  Low: "blue",
};

interface StoryForm {
  jiraId: string;
  title: string;
  description: string;
  acceptanceCriteria: string;
  priority: string;
}

const EMPTY_FORM: StoryForm = {
  jiraId: "",
  title: "",
  description: "",
  acceptanceCriteria: "",
  priority: "Medium",
};

export default function RequirementsPage() {
  const params = useParams();
  const workspaceId = params.workspaceId as string;
  const { user } = useAuth();
  const { toast } = useToast();

  const [stories, setStories] = useState<SavedStory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [activeStatus, setActiveStatus] = useState<StatusTab>("All");

  const [addOpen, setAddOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<SavedStory | null>(null);
  const [form, setForm] = useState<StoryForm>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [jiraOpen, setJiraOpen] = useState(false);
  const [jiraKey, setJiraKey] = useState("");
  const [jiraJql, setJiraJql] = useState("issuetype = Story ORDER BY updated DESC");
  const [jiraResults, setJiraResults] = useState<JiraIssue[]>([]);
  const [jiraSearchLoading, setJiraSearchLoading] = useState(false);
  const [jiraImportingKey, setJiraImportingKey] = useState<string | null>(null);
  const [jiraNextPageToken, setJiraNextPageToken] = useState<string | null>(null);
  const [jiraError, setJiraError] = useState<string | null>(null);
  const [importedCount, setImportedCount] = useState(0);

  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [markingAnalyzedId, setMarkingAnalyzedId] = useState<number | null>(null);

  const fetchStories = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getStories();
      setStories(data);
    } catch {
      setError("Failed to load requirements.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStories();
  }, [fetchStories]);

  const filtered = stories.filter((s) => {
    const matchStatus = activeStatus === "All" || normStatus(s.status) === activeStatus;
    const q = search.toLowerCase();
    const matchSearch =
      s.title.toLowerCase().includes(q) ||
      (s.jiraId ?? "").toLowerCase().includes(q);
    return matchStatus && matchSearch;
  });

  const openAdd = () => {
    setEditTarget(null);
    setForm(EMPTY_FORM);
    setFormError(null);
    setAddOpen(true);
  };

  const openEdit = (story: SavedStory) => {
    setEditTarget(story);
    setForm({
      jiraId: story.jiraId ?? "",
      title: story.title,
      description: story.description ?? "",
      acceptanceCriteria: (story.acceptanceCriteria ?? []).join("\n"),
      priority: story.priority ?? "Medium",
    });
    setFormError(null);
    setAddOpen(true);
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
      const payload = {
        jiraId: form.jiraId.trim(),
        title: form.title.trim(),
        description: form.description.trim(),
        acceptanceCriteria: form.acceptanceCriteria
          .split("\n")
          .map((l) => l.trim())
          .filter(Boolean),
        framework: "Playwright" as const,
        priority: form.priority,
        status: editTarget?.status,
        type: editTarget?.type,
      };
      if (editTarget) {
        const updated = await updateStory(editTarget.id, payload);
        setStories((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
        toast({ title: "Requirement updated", variant: "success" });
      } else {
        const created = await createStory(payload, workspaceId);
        setStories((prev) => [created, ...prev]);
        toast({ title: "Requirement added", variant: "success" });
      }
      setAddOpen(false);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Operation failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleMarkAnalyzed = async (id: number) => {
    setMarkingAnalyzedId(id);
    try {
      const payload = { status: "approved" };
      const updated = await updateStory(id, payload);
      setStories((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
      toast({ title: "Requirement marked as Analyzed", variant: "success" });
    } catch {
      toast({ title: "Failed to update requirement status", variant: "destructive" });
    } finally {
      setMarkingAnalyzedId(null);
    }
  };

  const handleDelete = async (id: number) => {
    setDeleting(true);
    try {
      await deleteStory(id);
      setStories((prev) => prev.filter((s) => s.id !== id));
      setDeleteConfirmId(null);
      toast({ title: "Requirement deleted" });
    } catch {
      toast({ title: "Failed to delete requirement", variant: "destructive" });
    } finally {
      setDeleting(false);
    }
  };

  const openJira = () => {
    setJiraKey("");
    setJiraResults([]);
    setJiraNextPageToken(null);
    setJiraError(null);
    setJiraOpen(true);
  };

  const handleFetchJiraIssue = async () => {
    if (!jiraKey.trim()) {
      setJiraError("Enter a Jira issue key.");
      return;
    }
    setJiraSearchLoading(true);
    setJiraError(null);
    try {
      const issue = await getJiraIssue(jiraKey.trim());
      setJiraResults([issue]);
      setJiraNextPageToken(null);
    } catch (err) {
      setJiraError(err instanceof Error ? err.message : "Failed to fetch Jira issue.");
    } finally {
      setJiraSearchLoading(false);
    }
  };

  const handleSearchJira = async (resetResults: boolean = true) => {
    if (!jiraJql.trim()) {
      setJiraError("Enter a JQL query.");
      return;
    }
    setJiraSearchLoading(true);
    setJiraError(null);
    try {
      const result = await searchJiraIssues(
        jiraJql,
        resetResults ? undefined : jiraNextPageToken ?? undefined,
      );
      setJiraResults((current) =>
        resetResults ? result.issues ?? [] : [...current, ...(result.issues ?? [])],
      );
      setJiraNextPageToken(result.nextPageToken ?? null);
    } catch (err) {
      setJiraError(err instanceof Error ? err.message : "Failed to search Jira.");
    } finally {
      setJiraSearchLoading(false);
    }
  };

  const handleImportIssue = async (issueKey: string) => {
    setJiraImportingKey(issueKey);
    setJiraError(null);
    try {
      const created = await importJiraIssue(issueKey, workspaceId);
      setStories((prev) => {
        const exists = prev.some((s) => s.id === created.id);
        return exists ? prev.map((s) => (s.id === created.id ? created : s)) : [created, ...prev];
      });
      setImportedCount((c) => c + 1);
      toast({ title: `Imported ${issueKey}`, variant: "success" });
    } catch (err) {
      setJiraError(err instanceof Error ? err.message : "Import failed.");
    } finally {
      setJiraImportingKey(null);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Requirements</h2>
          <p className="text-sm text-slate-500">
            Import user stories from Jira, then head to the Test Case Generator to create tests.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={openJira}>
            <Download className="h-4 w-4" />
            Import from Jira
          </Button>
          <Button size="sm" onClick={openAdd}>
            <Plus className="h-4 w-4" />
            Add Requirement
          </Button>
        </div>
      </div>

      {importedCount > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
          <p className="text-sm text-emerald-800">
            <span className="font-semibold">{importedCount}</span> requirement
            {importedCount > 1 ? "s" : ""} imported. Ready to generate test cases?
          </p>
          <Button size="sm" asChild>
            <Link href={`/studio/${workspaceId}/test-cases`}>
              Go to Test Case Generator
              <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </Button>
        </div>
      )}

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search requirements..."
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
            {status === "All" ? "All" : STATUS_META[status]?.label ?? status}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg border border-slate-100 bg-slate-50" />
          ))}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center py-16 text-center">
          <AlertCircle className="mb-3 h-8 w-8 text-rose-300" />
          <p className="text-sm text-slate-500">{error}</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={fetchStories}>Retry</Button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-16 text-center text-slate-500">
          <FileText className="mx-auto mb-3 h-8 w-8 text-slate-300" />
          <p className="text-sm">No requirements found.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((story) => (
            <Card key={story.id} className="transition-shadow hover:shadow-sm">
              <CardContent className="p-4">
                <div className="flex flex-wrap items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex items-center gap-2">
                      <span className="font-mono text-xs text-slate-400">#{story.id}</span>
                      {story.jiraId && (
                        <span className="inline-flex items-center gap-1 text-xs text-blue-600">
                          <ExternalLink className="h-3 w-3" />
                          {story.jiraId}
                        </span>
                      )}
                    </div>
                    <p className="text-sm font-medium text-slate-900">{story.title}</p>
                  </div>
                  <div className="flex shrink-0 flex-wrap items-center gap-2">
                    {story.priority && (
                      <Badge tone={PRIORITY_TONE[story.priority] ?? "slate"}>{story.priority}</Badge>
                    )}
                    <Badge tone={STATUS_META[normStatus(story.status)]?.tone ?? "slate"}>
                      {STATUS_META[normStatus(story.status)]?.label ?? story.status}
                    </Badge>
                    <span className="text-xs text-slate-400">Coverage: —</span>
                    {normStatus(story.status) !== "approved" && deleteConfirmId !== story.id && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7"
                        onClick={() => handleMarkAnalyzed(story.id)}
                        disabled={markingAnalyzedId === story.id}
                      >
                        {markingAnalyzedId === story.id ? "Marking..." : "Mark Analyzed"}
                      </Button>
                    )}
                    {deleteConfirmId === story.id ? (
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs text-rose-600">Delete?</span>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 border-rose-200 text-rose-600"
                          onClick={() => handleDelete(story.id)}
                          disabled={deleting}
                        >
                          Confirm
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7"
                          onClick={() => setDeleteConfirmId(null)}
                          disabled={deleting}
                        >
                          Cancel
                        </Button>
                      </div>
                    ) : (
                      <>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => openEdit(story)}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-rose-400 hover:text-rose-600"
                          onClick={() => setDeleteConfirmId(story.id)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Add / Edit Modal */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editTarget ? "Edit Requirement" : "Add Requirement"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Jira ID</label>
              <Input
                value={form.jiraId}
                onChange={(e) => setForm((f) => ({ ...f, jiraId: e.target.value }))}
                placeholder="e.g. AUTH-201"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">
                Title <span className="text-rose-500">*</span>
              </label>
              <Input
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                placeholder="Requirement title"
                required
              />
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
              <label className="text-sm font-medium text-slate-700">Acceptance Criteria</label>
              <Textarea
                value={form.acceptanceCriteria}
                onChange={(e) => setForm((f) => ({ ...f, acceptanceCriteria: e.target.value }))}
                rows={3}
                placeholder="One criterion per line..."
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Priority</label>
              <select
                value={form.priority}
                onChange={(e) => setForm((f) => ({ ...f, priority: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400"
              >
                {PRIORITY_OPTIONS.map((p) => <option key={p}>{p}</option>)}
              </select>
            </div>
            {formError && <p className="text-sm text-rose-600">{formError}</p>}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setAddOpen(false)} disabled={submitting}>
                Cancel
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Saving..." : editTarget ? "Save Changes" : "Add Requirement"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Jira Import Modal — fetch by key or search with JQL, then import */}
      <Dialog open={jiraOpen} onOpenChange={setJiraOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Import from Jira</DialogTitle>
          </DialogHeader>
          <div className="space-y-5 pt-2">
            {/* Fetch a single issue by key */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Fetch by issue key</label>
              <div className="flex gap-2">
                <Input
                  value={jiraKey}
                  onChange={(e) => setJiraKey(e.target.value)}
                  placeholder="e.g. AUTH-201"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleFetchJiraIssue();
                    }
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleFetchJiraIssue}
                  disabled={jiraSearchLoading}
                >
                  Fetch
                </Button>
              </div>
            </div>

            {/* Search with JQL */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Search with JQL</label>
              <Textarea
                value={jiraJql}
                onChange={(e) => setJiraJql(e.target.value)}
                rows={2}
                placeholder="issuetype = Story ORDER BY updated DESC"
              />
              <div className="flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  onClick={() => handleSearchJira(true)}
                  disabled={jiraSearchLoading}
                >
                  {jiraSearchLoading ? "Searching..." : "Search Jira"}
                </Button>
                {jiraNextPageToken && (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => handleSearchJira(false)}
                    disabled={jiraSearchLoading}
                  >
                    Load more
                  </Button>
                )}
              </div>
            </div>

            {jiraError && <p className="text-sm text-rose-600">{jiraError}</p>}

            {/* Results */}
            <div className="max-h-72 space-y-3 overflow-y-auto">
              {jiraResults.length === 0 ? (
                <div className="rounded-lg bg-slate-50 p-4 text-center text-sm text-slate-500">
                  No results yet. Fetch by key or run a JQL search.
                </div>
              ) : (
                jiraResults.map((issue) => (
                  <div key={issue.key} className="rounded-lg border border-slate-200 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone="blue">{issue.key}</Badge>
                      {issue.fields.issuetype?.name && (
                        <Badge tone="green">{issue.fields.issuetype.name}</Badge>
                      )}
                      {issue.fields.status?.name && (
                        <Badge tone="amber">{issue.fields.status.name}</Badge>
                      )}
                      {issue.fields.priority?.name && (
                        <Badge tone="rose">{issue.fields.priority.name}</Badge>
                      )}
                    </div>
                    <p className="mt-2 text-sm font-medium text-slate-900">
                      {issue.fields.summary || "(No summary)"}
                    </p>
                    <Button
                      size="sm"
                      className="mt-3"
                      onClick={() => handleImportIssue(issue.key)}
                      disabled={jiraImportingKey === issue.key}
                    >
                      {jiraImportingKey === issue.key ? "Importing..." : "Import"}
                    </Button>
                  </div>
                ))
              )}
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setJiraOpen(false)}>
              Done
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
