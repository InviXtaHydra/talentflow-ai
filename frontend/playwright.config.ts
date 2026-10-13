import { defineConfig, devices } from "@playwright/test";

// End-to-end tests run against a running stack (docker compose up, or the API + `npm run dev`).
// The main journey uses the configured AI provider (local Ollama by default), so allow a few minutes.
export default defineConfig({
  testDir: "tests/e2e",
  timeout: 6 * 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3300",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    acceptDownloads: true,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
