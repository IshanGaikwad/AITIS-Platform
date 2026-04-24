"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Section } from "@/components/ui/section";
import { getApiBaseUrl, getStories } from "@/lib/api";
import type { SavedStory } from "@/lib/api";

type AutomationFramework = "Playwright" | "Cypress" | "Selenium" | "API Test";

interface TestExecutionConfig {
  selectedStoryId: number | null;
  framework: AutomationFramework;
  bddEnabled: boolean;
  generatedCode: string | null;
}

const frameworkTemplates: Record<AutomationFramework, string> = {
  Playwright: `import { test, expect } from '@playwright/test';

describe('BDD Test Suite', () => {
  let page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();
  });

  // Feature: Test scenarios generated from acceptance criteria
  
  test('Given: Initial state, When: User action, Then: Expected outcome', async () => {
    // Implement test steps
  });
});`,
  Cypress: `describe('BDD Test Suite', () => {
  beforeEach(() => {
    // Setup before each test
  });

  // Feature: Test scenarios generated from acceptance criteria

  it('Given: Initial state, When: User action, Then: Expected outcome', () => {
    // Implement test steps
  });
});`,
  Selenium: `import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By

class TestBDDSuite(unittest.TestCase):
    
    def setUp(self):
        self.driver = webdriver.Chrome()
    
    # Feature: Test scenarios generated from acceptance criteria
    
    def test_scenario(self):
        '''Given: Initial state, When: User action, Then: Expected outcome'''
        # Implement test steps
        pass
    
    def tearDown(self):
        self.driver.quit()`,
  "API Test": `import requests
import pytest

class TestAPIBDDSuite:
    
    BASE_URL = "https://api.example.com"
    
    # Feature: API test scenarios generated from acceptance criteria
    
    def test_api_scenario(self):
        '''Given: Initial state, When: User action, Then: Expected outcome'''
        # Implement API test
        pass
`,
};

export default function TestExecutionStudio() {
  const [stories, setStories] = useState<SavedStory[]>([]);
  const [config, setConfig] = useState<TestExecutionConfig>({
    selectedStoryId: null,
    framework: "Playwright",
    bddEnabled: true,
    generatedCode: null,
  });

  const [loading, setLoading] = useState(true);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function bootstrap() {
      setBootstrapping(true);
      setError(null);

      try {
        const savedStories = await getStories();
        setStories(savedStories);
        if (savedStories.length > 0) {
          setConfig((prev) => ({
            ...prev,
            selectedStoryId: savedStories[0].id,
          }));
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load test cases"
        );
      } finally {
        setBootstrapping(false);
      }
    }

    bootstrap();
  }, []);

  function handleGenerateBDD() {
    setLoading(true);
    setError(null);

    try {
      // Get template based on selected framework
      const template = frameworkTemplates[config.framework];

      // In a real implementation, you would:
      // 1. Fetch the test cases from the selected story
      // 2. Transform them into BDD format
      // 3. Generate framework-specific code

      const generatedCode = `${template}

// Generated from Test Intelligence Platform
// Framework: ${config.framework}
// BDD Enabled: ${config.bddEnabled}
// Generated: ${new Date().toLocaleString()}`;

      setConfig((prev) => ({
        ...prev,
        generatedCode,
      }));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to generate BDD framework"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Badge tone="blue">AI Test Intelligence</Badge>
              <Badge tone="purple">Test Execution</Badge>
              <Badge tone="amber">BDD Framework</Badge>
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-slate-950">
              Test Execution Studio
            </h1>
            <p className="mt-3 max-w-3xl text-base text-slate-600">
              Pull generated test cases, create BDD frameworks, and prepare automation
              code for your preferred testing framework. Execute tests with full traceability
              from Jira stories.
            </p>
            <p className="mt-2 text-sm text-slate-500">
              API base URL: <span className="font-medium text-slate-700">{getApiBaseUrl()}</span>
            </p>

            <div className="mt-6">
              <Link
                href="/"
                className="text-sm font-medium text-slate-600 hover:text-slate-900"
              >
                ← Back to Home
              </Link>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Execution Workflow
            </h2>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              {[
                "1. Select Test Case",
                "2. Choose Framework",
                "3. Enable BDD",
                "4. Generate Code",
                "5. Review Artifacts",
                "6. Export & Execute",
              ].map((step) => (
                <div key={step} className="rounded-2xl bg-slate-50 p-3 text-slate-700">
                  {step}
                </div>
              ))}
            </div>
            <div className="mt-4 rounded-2xl bg-emerald-50 p-4 text-sm text-emerald-800">
              <strong>Status:</strong> {bootstrapping ? "Loading test cases..." : "Ready"}
            </div>
          </div>
        </div>

        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
          <div className="space-y-6">
            <Section
              title="Test Selection"
              subtitle="Select test cases from Test Generator"
            >
              <div className="space-y-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Generated Test Cases
                  </label>
                  <select
                    value={config.selectedStoryId ?? ""}
                    onChange={(event) =>
                      setConfig((prev) => ({
                        ...prev,
                        selectedStoryId: Number(event.target.value),
                      }))
                    }
                    className="w-full rounded-2xl border border-slate-200 px-4 py-2.5 outline-none transition focus:border-slate-400"
                  >
                    <option value="">Select a test case</option>
                    {stories.map((story) => (
                      <option key={story.id} value={story.id}>
                        {story.title}
                      </option>
                    ))}
                  </select>
                </div>

                {config.selectedStoryId && (
                  <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
                    <strong>Selected:</strong> {stories.find((s) => s.id === config.selectedStoryId)?.title}
                  </div>
                )}
              </div>
            </Section>

            <Section
              title="Framework Configuration"
              subtitle="Choose automation framework and options"
            >
              <div className="space-y-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">
                    Automation Framework
                  </label>
                  <select
                    value={config.framework}
                    onChange={(event) =>
                      setConfig((prev) => ({
                        ...prev,
                        framework: event.target.value as AutomationFramework,
                      }))
                    }
                    className="w-full rounded-2xl border border-slate-200 px-4 py-2.5 outline-none transition focus:border-slate-400"
                  >
                    <option>Playwright</option>
                    <option>Cypress</option>
                    <option>Selenium</option>
                    <option>API Test</option>
                  </select>
                </div>

                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="bdd-enabled"
                    checked={config.bddEnabled}
                    onChange={(event) =>
                      setConfig((prev) => ({
                        ...prev,
                        bddEnabled: event.target.checked,
                      }))
                    }
                    className="h-4 w-4 rounded border-slate-300"
                  />
                  <label
                    htmlFor="bdd-enabled"
                    className="text-sm font-medium text-slate-700"
                  >
                    Enable BDD (Given-When-Then)
                  </label>
                </div>

                <button
                  onClick={handleGenerateBDD}
                  disabled={loading || !config.selectedStoryId}
                  className="w-full rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                >
                  {loading ? "Generating..." : "Generate BDD Framework"}
                </button>
              </div>
            </Section>

            <Section
              title="Framework Info"
              subtitle="Details about selected framework"
            >
              <div className="space-y-3 text-sm text-slate-700">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>Framework:</strong> {config.framework}
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>BDD Format:</strong> {config.bddEnabled ? "Enabled" : "Disabled"}
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>Test Cases:</strong> {stories.length}
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>Status:</strong> {config.generatedCode ? "Generated" : "Pending"}
                </div>
              </div>
            </Section>
          </div>

          <div className="space-y-6">
            {config.generatedCode ? (
              <Section
                title="Generated Framework Code"
                subtitle="BDD framework code ready for integration"
              >
                <div className="rounded-3xl bg-slate-950 p-5 text-sm text-slate-100">
                  <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-xs leading-relaxed">
                    {config.generatedCode}
                  </pre>
                </div>

                <div className="mt-4 flex gap-2">
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(config.generatedCode || "");
                      alert("Code copied to clipboard!");
                    }}
                    className="flex-1 rounded-2xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Copy Code
                  </button>
                  <button
                    onClick={() => {
                      const element = document.createElement("a");
                      const file = new Blob([config.generatedCode || ""], {
                        type: "text/plain",
                      });
                      element.href = URL.createObjectURL(file);
                      element.download = `test-suite.${config.framework === "Playwright" ? "ts" : config.framework === "Cypress" ? "js" : "py"}`;
                      document.body.appendChild(element);
                      element.click();
                      document.body.removeChild(element);
                    }}
                    className="flex-1 rounded-2xl bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
                  >
                    Download
                  </button>
                </div>
              </Section>
            ) : (
              <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm text-center">
                <div className="text-slate-500">
                  <p className="font-medium">No framework generated yet</p>
                  <p className="mt-2 text-sm">
                    Select a test case and click "Generate BDD Framework" to create automation code.
                  </p>
                </div>
              </div>
            )}

            <Section
              title="Execution Guide"
              subtitle="Steps to execute the generated tests"
            >
              <div className="space-y-3 text-sm text-slate-700">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>1. Install Dependencies</strong>
                  <p className="mt-1 text-xs text-slate-600">
                    {config.framework === "Playwright"
                      ? "npm install @playwright/test"
                      : config.framework === "Cypress"
                      ? "npm install cypress"
                      : config.framework === "Selenium"
                      ? "pip install selenium"
                      : "pip install requests pytest"}
                  </p>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>2. Add Test File</strong>
                  <p className="mt-1 text-xs text-slate-600">
                    Copy the generated code to your test suite
                  </p>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <strong>3. Run Tests</strong>
                  <p className="mt-1 text-xs text-slate-600">
                    {config.framework === "Playwright"
                      ? "npx playwright test"
                      : config.framework === "Cypress"
                      ? "npx cypress run"
                      : "pytest"}
                  </p>
                </div>
              </div>
            </Section>
          </div>
        </div>
      </div>
    </main>
  );
}
