// ── AITIS Playwright Configuration Template ──────────────────────────
// This config is injected into the execution container.
// Environment variables control browser, base URL, timeouts, etc.
// ─────────────────────────────────────────────────────────────────────

import { defineConfig, devices } from '@playwright/test';

const browser = process.env.BROWSER || 'chromium';
const baseURL = process.env.BASE_URL || 'http://localhost:3000';
const headless = process.env.HEADLESS !== 'false';
const testTimeout = parseInt(process.env.TEST_TIMEOUT || '30000', 10);
const expectTimeout = parseInt(process.env.EXPECT_TIMEOUT || '10000', 10);
const retries = parseInt(process.env.RETRIES || '0', 10);
const workers = parseInt(process.env.WORKERS || '1', 10);

// Browser project configurations
const projects = {
  chromium: {
    name: 'chromium',
    use: { ...devices['Desktop Chrome'], channel: 'chromium' },
  },
  firefox: {
    name: 'firefox',
    use: { ...devices['Desktop Firefox'] },
  },
  webkit: {
    name: 'webkit',
    use: { ...devices['Desktop Safari'] },
  },
};

// Select the project based on BROWSER env var
const selectedProject = projects[browser] || projects.chromium;

export default defineConfig({
  // Test directory
  testDir: './tests',
  testMatch: ['**/*.spec.ts', '**/*.test.ts', '**/*.spec.js', '**/*.test.js'],

  // Timeouts
  timeout: testTimeout,
  expect: { timeout: expectTimeout },

  // Execution
  fullyParallel: workers > 1,
  retries: retries,
  workers: workers,
  reporter: [
    ['json', { outputFile: './results/results.json' }],
    ['list'],
  ],

  // Use settings
  use: {
    baseURL,
    headless,
    // Artifacts
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
    // Output paths
    screenshotOption: {
      path: './artifacts/screenshot-{testId}-{timestamp}.png',
    },
    videoOption: {
      dir: './artifacts/videos/',
    },
    traceOption: {
      dir: './artifacts/traces/',
    },
    // Context options
    viewport: { width: 1280, height: 720 },
    locale: 'en-US',
    timezoneId: 'America/New_York',
    // Navigation
    navigationTimeout: testTimeout,
    actionTimeout: expectTimeout,
  },

  // Project configuration
  projects: [selectedProject],

  // Output
  outputDir: './artifacts/',
});
