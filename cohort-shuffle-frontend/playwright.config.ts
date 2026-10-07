import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E configuration for Cohort Shuffle frontend.
 *
 * Tests run against a locally started Next.js dev server.
 * The backend FastAPI server must be running on port 8000.
 *
 * Run all tests:
 *   npx playwright test
 *
 * Run with UI:
 *   npx playwright test --ui
 *
 * Run a specific file:
 *   npx playwright test tests/e2e/activity-lifecycle.spec.ts
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false, // tests share DB state — run sequentially
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1, // single worker to keep test order predictable
  reporter: [["html", { outputFolder: "playwright-report" }], ["list"]],

  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "mobile-chrome",
      use: { ...devices["Pixel 5"] },
    },
  ],

  // Start the Next.js dev server before running tests
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
