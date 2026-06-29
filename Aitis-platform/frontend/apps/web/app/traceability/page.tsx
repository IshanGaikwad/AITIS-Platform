"use client";

import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth";
import { getTraceabilityMatrix, getRequirementCoverage } from "@/lib/api";
import type { TraceabilityMatrix, TraceabilityLink, RequirementCoverageReport } from "@/lib/types";
import {
  GitBranch,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileText,
  Bug,
  Zap,
  ArrowRight,
} from "lucide-react";
import Link from "next/link";

const statusBadge: Record<string, string> = {
  passed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  error: "bg-red-100 text-red-800",
  skipped: "bg-slate-100 text-slate-600",
  pending: "bg-amber-100 text-amber-800",
  unknown: "bg-slate-100 text-slate-500",
};

export default function TraceabilityPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [matrix, setMatrix] = useState<TraceabilityMatrix | null>(null);
  const [coverage, setCoverage] = useState<RequirementCoverageReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showUncoveredOnly, setShowUncoveredOnly] = useState(false);

  const projectId = user?.workspace_id || "";

  useEffect(() => {
    if (!isAuthenticated || !projectId) return;
    Promise.all([
      getTraceabilityMatrix(projectId),
      getRequirementCoverage(projectId),
    ])
      .then(([mat, cov]) => {
        setMatrix(mat);
        setCoverage(cov);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [isAuthenticated, projectId]);

  const filteredLinks = useMemo(() => {
    if (!matrix?.links) return [];
    let links = matrix.links;
    if (showUncoveredOnly) {
      links = links.filter((l) => !l.test_case_id);
    }
    if (search) {
      const q = search.toLowerCase();
      links = links.filter(
        (l) =>
          l.requirement_title?.toLowerCase().includes(q) ||
          l.test_case_title?.toLowerCase().includes(q) ||
          l.automation_script_name?.toLowerCase().includes(q)
      );
    }
    return links;
  }, [matrix, search, showUncoveredOnly]);

  if (authLoading) return null;
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="max-w-md text-center">
          <CardContent className="pt-8 pb-8">
            <GitBranch className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-slate-900">Sign in to view traceability</h2>
            <p className="text-sm text-slate-500 mt-1">Connect your account to see the traceability matrix.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Traceability Matrix</h1>
          <p className="text-slate-500 mt-1">
            Requirements → Test Cases → Automation → Defects
          </p>
        </div>
        {coverage && (
          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-2xl font-bold text-slate-900">{coverage.coverage_percent}%</div>
              <div className="text-xs text-slate-500">Coverage</div>
            </div>
          </div>
        )}
      </div>

      {/* ── Coverage Summary ── */}
      {coverage && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-blue-500" />
                <div>
                  <div className="text-2xl font-bold text-slate-900">{coverage.total_requirements}</div>
                  <div className="text-xs text-slate-500">Total Requirements</div>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-500" />
                <div>
                  <div className="text-2xl font-bold text-green-700">{coverage.covered_requirements}</div>
                  <div className="text-xs text-slate-500">Covered</div>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <XCircle className="h-5 w-5 text-red-500" />
                <div>
                  <div className="text-2xl font-bold text-red-700">{coverage.total_requirements - coverage.covered_requirements}</div>
                  <div className="text-xs text-slate-500">Uncovered</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ── Filters ── */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search requirements, test cases..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button
          variant={showUncoveredOnly ? "default" : "outline"}
          size="sm"
          onClick={() => setShowUncoveredOnly(!showUncoveredOnly)}
        >
          <Filter className="h-4 w-4 mr-1" />
          {showUncoveredOnly ? "Show All" : "Uncovered Only"}
        </Button>
      </div>

      {/* ── Matrix Table ── */}
      <Card>
        <CardContent className="pt-6">
          {filteredLinks.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <GitBranch className="h-12 w-12 text-slate-300 mx-auto mb-4" />
              <p className="text-lg font-medium">No traceability links found</p>
              <p className="text-sm mt-1">
                {matrix ? "Try adjusting your filters." : "Create requirements and test cases to build the matrix."}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 px-3 font-medium text-slate-500">Requirement</th>
                    <th className="text-left py-3 px-3 font-medium text-slate-500">Status</th>
                    <th className="text-left py-3 px-3 font-medium text-slate-500">Test Suite</th>
                    <th className="text-left py-3 px-3 font-medium text-slate-500">Test Case</th>
                    <th className="text-left py-3 px-3 font-medium text-slate-500">Automation</th>
                    <th className="text-left py-3 px-3 font-medium text-slate-500">Last Run</th>
                    <th className="text-left py-3 px-3 font-medium text-slate-500">Defects</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLinks.map((link, i) => (
                    <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="py-3 px-3">
                        <div className="font-medium text-slate-900 max-w-[200px] truncate">
                          {link.requirement_title || "—"}
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <Badge tone={link.requirement_status === 'approved' ? 'green' : link.requirement_status === 'draft' ? 'amber' : 'slate'} className="border">
                          {link.requirement_status || "—"}
                        </Badge>
                      </td>
                      <td className="py-3 px-3 text-slate-600 max-w-[150px] truncate">
                        {link.test_suite_name || "—"}
                      </td>
                      <td className="py-3 px-3">
                        {link.test_case_title ? (
                          <div className="flex items-center gap-1">
                            <span className="max-w-[150px] truncate">{link.test_case_title}</span>
                          </div>
                        ) : (
                          <span className="text-slate-400">No test case</span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        {link.automation_script_name ? (
                          <div className="flex items-center gap-1">
                            <Zap className="h-3 w-3 text-blue-500" />
                            <span className="max-w-[120px] truncate text-blue-700">{link.automation_script_name}</span>
                          </div>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        {link.last_execution_status ? (
                          <Badge tone={link.last_execution_status === 'passed' ? 'green' : link.last_execution_status === 'failed' ? 'rose' : 'slate'} className="border">
                            {link.last_execution_status}
                          </Badge>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        {link.defect_count > 0 ? (
                          <div className="flex items-center gap-1">
                            <Bug className="h-3 w-3 text-red-500" />
                            <span className="text-red-700 font-medium">{link.defect_count}</span>
                          </div>
                        ) : (
                          <span className="text-slate-400">0</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Coverage Detail ── */}
      {coverage && coverage.items && coverage.items.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Requirement Coverage Detail</CardTitle>
            <CardDescription>Per-requirement test coverage breakdown</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {coverage.items.map((item) => (
                <div key={item.requirement_id} className="flex items-center gap-3 py-2 border-b border-slate-100 last:border-0">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-slate-900 truncate">
                      {item.requirement_title || item.requirement_id}
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {item.test_case_count} test case{item.test_case_count !== 1 ? "s" : ""}
                    </div>
                  </div>
                  <Badge tone={item.covered ? 'green' : 'rose'} className="shrink-0">
                    {item.covered ? "Covered" : "Uncovered"}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
