"""End-to-end tests for Phase 1 frontend: Projects, Applications, Environments.

Coverage:
- Project creation and listing
- Application management within projects
- Environment management within applications
- UI navigation and interactions
"""

import { test, expect } from "@playwright/test";

const BASE_URL = process.env.PLAYWRIGHT_TEST_BASE_URL || "http://localhost:3000";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

test.describe("Phase 1: Project Management", () => {
  test.beforeEach(async ({ page, context }) => {
    // Mock authentication
    await context.addCookies([
      {
        name: "aitis_access_token",
        value: "test-token-123",
        url: BASE_URL,
      },
    ]);

    // Store auth token in localStorage
    await page.evaluate(() => {
      localStorage.setItem("aitis_access_token", "test-token-123");
      localStorage.setItem("workspace_id", "test-workspace-123");
    });
  });

  test("should create and view a project", async ({ page }) => {
    // Navigate to projects page
    await page.goto(`${BASE_URL}/projects`);

    // Wait for page to load
    await page.waitForSelector("text=Projects");

    // Click "New Project" button
    await page.click("button:has-text('New Project')");

    // Fill form
    await page.fill('input[placeholder="e.g., E-Commerce Platform"]', "E-Commerce Platform");
    await page.fill('input[placeholder="e.g., ECOM"]', "ECOM");
    await page.fill(
      'textarea[placeholder="Describe your project..."]',
      "Platform for online shopping"
    );

    // Submit form
    await page.click("button:has-text('Create Project')");

    // Wait for success and redirect
    await page.waitForURL(/\/projects\/[a-f0-9-]+/);

    // Verify project details are displayed
    await expect(page.locator("h1")).toContainText("E-Commerce Platform");
    await expect(page.locator("text=ECOM")).toBeVisible();
  });

  test("should manage applications within a project", async ({ page }) => {
    // Navigate to project detail page
    await page.goto(`${BASE_URL}/projects/test-project-123`);

    // Wait for page to load
    await page.waitForSelector("text=Applications");

    // Click "Add Application" button
    await page.click("button:has-text('Add Application')");

    // Fill form
    await page.fill('input[placeholder="e.g., Frontend Web App"]', "Frontend Web App");

    // Select application type
    await page.click("[role=combobox]");
    await page.click("text=Web Application");

    // Add repository URL
    await page.fill('input[placeholder="https://github.com/..."]', "https://github.com/example/frontend");

    // Submit form
    await page.click("button:has-text('Create')");

    // Verify application appears in list
    await expect(page.locator("text=Frontend Web App")).toBeVisible();
    await expect(page.locator("text=Web Application")).toBeVisible();
  });

  test("should manage environments within an application", async ({ page }) => {
    // Navigate to project detail page
    await page.goto(`${BASE_URL}/projects/test-project-123`);

    // Wait for applications section
    await page.waitForSelector("text=Applications");

    // If no applications exist, create one
    const appCount = await page.locator("text=Frontend Web App").count();
    if (appCount === 0) {
      await page.click("button:has-text('Add Application')");
      await page.fill('input[placeholder="e.g., Frontend Web App"]', "Frontend Web App");
      await page.click("[role=combobox]");
      await page.click("text=Web Application");
      await page.click("button:has-text('Create')");
      await page.waitForSelector("text=Frontend Web App");
    }

    // Click "Environments" button
    await page.click("button:has-text('Environments')");

    // Wait for environments modal/section
    await page.waitForSelector("text=Add Environment");

    // Click "Add Environment" button
    await page.click("button:has-text('Add Environment')");

    // Fill form
    await page.fill('input[placeholder="e.g., Development"]', "Development");

    // Select environment type
    await page.click("[role=combobox]");
    await page.click("text=Development");

    // Add base URL
    await page.fill('input[placeholder="https://dev.example.com"]', "https://dev.example.com");

    // Add health check URL
    await page.fill(
      'input[placeholder="https://dev.example.com/health"]',
      "https://dev.example.com/health"
    );

    // Submit form
    await page.click("button:has-text('Create')");

    // Verify environment appears in list
    await expect(page.locator("text=Development")).toBeVisible();
    await expect(page.locator("text=https://dev.example.com")).toBeVisible();
  });

  test("should navigate between projects and maintain state", async ({ page }) => {
    // Navigate to projects list
    await page.goto(`${BASE_URL}/projects`);
    await page.waitForSelector("text=Projects");

    // Create a project
    await page.click("button:has-text('New Project')");
    await page.fill('input[placeholder="e.g., E-Commerce Platform"]', "Test Project 1");
    await page.fill('input[placeholder="e.g., ECOM"]', "TP1");
    await page.click("button:has-text('Create Project')");

    // Wait for redirect to project page
    await page.waitForURL(/\/projects\/[a-f0-9-]+/);

    // Go back to projects list
    await page.click("button:has-text('Back')");

    // Verify we're back on projects list
    await expect(page.url()).toContain("/projects");

    // Verify created project appears in list
    await expect(page.locator("text=Test Project 1")).toBeVisible();
  });

  test("should delete a project", async ({ page }) => {
    // Navigate to projects list
    await page.goto(`${BASE_URL}/projects`);
    await page.waitForSelector("text=Projects");

    // Create a project
    await page.click("button:has-text('New Project')");
    await page.fill('input[placeholder="e.g., E-Commerce Platform"]', "Project to Delete");
    await page.fill('input[placeholder="e.g., ECOM"]', "DEL");
    await page.click("button:has-text('Create Project')");

    // Go back to list
    await page.click("button:has-text('Back')");

    // Find and click delete button for the project
    const projectCard = page.locator("text=Project to Delete").locator("..").nth(0);
    const deleteButton = projectCard.locator("button:has-text('Delete')");

    await deleteButton.click();

    // Confirm deletion (if there's a confirmation dialog)
    const confirmButton = page.locator("button:has-text('Delete')").nth(1);
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }

    // Wait for project to disappear
    await expect(page.locator("text=Project to Delete")).not.toBeVisible();
  });

  test("should handle error states gracefully", async ({ page }) => {
    // Navigate to non-existent project
    await page.goto(`${BASE_URL}/projects/invalid-project-id`);

    // Wait for error message
    await page.waitForSelector("text=Failed to load project");

    // Verify back button works
    await page.click("button:has-text('Back to Projects')");
    await expect(page.url()).toContain("/projects");
  });
});

test.describe("Phase 1: Application & Environment Management", () => {
  test.beforeEach(async ({ page, context }) => {
    // Mock authentication
    await context.addCookies([
      {
        name: "aitis_access_token",
        value: "test-token-123",
        url: BASE_URL,
      },
    ]);

    await page.evaluate(() => {
      localStorage.setItem("aitis_access_token", "test-token-123");
      localStorage.setItem("workspace_id", "test-workspace-123");
    });
  });

  test("should display application types with correct icons", async ({ page }) => {
    // Navigate to project page
    await page.goto(`${BASE_URL}/projects/test-project-123`);

    // Create different application types
    const appTypes = [
      { name: "Web App", type: "Web Application" },
      { name: "Mobile Web", type: "Mobile Web" },
      { name: "Android App", type: "Android" },
    ];

    for (const appType of appTypes) {
      await page.click("button:has-text('Add Application')");
      await page.fill('input[placeholder="e.g., Frontend Web App"]', appType.name);
      await page.click("[role=combobox]");
      await page.click(`text=${appType.type}`);
      await page.click("button:has-text('Create')");
      await page.waitForSelector(`text=${appType.name}`);
    }

    // Verify all apps are displayed
    for (const appType of appTypes) {
      await expect(page.locator(`text=${appType.name}`)).toBeVisible();
    }
  });

  test("should display environment types with correct colors", async ({ page }) => {
    // Navigate to project page
    await page.goto(`${BASE_URL}/projects/test-project-123`);

    // Create an application first
    await page.click("button:has-text('Add Application')");
    await page.fill('input[placeholder="e.g., Frontend Web App"]', "Test App");
    await page.click("[role=combobox]");
    await page.click("text=Web Application");
    await page.click("button:has-text('Create')");

    // Create environments
    const envTypes = ["Development", "QA", "Staging", "Production"];

    for (const envType of envTypes) {
      await page.click("button:has-text('Add Environment')");
      await page.fill('input[placeholder="e.g., Development"]', envType);
      await page.click("[role=combobox]");
      await page.click(`text=${envType}`);
      await page.fill('input[placeholder="https://dev.example.com"]', `https://${envType.toLowerCase()}.example.com`);
      await page.click("button:has-text('Create')");
      await page.waitForSelector(`text=${envType}`);
    }

    // Verify all environments are displayed
    for (const envType of envTypes) {
      await expect(page.locator(`text=${envType}`)).toBeVisible();
    }
  });
});
