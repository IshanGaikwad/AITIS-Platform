"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth";
import { getOrganizations, createOrganization, getProjects, createProject } from "@/lib/api";
import type { Organization, Project } from "@/lib/types";
import { Building2, Users, Plus, Settings, Globe, Hash } from "lucide-react";

export default function SettingsPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  // Create org form
  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [creatingOrg, setCreatingOrg] = useState(false);

  // Create project form
  const [wsName, setWsName] = useState("");
  const [wsSlug, setWsSlug] = useState("");
  const [wsOrgId, setWsOrgId] = useState("");
  const [creatingWs, setCreatingWs] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) return;
    getOrganizations()
      .then((orgs) => {
        setOrganizations(orgs);
        if (orgs.length > 0) {
          setWsOrgId(orgs[0].id);
          return getProjects(orgs[0].id);
        }
        return [] as Project[];
      })
      .then((wss) => {
        setProjects(wss);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [isAuthenticated]);

  const handleCreateOrg = async () => {
    if (!orgName.trim()) return;
    setCreatingOrg(true);
    try {
      const org = await createOrganization({ name: orgName, slug: orgSlug || orgName.toLowerCase().replace(/\s+/g, "-") });
      setOrganizations([...organizations, org]);
      setOrgName("");
      setOrgSlug("");
    } catch (err) {
      console.error(err);
    } finally {
      setCreatingOrg(false);
    }
  };

  const handleCreateWs = async () => {
    if (!wsName.trim() || !wsOrgId) return;
    setCreatingWs(true);
    try {
      const ws = await createProject(wsOrgId, { name: wsName, slug: wsSlug || wsName.toLowerCase().replace(/\s+/g, "-") });
      setProjects([...projects, ws]);
      setWsName("");
      setWsSlug("");
    } catch (err) {
      console.error(err);
    } finally {
      setCreatingWs(false);
    }
  };

  if (authLoading) return null;
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="max-w-md text-center">
          <CardContent className="pt-8 pb-8">
            <Settings className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-slate-900">Sign in to manage settings</h2>
            <p className="text-sm text-slate-500 mt-1">Connect your account to configure your project.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="text-slate-500 mt-1">Manage your organizations, projects, and account settings.</p>
      </div>

      <Tabs defaultValue="organizations">
        <TabsList>
          <TabsTrigger value="organizations">
            <Building2 className="h-4 w-4 mr-2" />
            Organizations
          </TabsTrigger>
          <TabsTrigger value="projects">
            <Users className="h-4 w-4 mr-2" />
            Projects
          </TabsTrigger>
          <TabsTrigger value="account">
            <Settings className="h-4 w-4 mr-2" />
            Account
          </TabsTrigger>
        </TabsList>

        <TabsContent value="organizations" className="mt-4 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Create Organization</CardTitle>
              <CardDescription>Organizations group projects and users together.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label htmlFor="orgName">Name</Label>
                <Input
                  id="orgName"
                  placeholder="My Organization"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="orgSlug">Slug (optional)</Label>
                <Input
                  id="orgSlug"
                  placeholder="my-org"
                  value={orgSlug}
                  onChange={(e) => setOrgSlug(e.target.value)}
                />
              </div>
              <Button onClick={handleCreateOrg} disabled={creatingOrg || !orgName.trim()}>
                <Plus className="h-4 w-4 mr-2" />
                {creatingOrg ? "Creating..." : "Create Organization"}
              </Button>
            </CardContent>
          </Card>

          <div className="grid gap-4">
            {organizations.map((org) => (
              <Card key={org.id}>
                <CardContent className="py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-50">
                        <Building2 className="h-5 w-5 text-purple-600" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-slate-900">{org.name}</h3>
                        {org.slug && (
                          <div className="flex items-center gap-1 text-sm text-slate-500">
                            <Hash className="h-3 w-3" />
                            {org.slug}
                          </div>
                        )}
                      </div>
                    </div>
                    <Badge tone="green">Active</Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
            {organizations.length === 0 && (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Building2 className="h-10 w-10 text-slate-300 mb-3" />
                  <p className="text-sm text-slate-500">No organizations yet. Create one above.</p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        <TabsContent value="projects" className="mt-4 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Create Project</CardTitle>
              <CardDescription>Projects contain workspaces, requirements, and tests.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label htmlFor="wsOrg">Organization</Label>
                <select
                  id="wsOrg"
                  className="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                  value={wsOrgId}
                  onChange={(e) => setWsOrgId(e.target.value)}
                >
                  {organizations.map((org) => (
                    <option key={org.id} value={org.id}>{org.name}</option>
                  ))}
                </select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="wsName">Name</Label>
                <Input
                  id="wsName"
                  placeholder="My Project"
                  value={wsName}
                  onChange={(e) => setWsName(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="wsSlug">Slug (optional)</Label>
                <Input
                  id="wsSlug"
                  placeholder="my-project"
                  value={wsSlug}
                  onChange={(e) => setWsSlug(e.target.value)}
                />
              </div>
              <Button onClick={handleCreateWs} disabled={creatingWs || !wsName.trim() || !wsOrgId}>
                <Plus className="h-4 w-4 mr-2" />
                {creatingWs ? "Creating..." : "Create Project"}
              </Button>
            </CardContent>
          </Card>

          <div className="grid gap-4">
            {projects.map((ws) => (
              <Card key={ws.id}>
                <CardContent className="py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
                        <Globe className="h-5 w-5 text-blue-600" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-slate-900">{ws.name}</h3>
                        {ws.slug && (
                          <div className="flex items-center gap-1 text-sm text-slate-500">
                            <Hash className="h-3 w-3" />
                            {ws.slug}
                          </div>
                        )}
                      </div>
                    </div>
                    <Badge tone="blue">Active</Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
            {projects.length === 0 && (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Globe className="h-10 w-10 text-slate-300 mb-3" />
                  <p className="text-sm text-slate-500">No projects yet. Create one above.</p>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        <TabsContent value="account" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>Account Information</CardTitle>
              <CardDescription>Your profile and authentication details.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label>Name</Label>
                <p className="text-sm text-slate-700">{user?.name || "—"}</p>
              </div>
              <div className="grid gap-2">
                <Label>Email</Label>
                <p className="text-sm text-slate-700">{user?.email || "—"}</p>
              </div>
              <div className="grid gap-2">
                <Label>Provider</Label>
                <Badge tone="blue">{user?.provider || "unknown"}</Badge>
              </div>
              <div className="grid gap-2">
                <Label>Role</Label>
                <Badge tone="purple">{user?.role || "viewer"}</Badge>
              </div>
              <div className="grid gap-2">
                <Label>Organization ID</Label>
                <p className="text-sm text-slate-500 font-mono">{user?.organization_id || "—"}</p>
              </div>
              <div className="grid gap-2">
                <Label>Project ID</Label>
                <p className="text-sm text-slate-500 font-mono">{user?.project_id || "—"}</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}