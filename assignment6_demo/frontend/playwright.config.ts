import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './e2e', fullyParallel: false, workers: 1, timeout: 30_000,
  expect: { timeout: 10_000 },
  use: { baseURL: 'http://127.0.0.1:5173', trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  outputDir: '../artifacts/frontend/playwright',
  reporter: [['list'], ['json', { outputFile: '../artifacts/frontend/e2e-results.json' }]],
});
