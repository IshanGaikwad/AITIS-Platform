"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth";

export default function LandingPage() {
  const { user, isAuthenticated, login, logout } = useAuth();

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      {/* Header */}
      <header className="mx-auto max-w-7xl px-6 py-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Badge tone="blue">AI</Badge>
          <span className="text-lg font-semibold">AI Test Intelligence</span>
        </div>

        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <>
              <div className="flex items-center gap-2">
                {user?.picture && (
                  <img
                    src={user.picture}
                    alt={user.name || user.email}
                    className="w-8 h-8 rounded-full"
                  />
                )}
                <span className="text-sm text-slate-700">
                  {user?.name || user?.email}
                </span>
              </div>
              <Link
                href="/studio"
                className="rounded-2xl bg-slate-950 px-5 py-2.5 text-sm font-medium text-white hover:bg-slate-800"
              >
                Open Test Generator Studio
              </Link>
              <Link
                href="/execution"
                className="rounded-2xl border border-slate-950 px-5 py-2.5 text-sm font-medium text-slate-950 hover:bg-slate-100"
              >
                Test Execution Studio
              </Link>
              <button
                onClick={logout}
                className="rounded-2xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <Link
                href="/studio"
                className="rounded-2xl bg-slate-950 px-5 py-2.5 text-sm font-medium text-white hover:bg-slate-800"
              >
                Open Test Generator Studio
              </Link>
              <Link
                href="/execution"
                className="rounded-2xl border border-slate-950 px-5 py-2.5 text-sm font-medium text-slate-950 hover:bg-slate-100"
              >
                Test Execution Studio
              </Link>
              <button
                onClick={login}
                className="rounded-2xl bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
              >
                Login
              </button>
            </>
          )}
        </div>
      </header>

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

          <div className="mt-8 flex gap-4">
            <Link
              href="/studio"
              className="rounded-2xl bg-slate-950 px-6 py-3 text-sm font-semibold text-white hover:bg-slate-800"
            >
              Open Test Generator
            </Link>

            <a
              href="#how-it-works"
              className="rounded-2xl border border-slate-300 px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
            >
              How it Works
            </a>
          </div>
        </div>

        {/* Visual placeholder */}
        <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="space-y-4 text-sm text-slate-700">
            <div className="rounded-xl bg-slate-50 p-4">
              Jira Story Imported
            </div>
            <div className="rounded-xl bg-slate-50 p-4">
              Acceptance Criteria Refined
            </div>
            <div className="rounded-xl bg-slate-50 p-4">
              Coverage‑Aware Test Cases Generated
            </div>
            <div className="rounded-xl bg-slate-50 p-4">
              Gherkin & Automation Code Ready
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section
        id="how-it-works"
        className="mx-auto max-w-7xl px-6 py-20"
      >
        <h2 className="text-3xl font-bold text-slate-950">
          How AI Test Intelligence Works
        </h2>

        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {[
            {
              title: "Import from Jira",
              description:
                "Search Jira or fetch a story by key. Automatically extract descriptions and acceptance criteria.",
            },
            {
              title: "Refine Acceptance Criteria",
              description:
                "Edit, reorder, and normalize acceptance criteria using the built‑in AC editor.",
            },
            {
              title: "Generate with Coverage",
              description:
                "Produce intent models, AC‑mapped test cases, Gherkin scenarios, and automation code with coverage insights.",
            },
          ].map((item) => (
            <div
              key={item.title}
              className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <h3 className="text-lg font-semibold text-slate-900">
                {item.title}
              </h3>
              <p className="mt-2 text-sm text-slate-600">
                {item.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Value props */}
      <section className="mx-auto max-w-7xl px-6 py-20">
        <h2 className="text-3xl font-bold text-slate-950">
          Why Teams Use It
        </h2>

        <div className="mt-10 grid gap-6 md:grid-cols-2">
          {[
            "Acceptance‑criteria‑driven test coverage",
            "Clear traceability from requirements to automation",
            "Reduced manual test design effort",
            "Consistent test quality across teams",
            "Jira‑native workflows",
            "Automation‑framework ready output",
          ].map((benefit) => (
            <div
              key={benefit}
              className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-700"
            >
              {benefit}
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-slate-950 text-white">
        <div className="mx-auto max-w-7xl px-6 py-20 text-center">
          <h2 className="text-4xl font-bold">
            Ready to Generate Smarter Tests?
          </h2>
          <p className="mt-4 text-slate-300">
            Start with a Jira story and see coverage‑aware tests in minutes.
          </p>

          <Link
            href="/studio"
            className="mt-8 inline-block rounded-2xl bg-white px-8 py-3 text-sm font-semibold text-slate-950 hover:bg-slate-200"
          >
            Generate Test Artifacts
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-6 py-6 text-sm text-slate-500">
          © {new Date().getFullYear()} AI Test Intelligence
        </div>
      </footer>
    </main>
  );
}