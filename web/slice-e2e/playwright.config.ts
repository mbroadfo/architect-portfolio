// End-to-end slice check (W6), run by `make slice-check` (local/slice_check.py) against the
// local Compose stack. Playwright is pinned in web/package.json (installed from
// web/package-lock.json with `npm ci`); its browser is installed project-locally with
// PLAYWRIGHT_BROWSERS_PATH=0. The Studio dev server runs on SLICE_STUDIO_PORT, a port the
// check chose free for this run, so parallel worktrees never collide.
import { defineConfig, devices } from "@playwright/test";

const apiUrl = process.env.SLICE_API_URL ?? "http://127.0.0.1:8000";
const idpUrl = process.env.SLICE_IDP_URL ?? "http://127.0.0.1:9000";
const studioPort = process.env.SLICE_STUDIO_PORT ?? "5173";
const studioUrl = `http://localhost:${studioPort}`;

export default defineConfig({
  testDir: ".",
  testMatch: "*.spec.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  reporter: [["list"]],
  outputDir: "../../local/.slice-check/test-results",
  use: {
    baseURL: studioUrl,
    trace: "off",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    // The Studio page on the Vite dev server; its origin is the only one the API allows.
    command: `npm --prefix ../slice-studio run dev -- --port ${studioPort}`,
    url: studioUrl,
    reuseExistingServer: false,
    timeout: 120_000,
    env: { VITE_API_BASE: apiUrl, VITE_TOKEN_URL: `${idpUrl}/token` },
  },
});
