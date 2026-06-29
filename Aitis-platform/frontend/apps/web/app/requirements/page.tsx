"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth";
import { getStories } from "@/lib/api";
import type { SavedStory } from "@/lib/types";
import { FileText, Plus, Search, ExternalLink, ChevronRight } from "lucide-react";

const priorityColors: Record<string, "rose" | "amber" | "blue" | "slate"> = {
  critical: "rose",
  high: "amber",
  medium: "blue",
  low: "slate",
};

const statusColors: Record<string, "green" | "amber" | "blue" | "purple" | "slate"> = {
  active: "green",
  draft: "amber",
  review: "blue",
  approved: "purple",
  archived: "slate",
};

export default function RequirementsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [stories, setStories] = useState<SavedStory[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!isAuthenticated) return;
    getStories()
      .then(setStories)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [isAuthenticated]);

  if (authLoading) return null;
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="max-w-md text-center">
          <CardContent className="pt-8 pb-8">
            <FileText className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-slate-900">Sign in to view requirements</h2>
            <p className="text-sm text-slate-500 mt-1">Connect your account to manage requirements.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const filtered = stories.filter((s) =>
    s.title?.toLowerCase().includes(search.toLowerCase()) ||
    s.jiraId?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Requirements</h1>
          <p className="text-slate-500 mt-1">Manage your test requirements and acceptance criteria.</p>
        </div>
        <Link href="/studio">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Import from Jira
          </Button>
        </Link>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <Input
          placeholder="Search requirements by title or Jira key..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900" />
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <FileText className="h-12 w-12 text-slate-300 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900">No requirements yet</h3>
            <p className="text-sm text-slate-500 mt-1 mb-4">
              Import a Jira story to get started with AI-powered test generation.
            </p>
            <Link href="/studio">
              <Button>Go to Studio</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {filtered.map((story) => (
            <Link key={story.id} href={`/requirements/${story.id}`}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardContent className="flex items-center justify-between py-4">
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-50">
                      <FileText className="h-5 w-5 text-blue-600" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-slate-900 truncate">
                          {story.title || "Untitled"}
                        </p>
                        {story.external_id && (
                          <Badge tone="slate" className="shrink-0">
                            {story.external_id}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        {story.priority && (
                          <Badge tone={priorityColors[story.priority] || "slate"}>
                            {story.priority}
                          </Badge>
                        )}
                        {story.status && (
                          <Badge tone={statusColors[story.status] || "slate"}>
                            {story.status}
                          </Badge>
                        )}
                        {story.type && (
                          <span className="text-xs text-slate-400">{story.type}</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-slate-400 shrink-0" />
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}