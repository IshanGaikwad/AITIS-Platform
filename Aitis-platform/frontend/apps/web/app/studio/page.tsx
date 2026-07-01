"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Plus, FolderOpen, AlertCircle } from "lucide-react";
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
import { useAuth } from "@/lib/auth";
import { useToast } from "@/components/ui/use-toast";
import { getWorkspaces, createWorkspace, getProjects } from "@/lib/api";
import type { Workspace } from "@/lib/types";
import { ProtectedRoute } from "@/components/ProtectedRoute";

function generateKey(name: string): string {
  return name
    .split(/\s+/)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("")
    .slice(0, 10);
}

function LoadingSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="rounded-xl border border-slate-200 p-5 animate-pulse">
          <div className="h-4 w-2/3 rounded bg-slate-200 mb-3" />
          <div className="h-3 w-1/3 rounded bg-slate-100 mb-4" />
          <div className="space-y-2">
            <div className="h-3 w-full rounded bg-slate-100" />
            <div className="h-3 w-full rounded bg-slate-100" />
            <div className="h-3 w-3/4 rounded bg-slate-100" />
          </div>
        </div>
      ))}
    </div>
  );
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="mb-4 rounded-full bg-rose-50 p-4">
        <AlertCircle className="h-8 w-8 text-rose-400" />
      </div>
      <h3 className="mb-1 text-base font-semibold text-slate-900">Failed to load workspaces</h3>
      <p className="mb-4 text-sm text-slate-500">Something went wrong while fetching your workspaces.</p>
      <Button size="sm" variant="outline" onClick={onRetry}>Try again</Button>
    </div>
  );
}

function NoProjectState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="mb-4 rounded-full bg-slate-100 p-4">
        <FolderOpen className="h-8 w-8 text-slate-400" />
      </div>
      <h3 className="mb-1 text-base font-semibold text-slate-900">No project selected</h3>
      <p className="text-sm text-slate-500">
        Create or select a project from the switcher (top-left) to add workspaces.
      </p>
    </div>
  );
}

function EmptyState({ onCreateClick }: { onCreateClick: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="mb-4 rounded-full bg-slate-100 p-4">
        <FolderOpen className="h-8 w-8 text-slate-400" />
      </div>
      <h3 className="mb-1 text-base font-semibold text-slate-900">No workspaces yet</h3>
      <p className="mb-4 text-sm text-slate-500">Get started by creating your first workspace in this project.</p>
      <Button size="sm" onClick={onCreateClick}>
        <Plus className="h-4 w-4" />
        Create your first workspace
      </Button>
    </div>
  );
}

function WorkspaceCard({ workspace, onClick }: { workspace: Workspace; onClick: () => void }) {
  return (
    <Card className="cursor-pointer transition-shadow hover:shadow-md" onClick={onClick}>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate font-semibold text-slate-900">{workspace.name}</p>
            <p className="mt-0.5 truncate font-mono text-xs text-slate-500">{workspace.key}</p>
          </div>
          <Badge tone={workspace.status === "active" ? "green" : "slate"}>{workspace.status}</Badge>
        </div>
        {workspace.description && (
          <p className="line-clamp-2 text-xs text-slate-500">{workspace.description}</p>
        )}
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
          <div><span className="text-slate-400">Health: </span><span className="font-medium text-slate-700">—</span></div>
          <div><span className="text-slate-400">Pass Rate: </span><span className="font-medium text-slate-700">N/A</span></div>
          <div><span className="text-slate-400">Defects: </span><span className="font-medium text-slate-700">N/A</span></div>
          <div>
            <span className="text-slate-400">Created: </span>
            <span className="font-medium text-slate-700">
              {new Date(workspace.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function StudioPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { toast } = useToast();

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [projectName, setProjectName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [formName, setFormName] = useState("");
  const [formKey, setFormKey] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchWorkspaces = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (!user?.project_id) {
        setLoading(false);
        return;
      }
      const data = await getWorkspaces(user.project_id);
      setWorkspaces(data);
    } catch {
      setError("Failed to load workspaces.");
    } finally {
      setLoading(false);
    }
  }, [user?.project_id]);

  useEffect(() => {
    fetchWorkspaces();
  }, [fetchWorkspaces]);

  // Resolve the active project's name for context
  useEffect(() => {
    if (!user?.organization_id || !user?.project_id) {
      setProjectName(null);
      return;
    }
    let cancelled = false;
    getProjects(user.organization_id)
      .then((projects) => {
        if (cancelled) return;
        const active = projects.find((p) => p.id === user.project_id);
        setProjectName(active?.name ?? null);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [user?.organization_id, user?.project_id]);

  const handleNameChange = (name: string) => {
    setFormName(name);
    setFormKey(generateKey(name));
  };

  const openModal = () => {
    setFormName("");
    setFormKey("");
    setFormDescription("");
    setFormError(null);
    setModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) {
      setFormError("Workspace name is required.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      if (!user?.project_id) {
        setFormError("No active project. Create or select a project from the switcher first.");
        setSubmitting(false);
        return;
      }
      const created = await createWorkspace(user.project_id, {
        name: formName.trim(),
        key: formKey.trim() || generateKey(formName),
        description: formDescription.trim() || undefined,
      });
      setWorkspaces((prev) => [created, ...prev]);
      setModalOpen(false);
      toast({ title: "Workspace created", variant: "success" });
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create workspace.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ProtectedRoute>
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Studio</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            {projectName ? (
              <>Workspaces in <span className="font-medium text-slate-700">{projectName}</span></>
            ) : (
              "Select or create a project from the switcher to begin"
            )}
          </p>
        </div>
        <Button size="sm" onClick={openModal} disabled={!user?.project_id}>
          <Plus className="h-4 w-4" />
          Create Workspace
        </Button>
      </div>

      {loading ? (
        <LoadingSkeleton />
      ) : !user?.project_id ? (
        <NoProjectState />
      ) : error ? (
        <ErrorState onRetry={fetchWorkspaces} />
      ) : workspaces.length === 0 ? (
        <EmptyState onCreateClick={openModal} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {workspaces.map((workspace) => (
            <WorkspaceCard
              key={workspace.id}
              workspace={workspace}
              onClick={() => router.push(`/studio/${workspace.id}`)}
            />
          ))}
        </div>
      )}

      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Workspace</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">
                Workspace Name <span className="text-rose-500">*</span>
              </label>
              <Input
                value={formName}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder="e.g. Customer Portal QA"
                required
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Key</label>
              <Input
                value={formKey}
                onChange={(e) => setFormKey(e.target.value.toUpperCase().slice(0, 10))}
                placeholder="e.g. CPQ"
                maxLength={10}
              />
              <p className="text-xs text-slate-400">Auto-generated from name. Max 10 characters.</p>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-700">Description</label>
              <Textarea
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                placeholder="Optional description..."
                rows={3}
              />
            </div>
            {formError && <p className="text-sm text-rose-600">{formError}</p>}
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setModalOpen(false)}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting ? "Creating..." : "Create Workspace"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
    </ProtectedRoute>
  );
}
