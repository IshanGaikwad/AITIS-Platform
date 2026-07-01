"use client";

import Link from "next/link";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useAuth } from "@/lib/auth";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Code2,
  FolderPlus,
  TestTube,
  LayoutDashboard,
  ArrowRight,
  Sparkles,
  FileText,
  BarChart3,
} from "lucide-react";

interface StartStep {
  step: number;
  title: string;
  description: string;
  icon: typeof Code2;
}

const startSteps: StartStep[] = [
  {
    step: 1,
    title: "Import a Jira story",
    description:
      "Pull a user story straight from Jira and let AITIS extract its description and acceptance criteria.",
    icon: Code2,
  },
  {
    step: 2,
    title: "Create a workspace",
    description:
      "Set up a workspace to organize your requirements, test suites, and automation in one place.",
    icon: FolderPlus,
  },
  {
    step: 3,
    title: "Generate test assets",
    description:
      "Produce coverage-aware test cases, Gherkin scenarios, and automation code from your requirements.",
    icon: TestTube,
  },
];

const shortcuts = [
  {
    label: "Requirements",
    href: "/requirements",
    icon: FileText,
    description: "Capture and refine acceptance criteria, then trace them to your test cases.",
  },
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
    description: "Track workspace health, release readiness, and defect trends at a glance.",
  },
  {
    label: "Insights",
    href: "/insights",
    icon: BarChart3,
    description: "Analyze coverage, failures, and quality trends across your test runs.",
  },
];

export default function HomePage() {
  const { user } = useAuth();
  const firstName = user?.name ? user.name.split(" ")[0] : null;

  return (
    <ProtectedRoute>
      <div className="space-y-8">
        {/* Hero / welcome */}
        <section className="relative overflow-hidden rounded-3xl border border-slate-200 bg-gradient-to-br from-slate-900 to-slate-700 p-8 text-white shadow-sm">
          <div className="relative z-10 max-w-2xl">
            <Badge tone="green" className="mb-4 bg-white/10 text-white">
              <Sparkles className="mr-1 h-3 w-3" /> Welcome to AITIS
            </Badge>
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
              {firstName ? `Welcome, ${firstName}.` : "Welcome."}
            </h1>
            <p className="mt-3 text-slate-300">
              Turn Jira stories into coverage-aware test assets. Your project is empty —
              start by importing a story or creating a workspace below.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Button asChild className="bg-white text-slate-900 hover:bg-slate-100">
                <Link href="/studio">
                  Open Studio <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button
                asChild
                variant="outline"
                className="border-white/30 bg-transparent text-white hover:bg-white/10"
              >
                <Link href="/workspaces">Create a Workspace</Link>
              </Button>
            </div>
          </div>
          {/* Decorative grid glow */}
          <div className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white/5 blur-3xl" />
        </section>

        {/* Get started steps */}
        <section>
          <h2 className="text-lg font-semibold text-slate-900">Get started</h2>
          <p className="text-sm text-slate-500">Three steps to your first test suite.</p>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            {startSteps.map((s) => (
              <Card key={s.step}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-slate-700">
                      <s.icon className="h-5 w-5" />
                    </div>
                    <span className="text-2xl font-bold text-slate-200">{s.step}</span>
                  </div>
                  <CardTitle className="mt-3 text-base">{s.title}</CardTitle>
                  <CardDescription>{s.description}</CardDescription>
                </CardHeader>
              </Card>
            ))}
          </div>
        </section>

        {/* Quick shortcuts */}
        <section>
          <div className="grid gap-3 sm:grid-cols-3">
            {shortcuts.map((s) => (
              <Link
                key={s.href}
                href={s.href}
                className="rounded-xl border border-slate-200 bg-white p-4 transition-colors hover:bg-slate-50"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-slate-700">
                    <s.icon className="h-4 w-4" />
                  </div>
                  <span className="text-sm font-medium text-slate-900">{s.label}</span>
                </div>
                <p className="mt-2 text-xs text-slate-500">{s.description}</p>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </ProtectedRoute>
  );
}
