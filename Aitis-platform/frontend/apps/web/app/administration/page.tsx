"use client";

import { useState, useEffect } from "react";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Plus,
  Building2,
  Users,
  Shield,
  Plug,
  ScrollText,
  Bot,
  Loader2,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { getOrganizations, getWorkspaces, createWorkspace, getAuditEvents } from "@/lib/api";
import type { Workspace, Organization, AuditEvent } from "@/lib/types";
import { useToast } from "@/components/ui/use-toast";

/* ── Static data ── */
const ROLES = [
  { name: "Organization Owner", description: "Full control over org settings, billing, and all workspaces.", color: "rose" as const },
  { name: "Administrator", description: "Manage members, workspaces, and integrations.", color: "rose" as const },
  { name: "QA Lead", description: "Create and manage test suites, runs, defects, and reports.", color: "amber" as const },
  { name: "Automation Engineer", description: "Write, version, and execute automation scripts.", color: "blue" as const },
  { name: "Manual Tester", description: "Execute manual test cases and log defects.", color: "blue" as const },
  { name: "Developer", description: "View tests and manage defects assigned to them.", color: "slate" as const },
  { name: "Viewer", description: "Read-only access to all resources.", color: "slate" as const },
];

const INTEGRATIONS = [
  { name: "Jira", description: "Import stories and sync defects.", icon: "J" },
  { name: "GitHub", description: "Trigger runs from CI/CD pipelines.", icon: "G" },
  { name: "GitLab", description: "Trigger runs from GitLab CI pipelines.", icon: "GL" },
  { name: "Slack", description: "Send run notifications to channels.", icon: "S" },
  { name: "Microsoft Teams", description: "Send alerts to Teams channels.", icon: "T" },
];

/* ── Create Workspace Dialog ── */
interface CreateWorkspaceDialogProps {
  open: boolean;
  onClose: () => void;
  orgId: string;
  onCreated: () => void;
}

function CreateWorkspaceDialog({ open, onClose, orgId, onCreated }: CreateWorkspaceDialogProps) {
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);

  const slug = name.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !orgId) return;
    setSaving(true);
    try {
      await createWorkspace(orgId, { name: name.trim(), slug, description: "" });
      toast({ title: "Workspace created." });
      onCreated();
      onClose();
      setName("");
    } catch (err: unknown) {
      toast({
        title: "Failed to create workspace",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Workspace</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 mt-2">
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Name *</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="My Workspace" required />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Slug (auto-generated)</label>
            <Input value={slug} readOnly className="bg-slate-50 text-slate-500" />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={saving || !name.trim()}>
              {saving && <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />}
              Create
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ── Page ── */
export default function AdministrationPage() {
  const { user } = useAuth();
  const { toast } = useToast();

  const [activeTab, setActiveTab] = useState("workspaces");
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(true);
  const [loadingAudit, setLoadingAudit] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  // AI config state (localStorage persisted)
  const [aiProvider, setAiProvider] = useState("claude");
  const [aiModel, setAiModel] = useState("claude-sonnet-4-6");
  const [maxTokens, setMaxTokens] = useState("4096");

  useEffect(() => {
    const saved = localStorage.getItem("aitis_ai_config");
    if (saved) {
      try {
        const c = JSON.parse(saved);
        if (c.provider) setAiProvider(c.provider);
        if (c.model) setAiModel(c.model);
        if (c.maxTokens) setMaxTokens(c.maxTokens);
      } catch {
        // ignore
      }
    }
  }, []);

  async function loadWorkspaces() {
    setLoadingWorkspaces(true);
    try {
      const orgList = await getOrganizations();
      setOrgs(orgList);
      if (orgList.length > 0) {
        const wsList = await getWorkspaces(orgList[0].id);
        setWorkspaces(wsList);
      }
    } catch {
      // show empty
    } finally {
      setLoadingWorkspaces(false);
    }
  }

  useEffect(() => {
    if (!user) return;
    loadWorkspaces();
  }, [user]);

  useEffect(() => {
    if (activeTab !== "audit-log") return;
    setLoadingAudit(true);
    getAuditEvents()
      .then(setAuditEvents)
      .catch(() => setAuditEvents([]))
      .finally(() => setLoadingAudit(false));
  }, [activeTab]);

  function saveAiConfig() {
    localStorage.setItem("aitis_ai_config", JSON.stringify({ provider: aiProvider, model: aiModel, maxTokens }));
    toast({ title: "AI configuration saved." });
  }

  const primaryOrgId = orgs[0]?.id ?? "";

  return (
    <ProtectedRoute>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Administration</h1>
          <p className="text-slate-500 mt-1">
            Manage workspaces, members, roles, integrations, and platform settings.
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="flex-wrap h-auto gap-1">
            <TabsTrigger value="workspaces" className="flex items-center gap-1.5">
              <Building2 className="h-3.5 w-3.5" /> Workspaces
            </TabsTrigger>
            <TabsTrigger value="members" className="flex items-center gap-1.5">
              <Users className="h-3.5 w-3.5" /> Members
            </TabsTrigger>
            <TabsTrigger value="roles" className="flex items-center gap-1.5">
              <Shield className="h-3.5 w-3.5" /> Roles
            </TabsTrigger>
            <TabsTrigger value="integrations" className="flex items-center gap-1.5">
              <Plug className="h-3.5 w-3.5" /> Integrations
            </TabsTrigger>
            <TabsTrigger value="audit-log" className="flex items-center gap-1.5">
              <ScrollText className="h-3.5 w-3.5" /> Audit Log
            </TabsTrigger>
            <TabsTrigger value="ai-config" className="flex items-center gap-1.5">
              <Bot className="h-3.5 w-3.5" /> AI Configuration
            </TabsTrigger>
          </TabsList>

          {/* Workspaces */}
          <TabsContent value="workspaces" className="mt-4 space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-500">
                {loadingWorkspaces ? "Loading..." : `${workspaces.length} workspace${workspaces.length !== 1 ? "s" : ""}`}
              </p>
              <Button size="sm" onClick={() => setCreateDialogOpen(true)} disabled={!primaryOrgId}>
                <Plus className="h-4 w-4 mr-2" /> Create Workspace
              </Button>
            </div>
            {loadingWorkspaces ? (
              <div className="flex items-center justify-center h-32">
                <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
              </div>
            ) : workspaces.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Building2 className="h-10 w-10 mx-auto mb-3 text-slate-300" />
                  <p className="text-sm text-slate-500">No workspaces found.</p>
                  {primaryOrgId && (
                    <Button size="sm" className="mt-3" onClick={() => setCreateDialogOpen(true)}>
                      <Plus className="h-4 w-4 mr-2" /> Create Workspace
                    </Button>
                  )}
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="p-0">
                  <div className="divide-y divide-slate-100">
                    {workspaces.map((ws) => (
                      <div key={ws.id} className="flex items-center gap-4 px-6 py-4">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 shrink-0">
                          <Building2 className="h-4 w-4 text-slate-600" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-slate-900">{ws.name}</p>
                          <p className="text-xs text-slate-500">/{ws.slug} · Created {ws.created_at.slice(0, 10)}</p>
                        </div>
                        <Badge tone="green">Active</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
            <CreateWorkspaceDialog
              open={createDialogOpen}
              onClose={() => setCreateDialogOpen(false)}
              orgId={primaryOrgId}
              onCreated={loadWorkspaces}
            />
          </TabsContent>

          {/* Members */}
          <TabsContent value="members" className="mt-4">
            <Card>
              <CardContent className="py-12 text-center">
                <Users className="h-10 w-10 mx-auto mb-3 text-slate-300" />
                <p className="text-sm font-medium text-slate-700">Member management coming soon</p>
                <p className="text-xs text-slate-500 mt-2 max-w-sm mx-auto">
                  Use your identity provider to manage team access. Member provisioning via AITIS UI is on the roadmap.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Roles */}
          <TabsContent value="roles" className="mt-4 space-y-3">
            <p className="text-sm text-slate-500">Platform roles and their permissions.</p>
            {ROLES.map((role) => (
              <Card key={role.name} className="hover:shadow-sm transition-shadow">
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-center gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <p className="text-sm font-semibold text-slate-900">{role.name}</p>
                        <Badge tone={role.color}>{role.name.split(" ")[0]}</Badge>
                      </div>
                      <p className="text-xs text-slate-500">{role.description}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          {/* Integrations */}
          <TabsContent value="integrations" className="mt-4 space-y-3">
            <p className="text-sm text-slate-500">Connect AITIS to your existing tools and services.</p>
            {INTEGRATIONS.map((integration) => (
              <Card key={integration.name} className="hover:shadow-sm transition-shadow">
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-center gap-4">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-900 text-xs font-bold text-white shrink-0">
                      {integration.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-slate-900">{integration.name}</p>
                      <p className="text-xs text-slate-500">{integration.description}</p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toast({ title: "Integration configuration coming soon." })}
                    >
                      Configure
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          {/* Audit Log */}
          <TabsContent value="audit-log" className="mt-4 space-y-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-700">Recent Activity</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {loadingAudit ? (
                  <div className="flex items-center justify-center h-32">
                    <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
                  </div>
                ) : auditEvents.length === 0 ? (
                  <p className="text-sm text-slate-500 px-6 py-4">No audit events found.</p>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {auditEvents.map((event) => (
                      <div key={event.id} className="flex items-start gap-4 px-6 py-3">
                        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100 text-[10px] font-bold text-slate-600 shrink-0 mt-0.5">
                          {(event.user_id ?? "?")[0].toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-slate-900">
                            <span className="font-medium">{event.action}</span>
                          </p>
                          <p className="text-xs text-slate-500 mt-0.5">
                            {event.entity_type} · {event.entity_id.slice(0, 12)}
                          </p>
                          <p className="text-xs text-slate-400 mt-0.5">
                            {new Date(event.created_at).toLocaleString()}
                          </p>
                        </div>
                        <Badge tone="slate" className="text-[10px] shrink-0">{event.entity_type}</Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* AI Configuration */}
          <TabsContent value="ai-config" className="mt-4">
            <div className="space-y-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-slate-700">AI Provider</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="text-xs font-medium text-slate-600 block mb-1">Provider</label>
                    <select
                      className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-300"
                      value={aiProvider}
                      onChange={(e) => setAiProvider(e.target.value)}
                    >
                      <option value="claude">Anthropic Claude</option>
                      <option value="gpt4">OpenAI GPT-4</option>
                      <option value="custom">Custom / Self-hosted</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-600 block mb-1">Model</label>
                    <select
                      className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-300"
                      value={aiModel}
                      onChange={(e) => setAiModel(e.target.value)}
                    >
                      <option value="claude-sonnet-4-6">Claude Sonnet 4.6</option>
                      <option value="claude-haiku-3-5">Claude Haiku 3.5</option>
                      <option value="gpt-4o">GPT-4o</option>
                      <option value="gpt-4-turbo">GPT-4 Turbo</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-600 block mb-1">Max Tokens per Generation</label>
                    <Input
                      type="number"
                      value={maxTokens}
                      onChange={(e) => setMaxTokens(e.target.value)}
                      min="512"
                      max="16384"
                    />
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-slate-700">AI Safety Guardrails</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm text-slate-700">
                    <div className="flex items-center justify-between">
                      <span>PII detection in test data</span>
                      <Badge tone="green">Enabled</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Output content filtering</span>
                      <Badge tone="green">Enabled</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Test generation</span>
                      <Badge tone="green">Active</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
              <Button onClick={saveAiConfig}>Save Configuration</Button>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </ProtectedRoute>
  );
}
