"use client";

import React, { useState, useEffect } from "react";
import { 
  LayoutGrid, 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  Search, 
  Filter,
  ChevronRight,
  ArrowLeft,
  FileText
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import Link from "next/link";
import { 
  getRequirementCoverage, 
  getTestCaseById 
} from "@/lib/api";
import type { RequirementCoverageReport, RequirementCoverageItem, TestCase } from "@/lib/types";

export default function CoverageViewPage() {
  const { user } = useAuth();
  const [report, setReport] = useState<RequirementCoverageReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "covered" | "uncovered">("all");
  const [selectedItem, setSelectedItem] = useState<RequirementCoverageItem | null>(null);

  useEffect(() => {
    async function fetchCoverage() {
      try {
        const workspaceId = user?.project_id || "";
        if (!workspaceId) { setLoading(false); return; }
        const data = await getRequirementCoverage(workspaceId);
        setReport(data);
      } catch (error) {
        console.error("Failed to fetch coverage report:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchCoverage();
  }, [user?.project_id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900" />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex items-center justify-center min-h-screen text-slate-500">
        No coverage data available.
      </div>
    );
  }

  const filteredItems = report.items.filter(item => {
    const matchesSearch = (item.requirement_title ?? "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.requirement_id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === "all" ||
      (statusFilter === "covered" && item.test_case_count > 0) ||
      (statusFilter === "uncovered" && item.test_case_count === 0);
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/test-suites"><ArrowLeft className="h-4 w-4" /></Link>
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Requirement Coverage</h1>
            <p className="text-slate-500">Traceability between requirements and manual test cases.</p>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-500">Total Requirements</span>
              <LayoutGrid className="h-4 w-4 text-slate-400" />
            </div>
            <div className="text-2xl font-bold mt-2">{report.total_requirements}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-500">Covered Requirements</span>
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            </div>
            <div className="text-2xl font-bold mt-2">{report.covered_requirements}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-500">Overall Coverage</span>
              <div className="text-sm font-bold text-blue-600">{report.coverage_percent}%</div>
            </div>
            <Progress value={report.coverage_percent} className="h-2 mt-4" />
          </CardContent>
        </Card>
      </div>

      {/* Coverage Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle className="text-lg font-semibold">Coverage Matrix</CardTitle>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400" />
              <Input 
                placeholder="Search requirements..." 
                className="pl-8 w-64 h-9"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <Button
              variant={statusFilter !== "all" ? "default" : "outline"}
              size="sm"
              onClick={() => setStatusFilter(prev => prev === "all" ? "covered" : prev === "covered" ? "uncovered" : "all")}
            >
              <Filter className="h-4 w-4 mr-2" />
              {statusFilter === "all" ? "Filter" : statusFilter === "covered" ? "Covered" : "Uncovered"}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-50 border-b text-slate-500 font-medium">
                <tr>
                  <th className="p-4 font-medium">Requirement ID</th>
                  <th className="p-4 font-medium">Title</th>
                  <th className="p-4 font-medium">Coverage Status</th>
                  <th className="p-4 font-medium">Test Cases</th>
                  <th className="p-4 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredItems.map((item) => (
                  <tr 
                    key={item.requirement_id} 
                    className="hover:bg-slate-50 cursor-pointer transition-colors"
                    onClick={() => setSelectedItem(item)}
                  >
                    <td className="p-4 font-mono text-xs text-slate-600">{item.requirement_id}</td>
                    <td className="p-4 text-slate-900">{item.requirement_title}</td>
                    <td className="p-4">
                      {item.test_case_count > 0 ? (
                        <Badge className="bg-green-100 text-green-700 hover:bg-green-100 border-green-200">
                          Covered ({item.test_case_count})
                        </Badge>
                      ) : (
                        <Badge tone="rose" className="bg-rose-50 text-rose-600 border-rose-200">
                          Uncovered
                        </Badge>
                      )}
                    </td>
                    <td className="p-4">
                      <div className="flex gap-1 flex-wrap">
                        {item.test_cases.map(tc => (
                          <Badge key={tc.id} tone="slate" className="text-[10px] px-1 py-0">
                            {tc.id}
                          </Badge>
                        ))}
                        {item.test_cases.length === 0 && <span className="text-slate-400 text-xs">None</span>}
                      </div>
                    </td>
                    <td className="p-4 text-right">
                      <ChevronRight className="h-4 w-4 text-slate-300 inline" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Detail Panel */}
      {selectedItem && (
        <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex justify-end">
          <div className="w-full max-w-md bg-white h-full shadow-2xl p-6 overflow-y-auto animate-in slide-in-from-right">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold">Requirement Details</h2>
              <Button variant="ghost" size="sm" onClick={() => setSelectedItem(null)}>Close</Button>
            </div>
            
            <div className="space-y-6">
              <div>
                <Label className="text-xs text-slate-500 uppercase tracking-wider">ID</Label>
                <p className="font-mono text-sm">{selectedItem.requirement_id}</p>
              </div>
              <div>
                <Label className="text-xs text-slate-500 uppercase tracking-wider">Title</Label>
                <p className="text-slate-900 font-medium">{selectedItem.requirement_title}</p>
              </div>
              
              <div className="pt-6 border-t">
                <h3 className="text-sm font-semibold mb-4">Linked Test Cases</h3>
                <div className="space-y-3">
                  {selectedItem.test_cases.map(tc => (
                    <Card key={tc.id} className="hover:border-blue-300 transition-colors cursor-pointer" onClick={() => window.location.href = `/test-suites?caseId=${tc.id}`}>
                      <CardContent className="p-3 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <FileText className="h-4 w-4 text-slate-400" />
                          <span className="text-sm font-medium">{tc.id}: {tc.title}</span>
                        </div>
                        <ChevronRight className="h-4 w-4 text-slate-300" />
                      </CardContent>
                    </Card>
                  ))}
                  {selectedItem.test_cases.length === 0 && (
                    <p className="text-sm text-slate-500 italic">No test cases linked to this requirement.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
