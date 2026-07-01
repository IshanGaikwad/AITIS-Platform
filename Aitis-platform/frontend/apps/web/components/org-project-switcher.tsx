"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  getOrganizations,
  getProjects,
  getWorkspaces,
  createProject,
  createWorkspace,
} from "@/lib/api";
import type { Organization, Project, Workspace } from "@/lib/types";
import {
  Building2,
  ChevronsUpDown,
  Check,
  Loader2,
  Plus,
  FolderTree,
  Box,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { cn } from "@/lib/utils";

interface OrgProjectSwitcherProps {
  className?: string;
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function OrgProjectSwitcher({ className }: OrgProjectSwitcherProps) {
  const router = useRouter();
  const { toast } = useToast();
  const { user, selectProjectAndRefresh } = useAuth();

  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [switching, setSwitching] = useState(false);

  const [createProjectOpen, setCreateProjectOpen] = useState(false);
  const [createWorkspaceOpen, setCreateWorkspaceOpen] = useState(false);

  const currentOrgId = user?.organization_id;
  const currentProjectId = user?.project_id;
  const currentOrg = organizations.find((o) => o.id === currentOrgId);
  const currentProject = projects.find((p) => p.id === currentProjectId);

  /* Load organizations on mount */
  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    getOrganizations()
      .then((orgs) => !cancelled && setOrganizations(orgs))
      .catch(() => {})
      .finally(() => !cancelled && setIsLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  /* Load projects when org changes */
  const loadProjects = useCallback(() => {
    if (!currentOrgId) {
      setProjects([]);
      return;
    }
    getProjects(currentOrgId)
      .then(setProjects)
      .catch(() => setProjects([]));
  }, [currentOrgId]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  /* Load workspaces of the active project */
  const loadWorkspaces = useCallback(() => {
    if (!currentProjectId) {
      setWorkspaces([]);
      return;
    }
    getWorkspaces(currentProjectId)
      .then(setWorkspaces)
      .catch(() => setWorkspaces([]));
  }, [currentProjectId]);

  useEffect(() => {
    loadWorkspaces();
  }, [loadWorkspaces]);

  const handleSwitchProject = useCallback(
    async (projectId: string) => {
      if (projectId === currentProjectId) return;
      setSwitching(true);
      try {
        await selectProjectAndRefresh(projectId);
      } catch (err: unknown) {
        toast({
          title: "Couldn't switch project",
          description: err instanceof Error ? err.message : "Please try again.",
          variant: "destructive",
        });
      } finally {
        setSwitching(false);
      }
    },
    [currentProjectId, selectProjectAndRefresh, toast]
  );

  if (isLoading) {
    return (
      <div className={cn("flex items-center gap-2 px-2 py-1.5", className)}>
        <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
        <span className="text-xs text-slate-400">Loading...</span>
      </div>
    );
  }

  if (!currentOrg) {
    return null;
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            className={cn(
              "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-slate-100",
              className
            )}
            disabled={switching}
          >
            <div className="flex h-5 w-5 items-center justify-center rounded bg-slate-200 text-[10px] font-bold text-slate-600">
              {currentOrg.name.charAt(0).toUpperCase()}
            </div>
            <div className="flex flex-col items-start text-left">
              <span className="text-xs font-medium text-slate-700 leading-tight truncate max-w-[120px]">
                {currentProject?.name ?? currentOrg.name}
              </span>
              <span className="text-[10px] text-slate-400 leading-tight truncate max-w-[120px]">
                {currentProject ? currentOrg.name : "Select a project"}
              </span>
            </div>
            <ChevronsUpDown className="h-3.5 w-3.5 text-slate-400 ml-auto shrink-0" />
          </button>
        </DropdownMenuTrigger>

        <DropdownMenuContent align="start" className="w-72">
          {/* Organization */}
          <DropdownMenuLabel className="text-xs text-slate-400">Organization</DropdownMenuLabel>
          <DropdownMenuItem className="cursor-default" disabled>
            <Building2 className="mr-2 h-4 w-4 text-slate-500" />
            <span className="flex-1 truncate">{currentOrg.name}</span>
          </DropdownMenuItem>

          {/* Projects */}
          <DropdownMenuSeparator />
          <DropdownMenuLabel className="text-xs text-slate-400">Projects</DropdownMenuLabel>
          {projects.length === 0 && (
            <p className="px-2 py-1.5 text-xs text-slate-400">No projects yet.</p>
          )}
          {projects.map((p) => (
            <DropdownMenuItem
              key={p.id}
              className={cn("cursor-pointer", p.id === currentProjectId && "bg-slate-50")}
              onClick={() => handleSwitchProject(p.id)}
              disabled={switching}
            >
              <FolderTree className="mr-2 h-4 w-4 text-slate-500" />
              <span className="flex-1 truncate">{p.name}</span>
              <Check
                className={cn("h-4 w-4 text-slate-500", p.id !== currentProjectId && "invisible")}
              />
            </DropdownMenuItem>
          ))}
          <DropdownMenuItem
            className="cursor-pointer text-slate-600"
            onSelect={(e) => {
              e.preventDefault();
              setCreateProjectOpen(true);
            }}
          >
            <Plus className="mr-2 h-4 w-4" />
            Create project
          </DropdownMenuItem>

          {/* Workspaces under the active project */}
          <DropdownMenuSeparator />
          <DropdownMenuLabel className="text-xs text-slate-400">
            {currentProject ? `Workspaces in ${currentProject.name}` : "Workspaces"}
          </DropdownMenuLabel>
          {!currentProject && (
            <p className="px-2 py-1.5 text-xs text-slate-400">Select a project first.</p>
          )}
          {currentProject && workspaces.length === 0 && (
            <p className="px-2 py-1.5 text-xs text-slate-400">No workspaces yet.</p>
          )}
          {currentProject &&
            workspaces.map((w) => (
              <DropdownMenuItem
                key={w.id}
                className="cursor-pointer"
                onClick={() => router.push(`/workspaces/${w.id}`)}
              >
                <Box className="mr-2 h-4 w-4 text-slate-500" />
                <span className="flex-1 truncate">{w.name}</span>
                <span className="text-[10px] font-mono text-slate-400">{w.key}</span>
              </DropdownMenuItem>
            ))}
          {currentProject && (
            <DropdownMenuItem
              className="cursor-pointer text-slate-600"
              onSelect={(e) => {
                e.preventDefault();
                setCreateWorkspaceOpen(true);
              }}
            >
              <Plus className="mr-2 h-4 w-4" />
              Create workspace
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <CreateProjectDialog
        open={createProjectOpen}
        onOpenChange={setCreateProjectOpen}
        orgId={currentOrgId}
        onCreated={async (project) => {
          loadProjects();
          await handleSwitchProject(project.id);
        }}
      />

      <CreateWorkspaceDialog
        open={createWorkspaceOpen}
        onOpenChange={setCreateWorkspaceOpen}
        projectId={currentProjectId}
        onCreated={() => loadWorkspaces()}
      />
    </>
  );
}

/* ── Create Project dialog (mid-level container) ── */
function CreateProjectDialog({
  open,
  onOpenChange,
  orgId,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  orgId?: string;
  onCreated: (project: Project) => void | Promise<void>;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!orgId || !name.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const project = await createProject(orgId, {
        name: name.trim(),
        slug: slugify(name),
        description: description.trim() || undefined,
      });
      onOpenChange(false);
      setName("");
      setDescription("");
      await onCreated(project);
    } catch {
      setError("Could not create project. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create project</DialogTitle>
          <DialogDescription>
            A project groups related workspaces. You can create multiple workspaces inside it.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="project-name">Project name</Label>
            <Input
              id="project-name"
              placeholder="e.g., E-Commerce Platform"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="project-desc">Description (optional)</Label>
            <Input
              id="project-desc"
              placeholder="What is this project about?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          {error && <p className="text-xs text-rose-500">{error}</p>}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting || !name.trim() || !orgId}>
              {submitting ? "Creating..." : "Create project"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ── Create Workspace dialog (leaf, under a project) ── */
function CreateWorkspaceDialog({
  open,
  onOpenChange,
  projectId,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  projectId?: string;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [key, setKey] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId || !name.trim() || !key.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await createWorkspace(projectId, {
        name: name.trim(),
        key: key.trim().toUpperCase(),
        description: description.trim() || undefined,
      });
      onOpenChange(false);
      setName("");
      setKey("");
      setDescription("");
      onCreated();
    } catch {
      setError("Could not create workspace. Check the key is unique and uppercase.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create workspace</DialogTitle>
          <DialogDescription>
            A workspace holds your requirements, test suites, and automation for this project.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="ws-name">Workspace name</Label>
            <Input
              id="ws-name"
              placeholder="e.g., Web Checkout"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ws-key">Key</Label>
            <Input
              id="ws-key"
              placeholder="e.g., WEB"
              maxLength={10}
              value={key}
              onChange={(e) => setKey(e.target.value.toUpperCase())}
            />
            <p className="text-[11px] text-slate-400">Uppercase letters/numbers, starts with a letter.</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="ws-desc">Description (optional)</Label>
            <Input
              id="ws-desc"
              placeholder="What does this workspace cover?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          {error && <p className="text-xs text-rose-500">{error}</p>}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting || !name.trim() || !key.trim() || !projectId}>
              {submitting ? "Creating..." : "Create workspace"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
