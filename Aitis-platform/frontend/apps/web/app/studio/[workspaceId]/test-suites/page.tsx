"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Plus, Layers, Trash2, AlertCircle } from "lucide-react";
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
import { getTestSuites, createTestSuite, deleteTestSuite } from "@/lib/api";
import type { TestSuite } from "@/lib/types";
import { useAuth } from "@/lib/auth";

const SUITE_TYPE_OPTIONS = ["smoke", "regression", "sanity", "e2e", "api"] as const;
type SuiteType = (typeof SUITE_TYPE_OPTIONS)[number];

const TYPE_TONE: Record<SuiteType, "blue" | "slate" | "green" | "amber" | "rose"> = {
  smoke: "blue",
  regression: "slate",
  sanity: "green",
  e2e: "amber",
  api: "rose",
};

interface SuiteForm {
  name: string;
  type: SuiteType;
  description: string;
}

const EMPTY_FORM: SuiteForm = { name: "", type: "smoke", description: "" };

export default function TestSuitesPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.workspaceId as string;
  const { user } = useAuth();
  const { toast } = useToast();

  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<SuiteForm>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchSuites = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTestSuites(projectId);
      setSuites(data);
    } catch {
      setError("Failed to load test suites.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchSuites();
  }, [fetchSuites]);

  const openModal = () => {
    setForm(EMPTY_FORM);
    setFormError(null);
    setModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) {
      setFormError("Suite name is required.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      const created = await createTestSuite({
        project_id: projectId,
        name: form.name.trim(),
        type: form.type,
        description: form.description.trim() || undefined,
      });
      setSuites((prev) => [created, ...prev]);
      setModalOpen(false);
      toast({ title: "Test suite created", variant: "success" });
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create suite.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (suiteId: string) => {
    setDeleting(true);
    try {
      await deleteTestSuite(suiteId);
      setSuites((prev) => prev.filter((s) => s.id !== suiteId));
      setDeleteConfirmId(null);
      toast({ title: "Test suite deleted" });
    } catch {
      toast({ title: "Failed to delete suite", variant: "destructive" });
    } finally {
      setDeleting(false);
    }
  };

  const handleSuiteClick = (suiteId: string) => {
    router.push(`/studio/${projectId}/test-cases?suite=${suiteId}`);
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-900">Test Suites</h2>
        <Button size="sm" onClick={openModal}>
          <Plus className="h-4 w-4" />
          New Suite
        </Button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl border border-slate-200 bg-slate-50" />
          ))}
        </div>
      ) : error ? (
        <div className="flex flex-col items-center py-16 text-center">
          <AlertCircle className="mb-3 h-8 w-8 text-rose-300" />
          <p className="text-sm text-slate-500">{error}</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={fetchSuites}>Retry</Button>
        </div>
      ) : suites.length === 0 ? (
        <div className="py-16 text-center text-slate-500">
          <Layers className="mx-auto mb-3 h-8 w-8 text-slate-300" />
          <p className="text-sm">No test suites yet.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {suites.map((suite) => (
            <Card
              key={suite.id}
              className="cursor-pointer transition-shadow hover:shadow-sm"
              onClick={() => handleSuiteClick(suite.id)}
            >
              <CardContent className="p-4">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex items-center gap-2">
                      <p className="font-medium text-slate-900">{suite.name}</p>
                      <Badge tone={TYPE_TONE[suite.type as SuiteType] ?? "slate"}>
                        {suite.type}
                      </Badge>
                    </div>
                    {suite.description && (
                      <p className="line-clamp-1 text-xs text-slate-500">{suite.description}</p>
                    )}
                    <p className="mt-0.5 text-xs text-slate-400">
                      Created {new Date(suite.created_at).toLocaleDateString()}
                    </p>
                  </div>

                  <div onClick={(e) => e.stopPropagation()}>
                    {deleteConfirmId === suite.id ? (
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-rose-600">Delete this suite?</span>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 border-rose-200 text-rose-600"
                          onClick={() => handleDelete(suite.id)}
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
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-rose-400 hover:text-rose-600"
                        onClick={() => setDeleteConfirmId(suite.id)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Test Suite</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">
                Name <span className="text-rose-500">*</span>
              </label>
              <Input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Smoke Tests"
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Type</label>
              <select
                value={form.type}
                onChange={(e) => setForm((f) => ({ ...f, type: e.target.value as SuiteType }))}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-slate-400"
              >
                {SUITE_TYPE_OPTIONS.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Description</label>
              <Textarea
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                rows={3}
                placeholder="Optional description..."
              />
            </div>
            {formError && <p className="text-sm text-rose-600">{formError}</p>}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setModalOpen(false)} disabled={submitting}>
                Cancel
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Creating..." : "Create Suite"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
