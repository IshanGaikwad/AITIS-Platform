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
import { Plus, Server, Trash2, CheckCircle, AlertCircle } from "lucide-react";
import { useForm } from "react-hook-form";

interface Environment {
  id: string;
  workspace_id: string;
  application_id: string;
  name: string;
  environment_type: "dev" | "qa" | "uat" | "staging" | "prod" | "custom";
  base_url: string;
  environment_variables?: Array<{ name: string; isSecret: boolean }>;
  health_check_enabled: boolean;
  health_check_url?: string;
  created_at: string;
}

interface EnvironmentFormData {
  name: string;
  environment_type: Environment["environment_type"];
  base_url: string;
  health_check_url?: string;
  health_check_enabled?: boolean;
}

// Client-side: use a relative base so Next.js rewrites proxy /api/* to the backend
// (avoids CORS and keeps the port in next.config.mjs as the single source of truth).
const API_BASE = "/api";

const ENV_TYPE_COLORS: Record<string, string> = {
  dev: "bg-blue-100 text-blue-800",
  qa: "bg-yellow-100 text-yellow-800",
  uat: "bg-purple-100 text-purple-800",
  staging: "bg-orange-100 text-orange-800",
  prod: "bg-red-100 text-red-800",
  custom: "bg-slate-100 text-slate-800",
};

async function fetchEnvironments(
  workspaceId: string,
  applicationId: string
): Promise<Environment[]> {
  const response = await fetch(
    `${API_BASE}/applications/${applicationId}/environments`,
    {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("aitis_access_token")}`,
      },
    }
  );
  if (!response.ok) throw new Error("Failed to fetch environments");
  // Backend returns a paginated envelope: { items, total, skip, limit }
  const data = await response.json();
  return data.items ?? [];
}

async function createEnvironment(
  applicationId: string,
  data: EnvironmentFormData
): Promise<Environment> {
  const response = await fetch(
    `${API_BASE}/applications/${applicationId}/environments`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("aitis_access_token")}`,
      },
      body: JSON.stringify(data),
    }
  );
  if (!response.ok) throw new Error("Failed to create environment");
  return response.json();
}

async function deleteEnvironment(
  applicationId: string,
  environmentId: string
): Promise<void> {
  const response = await fetch(
    `${API_BASE}/applications/${applicationId}/environments/${environmentId}`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("aitis_access_token")}`,
      },
    }
  );
  if (!response.ok) throw new Error("Failed to delete environment");
}

export function EnvironmentsList({
  workspaceId,
  applicationId,
  applicationName,
}: {
  workspaceId: string;
  applicationId: string;
  applicationName: string;
}) {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const queryClient = useQueryClient();
  const { register, handleSubmit, reset, formState: { errors } } = useForm<EnvironmentFormData>();

  // Fetch environments
  const { data: environments = [], isLoading } = useQuery({
    queryKey: ["environments", applicationId],
    queryFn: () => fetchEnvironments(workspaceId, applicationId),
  });

  // Create environment mutation
  const createMutation = useMutation({
    mutationFn: (data: EnvironmentFormData) => createEnvironment(applicationId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["environments", applicationId] });
      setIsCreateOpen(false);
      reset();
    },
  });

  // Delete environment mutation
  const deleteMutation = useMutation({
    mutationFn: (envId: string) => deleteEnvironment(applicationId, envId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["environments", applicationId] });
    },
  });

  const handleCreate = (data: EnvironmentFormData) => {
    createMutation.mutate(data);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold">Environments for {applicationName}</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Manage deployment environments and configurations
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => setIsCreateOpen(true)}
          className="gap-1"
        >
          <Plus className="h-3 w-3" />
          Add Environment
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-slate-500 text-sm">
          Loading environments...
        </div>
      ) : environments.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex items-center justify-center py-12">
            <div className="text-center">
              <Server className="h-8 w-8 mx-auto text-slate-400 mb-2" />
              <p className="text-slate-600 text-sm">No environments yet</p>
              <p className="text-slate-500 text-xs">
                Create environments to configure deployment targets
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {environments.map((env) => (
            <Card key={env.id} className="hover:shadow-sm transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <Server className="h-4 w-4 text-slate-600" />
                    <div>
                      <CardTitle className="text-base">{env.name}</CardTitle>
                      <CardDescription className="text-xs mt-0.5">
                        {env.base_url}
                      </CardDescription>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={ENV_TYPE_COLORS[env.environment_type]}>
                      {env.environment_type}
                    </Badge>
                    {env.health_check_enabled && (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    )}
                  </div>
                </div>
              </CardHeader>
              {env.health_check_url && (
                <CardContent className="pb-2 pt-0">
                  <p className="text-xs text-slate-600">
                    Health Check: {env.health_check_url}
                  </p>
                </CardContent>
              )}
              <CardContent className="pt-0 flex justify-end gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => deleteMutation.mutate(env.id)}
                  disabled={deleteMutation.isPending}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Environment Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Environment</DialogTitle>
            <DialogDescription>
              Create a new deployment environment for {applicationName}.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(handleCreate)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Environment Name</Label>
              <Input
                id="name"
                placeholder="e.g., Development"
                {...register("name", { required: "Environment name is required" })}
              />
              {errors.name && <p className="text-xs text-red-500">{errors.name.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="type">Type</Label>
              <Select {...register("environment_type", { required: true })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="dev">Development</SelectItem>
                  <SelectItem value="qa">QA</SelectItem>
                  <SelectItem value="uat">UAT</SelectItem>
                  <SelectItem value="staging">Staging</SelectItem>
                  <SelectItem value="prod">Production</SelectItem>
                  <SelectItem value="custom">Custom</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="url">Base URL</Label>
              <Input
                id="url"
                type="url"
                placeholder="https://dev.example.com"
                {...register("base_url", { required: "Base URL is required" })}
              />
              {errors.base_url && (
                <p className="text-xs text-red-500">{errors.base_url.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="hc_url">Health Check URL (optional)</Label>
              <Input
                id="hc_url"
                type="url"
                placeholder="https://dev.example.com/health"
                {...register("health_check_url")}
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
