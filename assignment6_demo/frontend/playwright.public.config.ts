import { defineConfig } from '@playwright/test';

const baseURL = process.env.PUBLIC_DEMO_URL;
if (!baseURL || new URL(baseURL).protocol !== 'https:') {
  throw new Error('Set PUBLIC_DEMO_URL to the deployed HTTPS frontend origin.');
}

export default defineConfig({
  testDir: './e2e', fullyParallel: false, workers: 1, timeout: 90_000,
  expect: { timeout: 20_000 },
  testMatch: ['accounts.spec.ts', 'browse.spec.ts', 'checkout.spec.ts', 'public-demo.spec.ts'],
  grep: /real account API: register|real catalog API: filters|real encoder: hybrid|real checkout API: quote|public demo admin/,
  use: { baseURL, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  outputDir: '../runtime/public-demo/browser',
  reporter: [['list'], ['json', { outputFile: '../artifacts/validation/vercel-public-browser.json' }]],
});
