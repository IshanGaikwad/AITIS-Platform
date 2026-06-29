"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { getProjects, getProjectStats } from "@/lib/api";
import type { Project, ProjectStats } from "@/lib/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  FileText,
  TestTube,
  Play,
  Bug,
  TrendingUp,
  ArrowRight,
  Code2,
  Zap,
  Shield,
  BarChart3,
} from "lucide-react";

function LandingPage() {
  const { login } = useAuth();

  async function handleTryDemo() {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
      const res = await fetch(`${apiBase}/auth/demo`, { method: "POST" });
      if (!res.ok) throw new Error("Demo unavailable");
      const data = await res.json();
      localStorage.setItem("aitis_access_token", data.access_token);
      if (data.refresh_token) localStorage.setItem("aitis_refresh_token", data.refresh_token);
      window.location.href = "/dashboard";
    } catch {
      alert("Demo is temporarily unavailable. Please try again later.");
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      {/* Header */}
      <header className="mx-auto max-w-7xl px-6 py-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-xs font-bold text-white">
            AI
          </div>
          <span className="text-lg font-semibold">AITIS</span>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/studio"
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            Try Studio
          </Link>
          <Link
            href="/login"
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Login / Sign Up
          </Link>
        </div>
      </header>

      {/* Demo notice bar */}
      <div className="bg-slate-100 border-b border-slate-200 text-center py-2 px-6 text-xs text-slate-500">
        Explore AITIS with sample data.{" "}
        <button
          onClick={handleTryDemo}
          className="underline underline-offset-2 hover:text-slate-700 font-medium"
        >
          No account required.
        </button>
      </div>

      {/* Hero */}
      <section className="mx-auto max-w-7xl px-6 py-20 grid gap-12 lg:grid-cols-2 items-center">
        <div>
          <Badge tone="green">Jira → Tests → Automation</Badge>
          <h1 className="mt-6 text-5xl font-bold tracking-tight text-slate-950">
            Turn Jira Stories into
            <br />
            <span className="text-slate-700">Coverage‑Aware Test Assets</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg text-slate-600">
            AI Test Intelligence transforms Jira user stories into intent models,
            acceptance‑criteria‑mapped test cases, Gherkin scenarios, and
            automation-ready code — all with full traceability.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              href="/studio"
              className="rounded-lg bg-slate-900 px-6 py-3 text-sm font-semibold text-white hover:bg-slate-800 inline-flex items-center gap-2"
            >
              Open Test Generator <ArrowRight className="h-4 w-4" />
            </Link>
            <button
              onClick={handleTryDemo}
              className="rounded-lg border border-slate-900 px-6 py-3 text-sm font-semibold text-slate-900 hover:bg-slate-50"
            >
              Try Demo — No Sign Up Required
            </button>
            <a
              href="#how-it-works"
              className="rounded-lg border border-slate-300 px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              How it Works
            </a>
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="space-y-4 text-sm text-slate-700">
            {[
              "Jira Story Imported",
              "Acceptance Criteria Refined",
              "Coverage‑Aware Test Cases Generated",
              "Gherkin & Automation Code Ready",
            ].map((step, i) => (
              <div key={i} className="flex items-center gap-3 rounded-xl bg-slate-50 p-4">
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white">
                  {i + 1}
                </div>
                {step}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="mx-auto max-w-7xl px-6 py-20">
        <h2 className="text-3xl font-bold text-slate-950">How It Works</h2>
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {[
            {
              title: "Import from Jira",
              description:
                "Search Jira or fetch a story by key. Automatically extract descriptions and acceptance criteria.",
              icon: FileText,
            },
            {
              title: "Refine Acceptance Criteria",
              description:
                "Edit, reorder, and normalize acceptance criteria using the built‑in AC editor.",
              icon: Zap,
            },
            {
              title: "Generate with Coverage",
              description:
                "Produce intent models, AC‑mapped test cases, Gherkin scenarios, and automation code with coverage insights.",
              icon: BarChart3,
            },
          ].map((item) => (
            <div
              key={item.title}
              className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <item.icon className="h-8 w-8 text-slate-700 mb-3" />
              <h3 className="text-lg font-semibold text-slate-900">{item.title}</h3>
              <p className="mt-2 text-sm text-slate-600">{item.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Value props */}
      <section className="mx-auto max-w-7xl px-6 py-20">
        <h2 className="text-3xl font-bold text-slate-950">Why Teams Use It</h2>
        <div className="mt-10 grid gap-6 md:grid-cols-2">
          {[
            "Acceptance‑criteria‑driven test coverage",
            "Clear traceability from requirements to automation",
            "Reduced manual test design effort",
            "Consistent test quality across teams",
            "Jira‑native workflows",
            "Automation‑framework ready output",
          ].map((benefit) => (
            <div key={benefit} className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-700 flex items-center gap-2">
              <Shield className="h-4 w-4 text-green-600 shrink-0" />
              {benefit}
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-slate-950 text-white">
        <div className="mx-auto max-w-7xl px-6 py-20 text-center">
          <h2 className="text-4xl font-bold">Ready to Generate Smarter Tests?</h2>
          <p className="mt-4 text-slate-300">
            Start with a Jira story and see coverage‑aware tests in minutes.
          </p>
          <Link
            href="/studio"
            className="mt-8 inline-block rounded-lg bg-white px-8 py-3 text-sm font-semibold text-slate-950 hover:bg-slate-200"
          >
            Generate Test Artifacts
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-6 py-6 text-sm text-slate-500">
          © {new Date().getFullYear()} AITIS — AI Test Intelligence System
        </div>
      </footer>
    </main>
  );
}

function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const projects: Project[] = await getProjects(user?.workspace_id || "");
        if (projects.length > 0) {
          const s = await getProjectStats(projects[0].id);
          setStats(s);
        }
      } catch {
        // Stats unavailable — leave as null
      } finally {
        setLoading(false);
      }
    }
    if (user?.workspace_id) {
      fetchStats();
    } else {
      setLoading(false);
    }
  }, [user?.workspace_id]);

  const statCards = [
    { label: "Requirements", value: loading ? "…" : stats?.total_requirements ?? "—", icon: FileText, href: "/requirements", color: "text-blue-600" },
    { label: "Test Suites", value: loading ? "…" : stats?.total_test_cases ?? "—", icon: TestTube, href: "/test-suites", color: "text-purple-600" },
    { label: "Executions", value: "—", icon: Play, href: "/execution", color: "text-green-600" },
    { label: "Defects", value: "—", icon: Bug, href: "/defects", color: "text-red-600" },
  ];

  return (
    <div className="space-y-8">
      {/* Welcome */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          Welcome back{user?.name ? `, ${user.name.split(" ")[0]}` : ""}
        </h1>
        <p className="text-slate-500 mt-1">Here&apos;s an overview of your testing workspace.</p>
      </div>

      {/* Stats grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => (
          <Link key={stat.label} href={stat.href}>
            <Card className="hover:shadow-md transition-shadow cursor-pointer">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">{stat.label}</CardTitle>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Quick actions */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Jump into your workflow</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {[
              { label: "Import from Jira", href: "/studio", icon: Code2, description: "Fetch a Jira story and generate test artifacts" },
              { label: "View Test Suites", href: "/test-suites", icon: TestTube, description: "Browse and manage your test suites" },
              { label: "Run Execution", href: "/execution", icon: Play, description: "Execute tests and view results" },
            ].map((action) => (
              <Link
                key={action.label}
                href={action.href}
                className="flex items-center gap-4 rounded-lg border border-slate-200 p-4 hover:bg-slate-50 transition-colors"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100">
                  <action.icon className="h-5 w-5 text-slate-700" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-900">{action.label}</p>
                  <p className="text-xs text-slate-500">{action.description}</p>
                </div>
                <ArrowRight className="h-4 w-4 text-slate-400" />
              </Link>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Your latest actions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <TrendingUp className="h-10 w-10 text-slate-300 mb-3" />
              <p className="text-sm text-slate-500">No recent activity yet.</p>
              <p className="text-xs text-slate-400 mt-1">
                Start by importing a Jira story or creating a requirement.
              </p>
              <Link href="/studio">
                <Button variant="outline" size="sm" className="mt-4">
                  Go to Studio
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function HomePage() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return null;
  return isAuthenticated ? <DashboardPage /> : <LandingPage />;
}