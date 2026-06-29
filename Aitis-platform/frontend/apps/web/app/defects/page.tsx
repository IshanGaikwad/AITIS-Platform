"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { getDefects } from "@/lib/api";
import type { Defect } from "@/lib/types";
import { Bug, Search, AlertTriangle, AlertCircle, ShieldAlert } from "lucide-react";

const severityIcons: Record<string, React.ReactNode> = {
  critical: <ShieldAlert className="h-4 w-4 text-red-600" />,
  major: <AlertCircle className="h-4 w-4 text-amber-600" />,
  minor: <AlertTriangle className="h-4 w-4 text-blue-600" />,
};

const severityColors: Record<string, "rose" | "amber" | "blue" | "slate"> = {
  critical: "rose",
  major: "amber",
  minor: "blue",
  trivial: "slate",
};

const statusColors: Record<string, "rose" | "amber" | "blue" | "green" | "purple" | "slate"> = {
  open: "rose",
  in_progress: "amber",
  in_review: "blue",
  resolved: "green",
  closed: "purple",
  wont_fix: "slate",
};

export default function DefectsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [defects, setDefects] = useState<Defect[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    if (!isAuthenticated) return;
    getDefects()
      .then(setDefects)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [isAuthenticated]);

  if (authLoading) return null;
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="max-w-md text-center">
          <CardContent className="pt-8 pb-8">
            <Bug className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-slate-900">Sign in to view defects</h2>
            <p className="text-sm text-slate-500 mt-1">Connect your account to manage defects.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const filtered = defects.filter((d) =>
    d.title?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Defects</h1>
        <p className="text-slate-500 mt-1">Track and manage defects found during test execution.</p>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <Input
          placeholder="Search defects..."
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
            <Bug className="h-12 w-12 text-slate-300 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900">No defects found</h3>
            <p className="text-sm text-slate-500 mt-1">
              Defects will appear here when test executions find issues.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {filtered.map((defect) => (
            <Card key={defect.id}>
              <CardContent className="py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 min-w-0">
                    <div className="mt-0.5">
                      {severityIcons[defect.severity] || <Bug className="h-4 w-4 text-slate-400" />}
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-medium text-slate-900">{defect.title}</h3>
                      {defect.description && (
                        <p className="text-sm text-slate-500 mt-1 line-clamp-2">{defect.description}</p>
                      )}
                      <div className="flex items-center gap-2 mt-2">
                        {defect.severity && (
                          <Badge tone={severityColors[defect.severity] || "slate"}>
                            {defect.severity}
                          </Badge>
                        )}
                        {defect.status && (
                          <Badge tone={statusColors[defect.status] || "slate"}>
                            {defect.status.replace("_", " ")}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}