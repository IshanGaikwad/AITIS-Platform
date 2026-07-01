"use client";

import { use, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApplicationsList } from "@/components/applications-list";
import { EnvironmentsList } from "@/components/environments-list";
import { ArrowLeft, Settings, Users, FileText } from "lucide-react";
import { getWorkspaceStats } from "@/lib/api";
import type { WorkspaceStats } from "@/lib/types";

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
  applications?: any[];
  environments?: any[];
}

// Client-side: use a relative base so Next.js rewrites proxy /api/* to the backend
// (avoids CORS and keeps the port in next.config.mjs as the single source of truth).
const API_BASE = "/api";

async function fetchWorkspace(workspaceId: string): Promise<Workspace> {
  const response = await fetch(`${API_BASE}/workspaces/${workspaceId}`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem("aitis_access_token")}`,
    },
  });
  if (!response.ok) throw new Error("Failed to fetch workspace");
  return response.json();
}

export default function WorkspaceDetailPage({
  params,
}: {
  params: Promise<{ workspaceId: string }>;
}) {
  const { workspaceId } = use(params);
  const [activeTab, setActiveTab] = useState("overview");

  // Fetch workspace
  const { data: workspace, isLoading, isError } = useQuery({
    queryKey: ["workspace", workspaceId],
    queryFn: () => fetchWorkspace(workspaceId),
  });

  // Fetch workspace stats
  const { data: stats } = useQuery({
    queryKey: ["workspace-stats", workspaceId],
    queryFn: () => getWorkspaceStats(workspaceId),
    enabled: !!workspaceId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="h-8 w-8 border-4 border-slate-200 border-t-slate-900 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-600">Loading workspace...</p>
        </div>
      </div>
    );
  }

  if (isError || !workspace) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Card>
          <CardContent className="pt-6">
            <p className="text-red-600 mb-4">Failed to load workspace</p>
            <Link href="/workspaces">
              <Button>Back to Workspaces</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center gap-4 mb-4">
            <Link href="/workspaces">
              <Button variant="ghost" size="sm" className="gap-1">
                <ArrowLeft className="h-4 w-4" />
                Back
              </Button>
            </Link>
          </div>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold">{workspace.name}</h1>
              <p className="text-slate-600 mt-1 flex items-center gap-2">
                <code className="bg-slate-100 px-2 py-1 rounded text-sm">{workspace.key}</code>
                <Badge tone={workspace.status === "active" ? "green" : "slate"}>
                  {workspace.status}
                </Badge>
              </p>
              {workspace.description && (
                <p className="text-slate-600 mt-3 max-w-2xl">{workspace.description}</p>
              )}
              {workspace.tags && workspace.tags.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-3">
                  {workspace.tags.map((tag) => (
                    <Badge key={tag} tone="slate">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
            <Button variant="outline" className="gap-2" onClick={() => setActiveTab("settings")}>
              <Settings className="h-4 w-4" />
              Settings
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-6 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full max-w-md grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="requirements">Requirements</TabsTrigger>
            <TabsTrigger value="members">Members</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6 mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Workspace Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-xs font-medium text-slate-600">Key</p>
                    <p className="font-mono text-sm mt-1">{workspace.key}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-slate-600">Status</p>
                    <p className="text-sm mt-1 capitalize">{workspace.status}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-slate-600">Created</p>
                    <p className="text-sm mt-1">
                      {new Date(workspace.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-slate-600">Applications</p>
                    <p className="text-sm mt-1">{workspace.applications?.length || 0}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Applications</CardTitle>
                  <CardDescription>Deployment targets for this workspace</CardDescription>
                </CardHeader>
                <CardContent>
                  <ApplicationsList workspaceId={workspaceId} />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Quick Stats</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between p-3 bg-slate-50 rounded">
                    <span className="text-sm text-slate-600">Total Requirements</span>
                    <span className="text-2xl font-bold">{stats?.total_requirements ?? "—"}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-slate-50 rounded">
                    <span className="text-sm text-slate-600">Test Cases</span>
                    <span className="text-2xl font-bold">{stats?.total_test_cases ?? "—"}</span>
                  </div>
                  <div className="flex items-center justify-between p-3 bg-slate-50 rounded">
                    <span className="text-sm text-slate-600">Team Members</span>
                    <span className="text-2xl font-bold">{stats?.team_members ?? "—"}</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Requirements Tab */}
          <TabsContent value="requirements" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Requirements</CardTitle>
                <CardDescription>
                  Manage requirements and specifications for this workspace
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-center py-12">
                  <div className="text-center">
                    <FileText className="h-8 w-8 mx-auto text-slate-400 mb-2" />
                    <p className="text-slate-600">Coming soon...</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Members Tab */}
          <TabsContent value="members" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Team Members</CardTitle>
                <CardDescription>Manage who has access to this workspace</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-center py-12">
                  <div className="text-center">
                    <Users className="h-8 w-8 mx-auto text-slate-400 mb-2" />
                    <p className="text-slate-600">Coming soon...</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Workspace Settings</CardTitle>
                <CardDescription>Configure workspace details and preferences</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium text-slate-700">Workspace Name</label>
                    <p className="text-sm text-slate-600 mt-1">{workspace.name}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-slate-700">Workspace Key</label>
                    <p className="text-sm text-slate-600 mt-1 font-mono">{workspace.key}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-slate-700">Status</label>
                    <p className="text-sm mt-1">
                      <Badge tone={workspace.status === "active" ? "green" : "slate"}>
                        {workspace.status}
                      </Badge>
                    </p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-slate-700">Created</label>
                    <p className="text-sm text-slate-600 mt-1">
                      {new Date(workspace.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
