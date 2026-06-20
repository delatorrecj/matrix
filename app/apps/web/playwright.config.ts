import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  // The scenario page boots deck.gl + maplibre (WebGL), so first paint is heavy — give
  // headroom over the 30s default so a slow CI runner doesn't flake (locally it's ~25s).
  timeout: 60_000,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  // CI: machine-readable list + an HTML report artifact (never auto-opens a browser).
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'html',
  use: {
    baseURL: 'http://127.0.0.1:3000',
    trace: 'on-first-retry',
  },
  // Auto-start the app under test. The e2e is hermetic (backend is mocked in-test via
  // page.route / page.routeWebSocket), so only the Next.js server is needed — no API,
  // Redis, or SUMO. CI runs the production build (`next start`, after `next build`);
  // locally it uses `next dev` and reuses an already-running server if present.
  webServer: {
    command: process.env.CI ? 'npm run start' : 'npm run dev',
    url: 'http://127.0.0.1:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
