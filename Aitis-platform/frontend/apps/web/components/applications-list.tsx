"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
import { Plus, Globe, Smartphone, Edit2, Trash2, ChevronDown, ChevronUp } from "lucide-react";
import { useForm } from "react-hook-form";

interface Application {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  application_type: "WEB" | "MOBILE_WEB" | "ANDROID" | "IOS" | "HYBRID";
  repository_url?: string;
  metadata_?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface ApplicationFormData {
  name: string;
  application_type: Application["application_type"];
  description?: string;
  repository_url?: string;
}

// Client-side: use a relative base so Next.js rewrites proxy /api/* to the backend
// (avoids CORS and keeps the port in next.config.mjs as the single source of truth).
const API_BASE = "/api";

const APP_TYPE_ICONS: Record<string, React.ReactNode> = {
  WEB: <Globe className="h-4 w-4" />,
  MOBILE_WEB: <Smartphone className="h-4 w-4" />,
  ANDROID: <Smartphone className="h-4 w-4" />,
  IOS: <Smartphone className="h-4 w-4" />,
  HYBRID: <Smartphone className="h-4 w-4" />,
};

async function fetchApplications(workspaceId: string): Promise<Application[]> {
  const response = await fetch(`${API_BASE}/workspaces/${workspaceId}/applications`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("aitis_access_token")}`,
    },
  });
  if (!response.ok) throw new Error("Failed to fetch applications");
  // Backend returns a paginated envelope: { items, total, skip, limit }
  const data = await response.json();
  return data.items ?? [];
}

async function createApplication(
  workspaceId: string,
  data: ApplicationFormData
): Promise<Application> {
  const response = await fetch(`${API_BASE}/workspaces/${workspaceId}/applications`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("aitis_access_token")}`,
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error("Failed to create application");
  return response.json();
}

async function deleteApplication(
  workspaceId: string,
  applicationId: string
): Promise<void> {
  const response = await fetch(
    `${API_BASE}/workspaces/${workspaceId}/applications/${applicationId}`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("aitis_access_token")}`,
      },
    }
  );
  if (!response.ok) throw new Error("Failed to delete application");
}

interface Environment {
  id: string;
  name: string;
  environment_type: string;
  base_url?: string;
  is_active: boolean;
}

async function fetchEnvironments(workspaceId: string, applicationId: string): Promise<Environment[]> {
  // Environments are addressed by application id (not nested under workspaces):
  // GET /api/applications/{application_id}/environments
  const response = await fetch(
    `${API_BASE}/applications/${applicationId}/environments`,
    {
      headers: { Authorization: `Bearer ${localStorage.getItem("aitis_access_token")}` },
    }
  );
  if (!response.ok) return [];
  // Backend returns a paginated envelope: { items, total, skip, limit }
  const data = await response.json();
  return data.items ?? [];
}

export function ApplicationsList({ workspaceId }: { workspaceId: string }) {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [expandedAppId, setExpandedAppId] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset, watch } = useForm<ApplicationFormData>();

  // Fetch applications
  const { data: applications = [], isLoading } = useQuery({
    queryKey: ["applications", workspaceId],
    queryFn: () => fetchApplications(workspaceId),
  });

  // Create application mutation
  const createMutation = useMutation({
    mutationFn: (data: ApplicationFormData) => createApplication(workspaceId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications", workspaceId] });
      setIsCreateOpen(false);
      reset();
    },
  });

  // Delete application mutation
  const deleteMutation = useMutation({
    mutationFn: (appId: string) => deleteApplication(workspaceId, appId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["applications", workspaceId] });
    },
  });

  const handleCreate = (data: ApplicationFormData) => {
    createMutation.mutate(data);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Applications</h3>
        <Button
          size="sm"
          onClick={() => setIsCreateOpen(true)}
          className="gap-1"
        >
          <Plus className="h-3 w-3" />
          Add Application
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-4 text-slate-500 text-sm">
          Loading applications...
        </div>
      ) : applications.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex items-center justify-center py-8">
            <div className="text-center">
              <Globe className="h-8 w-8 mx-auto text-slate-400 mb-2" />
              <p className="text-slate-600 text-sm">No applications yet</p>
              <p className="text-slate-500 text-xs">Add an application to manage environments</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {applications.map((app) => (
            <Card key={app.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    {APP_TYPE_ICONS[app.application_type]}
                    <div>
                      <CardTitle className="text-base">{app.name}</CardTitle>
                      <CardDescription className="text-xs">
                        {app.application_type}
                      </CardDescription>
                    </div>
                  </div>
                </div>
              </CardHeader>
              {app.description && (
                <CardContent className="pb-2">
                  <p className="text-sm text-slate-600 line-clamp-1">
                    {app.description}
                  </p>
                </CardContent>
              )}
              <CardContent className="pt-0">
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="flex-1 gap-1"
                    onClick={() =>
                      setExpandedAppId(expandedAppId === app.id ? null : app.id)
                    }
                  >
                    Environments
                    {expandedAppId === app.id ? (
                      <ChevronUp className="h-3 w-3" />
                    ) : (
                      <ChevronDown className="h-3 w-3" />
                    )}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => deleteMutation.mutate(app.id)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
                {expandedAppId === app.id && (
                  <EnvironmentsList
                    workspaceId={workspaceId}
                    applicationId={app.id}
                  />
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Application Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Application</DialogTitle>
            <DialogDescription>
              Create a new application to organize your deployment targets.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(handleCreate)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Application Name</Label>
              <Input
                id="name"
                placeholder="e.g., Frontend Web App"
                {...register("name", { required: true })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="type">Type</Label>
              <Select {...register("application_type", { required: true })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="WEB">Web Application</SelectItem>
                  <SelectItem value="MOBILE_WEB">Mobile Web</SelectItem>
                  <SelectItem value="ANDROID">Android</SelectItem>
                  <SelectItem value="IOS">iOS</SelectItem>
                  <SelectItem value="HYBRID">Hybrid</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="repo">Repository URL (optional)</Label>
              <Input
                id="repo"
                type="url"
                placeholder="https://github.com/..."
                {...register("repository_url")}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="desc">Description (optional)</Label>
              <Textarea
                id="desc"
                placeholder="Describe this application..."
                {...register("description")}
              />
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Creating..." : "Create"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function EnvironmentsList({
  workspaceId,
  applicationId,
}: {
  workspaceId: string;
  applicationId: string;
}) {
  const { data: environments = [], isLoading } = useQuery({
    queryKey: ["environments", workspaceId, applicationId],
    queryFn: () => fetchEnvironments(workspaceId, applicationId),
  });

  if (isLoading) {
    return (
      <div className="mt-2 text-xs text-slate-500">Loading environments...</div>
    );
  }

  if (environments.length === 0) {
    return (
      <div className="mt-2 text-xs text-slate-500">
        No environments configured
      </div>
    );
  }

  return (
    <div className="mt-2 space-y-1">
      {environments.map((env) => (
        <div
          key={env.id}
          className="flex items-center justify-between p-2 bg-slate-50 rounded text-xs"
        >
          <div>
            <span className="font-medium">{env.name}</span>
            <span className="ml-2 text-slate-500">{env.environment_type}</span>
          </div>
          <Badge tone={env.is_active ? "green" : "slate"}>
            {env.is_active ? "Active" : "Inactive"}
          </Badge>
        </div>
      ))}
    </div>
  );
}
