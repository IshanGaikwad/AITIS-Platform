"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { KeyRound, Plus, Loader2, Pencil, Trash2, ShieldCheck } from "lucide-react";
import {
  listSsoProviders,
  createSsoProvider,
  updateSsoProvider,
  deleteSsoProvider,
} from "@/lib/api";
import type { SsoProvider, SsoProviderInput } from "@/lib/types";
import { useToast } from "@/components/ui/use-toast";

const PROVIDER_TYPES = [
  { value: "oidc", label: "Generic OIDC" },
  { value: "azure_ad", label: "Microsoft Entra ID (Azure AD)" },
  { value: "google_workspace", label: "Google Workspace" },
];

const TYPE_LABEL: Record<string, string> = {
  oidc: "OIDC",
  azure_ad: "Azure AD",
  google_workspace: "Google",
  saml: "SAML",
  ldap: "LDAP",
};

function toDomainList(raw: string): string[] {
  return raw
    .split(/[\s,]+/)
    .map((d) => d.trim().toLowerCase())
    .filter(Boolean);
}

interface FormState {
  name: string;
  provider_type: string;
  domains: string;
  is_enabled: boolean;
  is_default: boolean;
  auto_provision: boolean;
  client_id: string;
  client_secret: string;
  issuer_url: string;
  scopes: string;
  authorization_endpoint: string;
  token_endpoint: string;
  userinfo_endpoint: string;
}

const EMPTY_FORM: FormState = {
  name: "",
  provider_type: "oidc",
  domains: "",
  is_enabled: true,
  is_default: false,
  auto_provision: false,
  client_id: "",
  client_secret: "",
  issuer_url: "",
  scopes: "openid profile email",
  authorization_endpoint: "",
  token_endpoint: "",
  userinfo_endpoint: "",
};

/* ── Provider create/edit dialog ── */
function ProviderDialog({
  open,
  onClose,
  editing,
  onSaved,
}: {
  open: boolean;
  onClose: () => void;
  editing: SsoProvider | null;
  onSaved: () => void;
}) {
  const { toast } = useToast();
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (editing) {
      // Config is never returned by the API (it holds secrets), so config fields
      // start blank and are only sent if the admin re-enters them.
      setForm({
        ...EMPTY_FORM,
        name: editing.name,
        provider_type: editing.provider_type,
        domains: editing.domain_whitelist.join(", "),
        is_enabled: editing.is_enabled,
        is_default: editing.is_default,
        auto_provision: editing.auto_provision,
        scopes: "",
      });
    } else {
      setForm(EMPTY_FORM);
    }
  }, [open, editing]);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function buildConfig(): Record<string, unknown> | null {
    const hasInput =
      form.client_id || form.client_secret || form.issuer_url ||
      form.authorization_endpoint || form.token_endpoint || form.userinfo_endpoint ||
      (form.scopes && form.scopes.trim());
    if (!hasInput) return null;
    const config: Record<string, unknown> = {};
    if (form.client_id) config.client_id = form.client_id.trim();
    if (form.client_secret) config.client_secret = form.client_secret.trim();
    if (form.issuer_url) config.issuer_url = form.issuer_url.trim();
    if (form.authorization_endpoint) config.authorization_endpoint = form.authorization_endpoint.trim();
    if (form.token_endpoint) config.token_endpoint = form.token_endpoint.trim();
    if (form.userinfo_endpoint) config.userinfo_endpoint = form.userinfo_endpoint.trim();
    const scopes = form.scopes.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
    if (scopes.length) config.scopes = scopes;
    return config;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const domains = toDomainList(form.domains);
    if (!form.name.trim()) return;
    if (domains.length === 0) {
      toast({ title: "At least one email domain is required.", variant: "destructive" });
      return;
    }
    const config = buildConfig();

    setSaving(true);
    try {
      if (editing) {
        const patch: Partial<SsoProviderInput> = {
          name: form.name.trim(),
          is_enabled: form.is_enabled,
          is_default: form.is_default,
          auto_provision: form.auto_provision,
          domain_whitelist: domains,
        };
        if (config) patch.config = config;
        await updateSsoProvider(editing.id, patch);
        toast({ title: "SSO provider updated." });
      } else {
        if (!config || !config.client_id || (!config.issuer_url && !config.authorization_endpoint)) {
          toast({
            title: "Client ID and an Issuer URL (or explicit endpoints) are required.",
            variant: "destructive",
          });
          setSaving(false);
          return;
        }
        const payload: SsoProviderInput = {
          name: form.name.trim(),
          provider_type: form.provider_type,
          is_enabled: form.is_enabled,
          is_default: form.is_default,
          auto_provision: form.auto_provision,
          domain_whitelist: domains,
          config,
        };
        await createSsoProvider(payload);
        toast({ title: "SSO provider created." });
      }
      onSaved();
      onClose();
    } catch (err: unknown) {
      toast({
        title: editing ? "Failed to update provider" : "Failed to create provider",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  }

  const fieldCls =
    "w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-300";

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit SSO Provider" : "Add SSO Provider"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 mt-2">
          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Display name *</label>
            <Input value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Acme Okta" required />
          </div>

          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Provider type</label>
            <select
              className={fieldCls}
              value={form.provider_type}
              onChange={(e) => set("provider_type", e.target.value)}
              disabled={!!editing}
            >
              {PROVIDER_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-slate-600 block mb-1">Email domains *</label>
            <Input
              value={form.domains}
              onChange={(e) => set("domains", e.target.value)}
              placeholder="acme.com, acme.io"
            />
            <p className="text-[11px] text-slate-400 mt-1">Comma-separated. Users with these email domains are routed to this provider.</p>
          </div>

          {/* OIDC config */}
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-3">
            <p className="text-xs font-semibold text-slate-700">OIDC configuration</p>
            {editing && (
              <p className="text-[11px] text-slate-500 -mt-1">
                Leave credential fields blank to keep the existing configuration.
              </p>
            )}
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1">Client ID {editing ? "" : "*"}</label>
              <Input value={form.client_id} onChange={(e) => set("client_id", e.target.value)} placeholder="0oa1b2c3..." />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1">Client secret {editing ? "" : "*"}</label>
              <Input type="password" value={form.client_secret} onChange={(e) => set("client_secret", e.target.value)} placeholder="••••••••" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1">Issuer URL</label>
              <Input value={form.issuer_url} onChange={(e) => set("issuer_url", e.target.value)} placeholder="https://acme.okta.com" />
              <p className="text-[11px] text-slate-400 mt-1">Endpoints are auto-discovered from <code>/.well-known/openid-configuration</code>.</p>
            </div>
            <details className="text-xs">
              <summary className="cursor-pointer text-slate-500 hover:text-slate-700">Advanced: explicit endpoints</summary>
              <div className="mt-2 space-y-2">
                <Input value={form.authorization_endpoint} onChange={(e) => set("authorization_endpoint", e.target.value)} placeholder="Authorization endpoint" />
                <Input value={form.token_endpoint} onChange={(e) => set("token_endpoint", e.target.value)} placeholder="Token endpoint" />
                <Input value={form.userinfo_endpoint} onChange={(e) => set("userinfo_endpoint", e.target.value)} placeholder="Userinfo endpoint" />
              </div>
            </details>
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1">Scopes</label>
              <Input value={form.scopes} onChange={(e) => set("scopes", e.target.value)} placeholder="openid profile email" />
            </div>
          </div>

          {/* Toggles */}
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={form.is_enabled} onChange={(e) => set("is_enabled", e.target.checked)} className="h-4 w-4 rounded border-slate-300" />
              Enabled
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={form.is_default} onChange={(e) => set("is_default", e.target.checked)} className="h-4 w-4 rounded border-slate-300" />
              Default provider for the organization
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={form.auto_provision} onChange={(e) => set("auto_provision", e.target.checked)} className="h-4 w-4 rounded border-slate-300" />
              Auto-provision new users on first sign-in
            </label>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={saving || !form.name.trim()}>
              {saving && <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />}
              {editing ? "Save Changes" : "Create Provider"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ── Delete confirmation dialog ── */
function DeleteProviderDialog({
  provider,
  onClose,
  onConfirm,
  deleting,
}: {
  provider: SsoProvider | null;
  onClose: () => void;
  onConfirm: () => void;
  deleting: boolean;
}) {
  return (
    <Dialog open={!!provider} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-rose-100">
              <Trash2 className="h-4 w-4 text-rose-600" />
            </span>
            Remove SSO provider
          </DialogTitle>
        </DialogHeader>
        <p className="text-sm text-slate-600 mt-1">
          Remove <span className="font-semibold text-slate-900">{provider?.name}</span>? Users on
          {provider?.domain_whitelist.length ? ` ${provider.domain_whitelist.join(", ")}` : " its domains"} will lose
          SSO access. This cannot be undone.
        </p>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose} disabled={deleting}>Cancel</Button>
          <Button type="button" variant="destructive" onClick={onConfirm} disabled={deleting}>
            {deleting && <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />}
            Remove Provider
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ── SSO providers tab ── */
export function SsoProvidersTab() {
  const { toast } = useToast();
  const [providers, setProviders] = useState<SsoProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<SsoProvider | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<SsoProvider | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listSsoProviders();
      setProviders(data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load SSO providers.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleConfirmDelete() {
    if (!confirmDelete) return;
    setDeleting(true);
    try {
      await deleteSsoProvider(confirmDelete.id);
      toast({ title: "SSO provider removed." });
      setConfirmDelete(null);
      await load();
    } catch (err: unknown) {
      toast({
        title: "Failed to remove provider",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setDeleting(false);
    }
  }

  function openCreate() {
    setEditing(null);
    setDialogOpen(true);
  }

  function openEdit(provider: SsoProvider) {
    setEditing(provider);
    setDialogOpen(true);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Configure enterprise single sign-on. Users sign in via &ldquo;Continue with Organization SSO&rdquo; using their work email.
        </p>
        <Button size="sm" onClick={openCreate}>
          <Plus className="h-4 w-4 mr-2" /> Add Provider
        </Button>
      </div>

      {error && (
        <Card>
          <CardContent className="py-4 text-sm text-rose-700 bg-rose-50 rounded-lg">
            {error}
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </div>
      ) : providers.length === 0 && !error ? (
        <Card>
          <CardContent className="py-12 text-center">
            <KeyRound className="h-10 w-10 mx-auto mb-3 text-slate-300" />
            <p className="text-sm font-medium text-slate-700">No SSO providers configured</p>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              Add an OIDC provider (Okta, Entra ID, Google Workspace, Auth0) to let your team sign in with their organization identity.
            </p>
            <Button size="sm" className="mt-3" onClick={openCreate}>
              <Plus className="h-4 w-4 mr-2" /> Add Provider
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="divide-y divide-slate-100">
              {providers.map((p) => (
                <div key={p.id} className="flex items-center gap-4 px-6 py-4">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 shrink-0">
                    <ShieldCheck className="h-4 w-4 text-slate-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-semibold text-slate-900">{p.name}</p>
                      <Badge tone="slate" className="text-[10px]">{TYPE_LABEL[p.provider_type] ?? p.provider_type}</Badge>
                      {p.is_default && <Badge tone="blue" className="text-[10px]">Default</Badge>}
                      <Badge tone={p.is_enabled ? "green" : "slate"} className="text-[10px]">
                        {p.is_enabled ? "Enabled" : "Disabled"}
                      </Badge>
                      {p.auto_provision && <Badge tone="amber" className="text-[10px]">Auto-provision</Badge>}
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5 truncate">
                      {p.domain_whitelist.length ? p.domain_whitelist.join(", ") : "No domains"}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(p)} aria-label="Edit">
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setConfirmDelete(p)}
                      aria-label="Delete"
                    >
                      <Trash2 className="h-4 w-4 text-rose-500" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <ProviderDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        editing={editing}
        onSaved={load}
      />

      <DeleteProviderDialog
        provider={confirmDelete}
        onClose={() => { if (!deleting) setConfirmDelete(null); }}
        onConfirm={handleConfirmDelete}
        deleting={deleting}
      />
    </div>
  );
}
