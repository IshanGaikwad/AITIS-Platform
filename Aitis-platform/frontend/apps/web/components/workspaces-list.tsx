"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Folder, Archive, Edit2, Trash2, Settings } from "lucide-react";
import { useForm } from "react-hook-form";

interface Workspace {
  id: string;
  name: string;
  key: string;
  description?: string;
  status: "active" | "archived";
  owner_id?: string;
  tags?: string[];
  created_at: string;
  project_id: string;
  organization_id: string;
}

interface WorkspaceFormData {
  name: string;
  key: string;
  description?: string;
}

// Client-side: use a relative base so Next.js rewrites proxy /api/* to the backend
// (avoids CORS and keeps the port in next.config.mjs as the single source of truth).
const API_BASE = "/api";

async function fetchWorkspaces(projectId: string): Promise<Workspace[]> {
  const response = await fetch(`${API_BASE}/workspaces?project_id=${projectId}`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("aitis_access_token")}`,
    },
  });
  if (!response.ok) throw new Error("Failed to fetch workspaces");
  return response.json();
}

async function createWorkspace(data: WorkspaceFormData, projectId: string): Promise<Workspace> {
  const response = await fetch(`${API_BASE}/workspaces`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("aitis_access_token")}`,
    },
    body: JSON.stringify({
      ...data,
      project_id: projectId,
      status: "active",
      settings: {},
    }),
  });
  if (!response.ok) throw new Error("Failed to create workspace");
  return response.json();
}

async function deleteWorkspace(workspaceId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/workspaces/${workspaceId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${localStorage.getItem("aitis_access_token")}`,
    },
  });
  if (!response.ok) throw new Error("Failed to delete workspace");
}

export function WorkspacesList({ projectId }: { projectId: string }) {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset, formState: { errors } } = useForm<WorkspaceFormData>();

  // Fetch workspaces
  const { data: workspaces = [], isLoading } = useQuery({
    queryKey: ["workspaces", projectId],
    queryFn: () => fetchWorkspaces(projectId),
  });

  // Create workspace mutation
  const createMutation = useMutation({
    mutationFn: (data: WorkspaceFormData) => createWorkspace(data, projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspaces", projectId] });
      setIsCreateOpen(false);
      reset();
    },
  });

  // Delete workspace mutation
  const deleteMutation = useMutation({
    mutationFn: deleteWorkspace,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspaces", projectId] });
    },
  });

  const handleCreate = (data: WorkspaceFormData) => {
    createMutation.mutate(data);
  };

  const activeWorkspaces = workspaces.filter(p => p.status === "active");
  const archivedWorkspaces = workspaces.filter(p => p.status === "archived");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Workspaces</h1>
          <p className="text-slate-600 mt-1">Manage your test automation workspaces</p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          New Workspace
        </Button>
      </div>

      {/* Active Workspaces */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Active Workspaces</h2>
        {isLoading ? (
          <div className="text-center py-8 text-slate-500">Loading workspaces...</div>
        ) : activeWorkspaces.length === 0 ? (
          <Card>
            <CardContent className="flex items-center justify-center py-16">
              <div className="text-center">
                <Folder className="h-12 w-12 mx-auto text-slate-400 mb-4" />
                <p className="text-slate-600 font-medium">No workspaces yet</p>
                <p className="text-slate-500 text-sm">Create your first workspace to get started</p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeWorkspaces.map((workspace) => (
              <Link key={workspace.id} href={`/workspaces/${workspace.id}`}>
                <Card className="hover:shadow-lg transition-shadow h-full cursor-pointer">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <CardTitle className="text-lg">{workspace.name}</CardTitle>
                        <CardDescription className="text-xs font-mono mt-1">{workspace.key}</CardDescription>
                      </div>
                      <Badge tone="green">Active</Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {workspace.description && (
                      <p className="text-sm text-slate-600 line-clamp-2">{workspace.description}</p>
                    )}
                    {workspace.tags && workspace.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {workspace.tags.slice(0, 3).map((tag) => (
                          <Badge key={tag} tone="slate" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                        {workspace.tags.length > 3 && (
                          <Badge tone="slate" className="text-xs">
                            +{workspace.tags.length - 3}
                          </Badge>
                        )}
                      </div>
                    )}
                    <div className="flex gap-2 pt-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.preventDefault();
                          // TODO: Archive workspace
                        }}
                      >
                        <Archive className="h-3 w-3" />
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.preventDefault();
                          deleteMutation.mutate(workspace.id);
                        }}
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Archived Workspaces */}
      {archivedWorkspaces.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Archived Workspaces</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {archivedWorkspaces.map((workspace) => (
              <Card key={workspace.id} className="opacity-60">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-lg">{workspace.name}</CardTitle>
                      <CardDescription className="text-xs font-mono mt-1">{workspace.key}</CardDescription>
                    </div>
                    <Badge tone="slate">Archived</Badge>
                  </div>
                </CardHeader>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Create Workspace Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Workspace</DialogTitle>
            <DialogDescription>
              Set up a new workspace to organize your test automation work.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(handleCreate)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Workspace Name</Label>
              <Input
                id="name"
                placeholder="e.g., E-Commerce Platform"
                {...register("name", { required: "Workspace name is required" })}
              />
              {errors.name && <p className="text-xs text-red-500">{errors.name.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="key">Workspace Key</Label>
              <Input
                id="key"
                placeholder="e.g., ECOM"
                maxLength={10}
                {...register("key", { required: "Workspace key is required" })}
              />
              {errors.key && <p className="text-xs text-red-500">{errors.key.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Textarea
                id="description"
                placeholder="Describe your workspace..."
                {...register("description")}
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Creating..." : "Create Workspace"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
