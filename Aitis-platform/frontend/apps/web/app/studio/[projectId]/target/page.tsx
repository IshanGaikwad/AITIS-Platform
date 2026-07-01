"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { Globe, Sparkles, AlertCircle, CheckCircle2, ExternalLink } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";
import {
  detectStack,
  getWorkspaceApplications,
  createApplication,
  getWorkspaceEnvironments,
  createEnvironment,
} from "@/lib/api";
import type {
  Application,
  ApplicationType,
  Environment,
  StackDetectionResult,
} from "@/lib/types";

const APPLICATION_TYPES: ApplicationType[] = ["WEB", "MOBILE_WEB", "ANDROID", "IOS", "HYBRID"];

function confidenceTone(confidence: number): "green" | "amber" | "rose" {
  if (confidence >= 0.7) return "green";
  if (confidence >= 0.35) return "amber";
  return "rose";
}

function hostnameFromUrl(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

export default function TargetPage() {
  const params = useParams();
  const workspaceId = params.projectId as string;
  const { toast } = useToast();

  const [applications, setApplications] = useState<Application[]>([]);
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [loading, setLoading] = useState(true);

  const [url, setUrl] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [detection, setDetection] = useState<StackDetectionResult | null>(null);

  const [appName, setAppName] = useState("");
  const [appType, setAppType] = useState<ApplicationType>("WEB");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const fetchTargets = useCallback(async () => {
    setLoading(true);
    try {
      const [apps, envs] = await Promise.all([
        getWorkspaceApplications(workspaceId),
        getWorkspaceEnvironments(workspaceId),
      ]);
      setApplications(apps);
      setEnvironments(envs);
    } catch {
      // non-fatal — the form above still works
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    fetchTargets();
  }, [fetchTargets]);

  const handleAnalyze = async () => {
    if (!url.trim()) {
      setAnalyzeError("Enter a URL first.");
      return;
    }
    setAnalyzing(true);
    setAnalyzeError(null);
    setDetection(null);
    try {
      const result = await detectStack(url.trim());
      setDetection(result);
      setAppType(result.suggested_application_type);
      setAppName(result.page_title || hostnameFromUrl(result.final_url));
    } catch (err) {
      setAnalyzeError(err instanceof Error ? err.message : "Failed to analyze URL.");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSaveTarget = async () => {
    if (!detection) return;
    if (!appName.trim()) {
      setSaveError("Application name is required.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      const app = await createApplication(workspaceId, {
        name: appName.trim(),
        application_type: appType,
        metadata_: {
          frontend_framework: detection.frontend_framework,
          backend_hints: detection.backend_hints,
          language: detection.language,
          css_framework: detection.css_framework,
          confidence: detection.confidence,
          detected_summary: detection.summary,
        },
      });
      await createEnvironment(app.id, {
        name: "Default",
        environment_type: "production",
        base_url: detection.final_url,
      });
      toast({ title: "Target saved", description: appName.trim(), variant: "success" });
      setUrl("");
      setDetection(null);
      setAppName("");
      await fetchTargets();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save target.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Target — System Under Test</h2>
        <p className="text-sm text-slate-500">
          Give the system a URL to test. It analyzes the page to infer the technology stack,
          then saves it as an Application + Environment that the Execution step can run against.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-4 pt-5">
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4 text-slate-700" />
            <h3 className="text-sm font-semibold text-slate-900">Analyze a URL</h3>
          </div>
          <div className="flex gap-2">
            <Input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://your-app.example.com"
              onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
            />
            <Button onClick={handleAnalyze} disabled={analyzing}>
              <Sparkles className="h-4 w-4" />
              {analyzing ? "Analyzing..." : "Analyze"}
            </Button>
          </div>
          {analyzeError && (
            <div className="flex items-center gap-2 rounded-lg border border-rose-100 bg-rose-50 p-3 text-sm text-rose-700">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {analyzeError}
            </div>
          )}

          {detection && (
            <div className="space-y-4 rounded-xl border border-slate-200 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                <span className="text-sm font-medium text-slate-800">{detection.final_url}</span>
                <Badge tone={confidenceTone(detection.confidence)}>
                  {Math.round(detection.confidence * 100)}% confidence
                </Badge>
                {detection.http_status && <Badge tone="slate">HTTP {detection.http_status}</Badge>}
              </div>
              <p className="text-sm text-slate-600">{detection.summary}</p>
              <div className="flex flex-wrap gap-2 text-xs">
                {detection.frontend_framework && (
                  <Badge tone="blue">Frontend: {detection.frontend_framework}</Badge>
                )}
                {detection.css_framework && <Badge tone="amber">CSS: {detection.css_framework}</Badge>}
                {detection.language && <Badge tone="green">Language: {detection.language}</Badge>}
                {detection.backend_hints && <Badge tone="slate">Backend: {detection.backend_hints}</Badge>}
              </div>

              <div className="grid gap-3 border-t border-slate-100 pt-4 sm:grid-cols-[1fr_auto]">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-600">Application name</label>
                  <Input value={appName} onChange={(e) => setAppName(e.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-600">Type</label>
                  <select
                    value={appType}
                    onChange={(e) => setAppType(e.target.value as ApplicationType)}
                    className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm outline-none focus:border-slate-400"
                  >
                    {APPLICATION_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              {saveError && <p className="text-sm text-rose-600">{saveError}</p>}
              <Button onClick={handleSaveTarget} disabled={saving}>
                {saving ? "Saving..." : "Save Target"}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-slate-900">Configured targets</h3>
        {loading ? (
          <div className="h-16 animate-pulse rounded-lg bg-slate-100" />
        ) : environments.length === 0 ? (
          <p className="text-sm text-slate-500">
            No targets configured yet. Analyze a URL above to add one.
          </p>
        ) : (
          <div className="space-y-2">
            {environments.map((env) => {
              const app = applications.find((a) => a.id === env.application_id);
              return (
                <div
                  key={env.id}
                  className="flex items-center gap-3 rounded-lg border border-slate-100 bg-white px-4 py-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-800">
                      {app?.name ?? "Application"}{" "}
                      <span className="font-normal text-slate-400">· {env.name}</span>
                    </p>
                    {env.base_url && (
                      <a
                        href={env.base_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
                      >
                        {env.base_url}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                  {app && <Badge tone="slate">{app.application_type}</Badge>}
                  <Badge tone="green">{env.environment_type}</Badge>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
