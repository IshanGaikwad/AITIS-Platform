"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { Plus, Search, FlaskConical, Pencil, Trash2, AlertCircle } from "lucide-react";
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
import { getTestSuites, getTestCases, createTestCase, updateTestCase, deleteTestCase } from "@/lib/api";
import type { TestSuite, TestCaseDB } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

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

interface CaseForm {
  title: string;
  type: string;
  priority: string;
  description: string;
  preconditions: string;
}

const EMPTY_FORM: CaseForm = {
  title: "",
  type: "functional",
  priority: "medium",
  description: "",
  preconditions: "",
};

export default function TestCasesPage() {
  const params = useParams();
  const projectId = params.workspaceId as string;
  const { user } = useAuth();
  const { toast } = useToast();

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

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const fetchedSuites = await getTestSuites(projectId);
      setSuites(fetchedSuites);
      const allCases = await Promise.all(
        fetchedSuites.map((s) => getTestCases(s.id))
      );
      setCases(allCases.flat());
    } catch {
      setError("Failed to load test cases.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filtered = cases.filter((tc) => {
    const matchStatus = activeStatus === "All" || tc.status === activeStatus;
    const q = search.toLowerCase();
    const matchSearch =
      tc.title.toLowerCase().includes(q) ||
      tc.id.toLowerCase().includes(q);
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
        preconditions: form.preconditions
          .split("\n")
          .map((l) => l.trim())
          .filter(Boolean),
      };

      if (editTarget) {
        const updated = await updateTestCase(editTarget.test_suite_id, editTarget.id, payload);
        setCases((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
        toast({ title: "Test case updated", variant: "success" });
      } else {
        if (suites.length === 0) {
          setFormError("No test suites exist. Create a suite first.");
          setSubmitting(false);
          return;
        }
        const created = await createTestCase(suites[0].id, payload);
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

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-900">Test Cases</h2>
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
          <Button variant="outline" size="sm" className="mt-3" onClick={fetchData}>Retry</Button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-16 text-center text-slate-500">
          <FlaskConical className="mx-auto mb-3 h-8 w-8 text-slate-300" />
          <p className="text-sm">No test cases found.</p>
        </div>
      ) : (
        <div className="space-y-1">
          {/* Column headers */}
          <div className="flex items-center gap-3 border-b border-slate-100 px-4 py-2 text-xs font-medium uppercase tracking-wide text-slate-400">
            <span className="flex-1">Title</span>
            <span className="hidden w-24 sm:block">Type</span>
            <span className="hidden w-16 md:block">Priority</span>
            <span className="hidden w-24 lg:block">Status</span>
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
              <div className="flex w-20 justify-end gap-1">
                {deleteConfirmId === tc.id ? (
                  <div className="flex items-center gap-1">
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 border-rose-200 text-rose-600 text-xs px-2"
                      onClick={() => handleDelete(tc)}
                      disabled={deleting}
                    >
                      Yes
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 text-xs px-2"
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
                      className="h-7 w-7"
                      onClick={() => openEdit(tc)}
                    >
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
                  {TYPE_OPTIONS.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-slate-700">Priority</label>
                <select
                  value={form.priority}
                  onChange={(e) => setForm((f) => ({ ...f, priority: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400"
                >
                  {PRIORITY_OPTIONS.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
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
    </div>
  );
}
