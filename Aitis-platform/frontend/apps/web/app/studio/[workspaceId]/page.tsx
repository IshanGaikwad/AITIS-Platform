"use client";

import { useParams, useRouter } from "next/navigation";
import {
  FileText,
  Plus,
  Zap,
  Play,
  Layers,
  FlaskConical,
  Activity,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function ProjectOverviewPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = params.workspaceId as string;

  const quickActions = [
    {
      label: "Import Jira Story",
      description: "Fetch a story by key and generate test artifacts",
      icon: FileText,
      onClick: () => router.push(`/studio/${workspaceId}/requirements`),
    },
    {
      label: "Add Requirement",
      description: "Manually add a requirement or user story",
      icon: Plus,
      onClick: () => router.push(`/studio/${workspaceId}/requirements`),
    },
    {
      label: "Create Test Suite",
      description: "Organise test cases into a suite",
      icon: Layers,
      onClick: () => router.push(`/studio/${workspaceId}/test-suites`),
    },
    {
      label: "Add Test Case",
      description: "Write a new test case manually",
      icon: FlaskConical,
      onClick: () => router.push(`/studio/${workspaceId}/test-cases`),
    },
    {
      label: "Generate Test Cases",
      description: "Use AI to generate cases from requirements",
      icon: Zap,
      onClick: () => router.push(`/studio/${workspaceId}/test-cases`),
    },
    {
      label: "Start Test Run",
      description: "Run a test suite and track results",
      icon: Play,
      onClick: () => router.push(`/studio/${workspaceId}/execution`),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Welcome state */}
      <Card>
        <CardContent className="p-6 text-center">
          <Activity className="mx-auto mb-3 h-10 w-10 text-slate-300" />
          <h3 className="mb-1 text-base font-semibold text-slate-900">Project Overview</h3>
          <p className="text-sm text-slate-500">
            Get started by adding requirements, creating test suites, and running executions.
            Stats will appear here as your project grows.
          </p>
        </CardContent>
      </Card>

      {/* Quick actions */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold text-slate-700">Quick Actions</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {quickActions.map((action) => (
            <button
              key={action.label}
              onClick={action.onClick}
              className="flex items-start gap-3 rounded-lg border border-slate-200 p-4 text-left transition-colors hover:border-slate-300 hover:bg-slate-50"
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-100">
                <action.icon className="h-4 w-4 text-slate-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-900">{action.label}</p>
                <p className="mt-0.5 text-xs text-slate-500">{action.description}</p>
              </div>
            </button>
          ))}
        </CardContent>
      </Card>

      {/* Navigation shortcuts */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "Requirements", href: `/studio/${workspaceId}/requirements`, icon: FileText },
          { label: "Test Cases", href: `/studio/${workspaceId}/test-cases`, icon: FlaskConical },
          { label: "Test Suites", href: `/studio/${workspaceId}/test-suites`, icon: Layers },
          { label: "Execution", href: `/studio/${workspaceId}/execution`, icon: Play },
        ].map((item) => (
          <Button
            key={item.label}
            variant="outline"
            className="h-auto flex-col gap-1 py-4"
            onClick={() => router.push(item.href)}
          >
            <item.icon className="h-5 w-5" />
            <span className="text-xs">{item.label}</span>
          </Button>
        ))}
      </div>
    </div>
  );
}
