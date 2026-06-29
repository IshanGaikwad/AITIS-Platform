"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/lib/auth";
import { getTestSuites, getTestCases, createTestSuite, deleteTestSuite } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { TestSuite, TestCaseDB } from "@/lib/types";
import { FlaskConical, TestTube, Clock, CheckCircle2, AlertCircle, Play, Plus, Trash2 } from "lucide-react";
import { TestSuiteFolderTree } from "@/components/TestSuiteFolderTree";
import { TestCaseEditor } from "@/components/TestCaseEditor";
import { useRouter } from "next/navigation";

const statusColors: Record<string, "green" | "amber" | "rose" | "slate" | "blue"> = {
  passed: "green",
  failed: "rose",
  skipped: "amber",
  pending: "slate",
  running: "blue",
};

const priorityColors: Record<string, "rose" | "amber" | "blue" | "slate"> = {
  critical: "rose",
  high: "amber",
  medium: "blue",
  low: "slate",
};

export default function TestSuitesPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [testCases, setTestCases] = useState<TestCaseDB[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeView, setActiveView] = useState<"list" | "editor">("list");
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [selectedSuiteId, setSelectedSuiteId] = useState<string | null>(null);
  const [editingCase, setEditingCase] = useState<{ suiteId: string; caseId?: string; data?: Partial<TestCaseDB> } | null>(null);

  const projectId = user?.workspace_id || "";

  const loadSuites = useCallback(async () => {
    if (!projectId) return;
    try {
      const s = await getTestSuites(projectId);
      setSuites(s);
    } catch (err) {
      console.error("Failed to load test suites:", err);
    }
  }, [projectId]);

  const loadTestCases = useCallback(async (suiteId: string) => {
    try {
      const cases = await getTestCases(suiteId);
      setTestCases(cases);
    } catch (err) {
      console.error("Failed to load test cases:", err);
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    setLoading(true);
    loadSuites().finally(() => setLoading(false));
  }, [isAuthenticated, loadSuites]);

  useEffect(() => {
    if (selectedSuiteId) {
      loadTestCases(selectedSuiteId);
    } else if (suites.length > 0) {
      // Auto-select first suite
      const firstId = suites[0].id;
      setSelectedSuiteId(firstId);
      loadTestCases(firstId);
    }
  }, [selectedSuiteId, suites, loadTestCases]);

  const handleCreateSuite = async () => {
    const name = prompt("Enter suite name:");
    if (!name || !projectId) return;
    try {
      const created = await createTestSuite({
        name,
        project_id: projectId,
        type: "manual",
      });
      setSuites(prev => [...prev, created]);
      setSelectedSuiteId(created.id);
    } catch (err) {
      console.error("Failed to create suite:", err);
    }
  };

  const handleDeleteSuite = async (suiteId: string) => {
    if (!confirm("Delete this suite and all its test cases?")) return;
    try {
      await deleteTestSuite(suiteId);
      setSuites(prev => prev.filter(s => s.id !== suiteId));
      if (selectedSuiteId === suiteId) {
        setSelectedSuiteId(null);
        setTestCases([]);
      }
    } catch (err) {
      console.error("Failed to delete suite:", err);
    }
  };

  const handleRunExecution = (suiteId: string) => {
    router.push(`/execution?suiteId=${suiteId}`);
  };

  if (authLoading) return null;
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="max-w-md text-center">
          <CardContent className="pt-8 pb-8">
            <FlaskConical className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <h2 className="text-lg font-semibold text-slate-900">Sign in to view test suites</h2>
            <p className="text-sm text-slate-500 mt-1">Connect your account to manage test suites.</p>
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

  if (activeView === "editor" && editingCase) {
    return (
      <TestCaseEditor 
        suiteId={editingCase.suiteId}
        testCaseId={editingCase.caseId}
        initialData={editingCase.data}
        onSave={(updated) => {
          setTestCases(prev => prev.map(c => c.id === updated.id ? updated : c));
          setActiveView("list");
          setEditingCase(null);
        }}
        onCancel={() => {
          setActiveView("list");
          setEditingCase(null);
        }}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Test Library</h1>
          <p className="text-slate-500 mt-1">Manage your test suites, folders, and test cases.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleCreateSuite}>
            <Plus className="h-4 w-4 mr-2" />
            New Suite
          </Button>
          <Button onClick={() => {
            const suiteId = selectedSuiteId || suites[0]?.id;
            if (suiteId) {
              setEditingCase({ suiteId });
              setActiveView("editor");
            }
          }}>
            <Plus className="h-4 w-4 mr-2" />
            New Test Case
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6 h-[calc(100vh-200px)]">
        <div className="col-span-3 h-full">
          <TestSuiteFolderTree 
            projectId={projectId}
            onSelectFolder={(id) => setSelectedFolderId(id)}
            onSelectCase={(id) => setSelectedCaseId(id)}
          />
        </div>

        <div className="col-span-9 h-full overflow-hidden flex flex-col">
          <Tabs defaultValue="cases" className="h-full flex flex-col">
            <TabsList className="mb-4">
              <TabsTrigger value="cases">
                <TestTube className="h-4 w-4 mr-2" />
                Test Cases
              </TabsTrigger>
              <TabsTrigger value="suites">
                <FlaskConical className="h-4 w-4 mr-2" />
                Suites
              </TabsTrigger>
            </TabsList>

            <TabsContent value="cases" className="flex-1 overflow-y-auto">
              {testCases.length === 0 ? (
                <Card>
                  <CardContent className="flex flex-col items-center justify-center py-16">
                    <TestTube className="h-12 w-12 text-slate-300 mb-4" />
                    <h3 className="text-lg font-semibold text-slate-900">No test cases found</h3>
                    <p className="text-sm text-slate-500 mt-1">
                      Create a new test case or select a suite to see cases.
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-4">
                  {testCases.map((tc) => (
                    <Card key={tc.id} className={cn(
                      "transition-all cursor-pointer hover:border-slate-400",
                      selectedCaseId === tc.id && "border-blue-500 ring-1 ring-blue-500"
                    )} onClick={() => setSelectedCaseId(tc.id)}>
                      <CardContent className="p-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={cn(
                            "p-2 rounded-full",
                            priorityColors[tc.priority as keyof typeof priorityColors] === "rose" ? "bg-rose-100 text-rose-600" : 
                            priorityColors[tc.priority as keyof typeof priorityColors] === "amber" ? "bg-amber-100 text-amber-600" : 
                            "bg-blue-100 text-blue-600"
                          )}>
                            <TestTube className="h-4 w-4" />
                          </div>
                          <div>
                            <h4 className="text-sm font-medium text-slate-900">{tc.title}</h4>
                            <div className="flex items-center gap-2 mt-1">
                              <Badge tone="slate" className="text-[10px] px-1 py-0">
                                {tc.priority}
                              </Badge>
                              <span className="text-[10px] text-slate-400">• {tc.status}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingCase({ 
                                suiteId: tc.test_suite_id, 
                                caseId: tc.id, 
                                data: tc 
                              });
                              setActiveView("editor");
                            }}
                          >
                            Edit
                          </Button>
                          <Button variant="ghost" size="sm" className="text-blue-600"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRunExecution(tc.test_suite_id);
                            }}>
                            <Play className="h-3 w-3 mr-1" />
                            Run
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>

            <TabsContent value="suites" className="flex-1 overflow-y-auto">
              {suites.length === 0 ? (
                <Card>
                  <CardContent className="flex flex-col items-center justify-center py-16">
                    <FlaskConical className="h-12 w-12 text-slate-300 mb-4" />
                    <h3 className="text-lg font-semibold text-slate-900">No test suites yet</h3>
                    <p className="text-sm text-slate-500 mt-1">
                      Create a test suite to organize your test cases.
                    </p>
                    <Button className="mt-4" onClick={handleCreateSuite}>
                      <Plus className="h-4 w-4 mr-2" />
                      Create Suite
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-4">
                  {suites.map((suite) => (
                    <Card key={suite.id} className={cn(
                      "transition-all cursor-pointer hover:border-slate-400",
                      selectedSuiteId === suite.id && "border-blue-500 ring-1 ring-blue-500"
                    )} onClick={() => setSelectedSuiteId(suite.id)}>
                      <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-sm font-medium">{suite.name}</CardTitle>
                          <Button variant="ghost" size="icon" className="h-7 w-7 text-rose-500 hover:text-rose-700"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteSuite(suite.id);
                            }}>
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                        <CardDescription className="text-xs">{suite.description || "No description"}</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Badge tone="slate" className="text-[10px]">
                              {suite.type}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button variant="ghost" size="sm" className="text-xs"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedSuiteId(suite.id);
                              }}>
                              View Cases
                            </Button>
                            <Button variant="ghost" size="sm" className="text-xs text-blue-600"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRunExecution(suite.id);
                              }}>
                              <Play className="h-3 w-3 mr-1" />
                              Run
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}