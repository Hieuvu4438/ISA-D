import { test, expect } from '@playwright/test';
import { initialCatalog, monitorConsole, submitSearch } from './helpers';

test('real local CPU speech populates transcript and preserves provider through search @local-speech', async ({ page }) => {
  test.setTimeout(120_000);
  test.skip(!process.env.LOCAL_SPEECH_E2E_AUDIO, 'Run fetch_speech_samples.py and supply LOCAL_SPEECH_E2E_AUDIO.');
  const errors = monitorConsole(page);
  await initialCatalog(page);
  await page.getByRole('tab', { name: 'Giọng nói', exact: true }).click();
  await expect(page.getByText('Nhận dạng trên máy chủ bằng Whisper CPU;', { exact: false })).toBeVisible();
  await page.getByTestId('voice-audio-input').setInputFiles(process.env.LOCAL_SPEECH_E2E_AUDIO!);
  const pending = page.waitForResponse(response => response.url().endsWith('/speech/transcriptions') && response.request().method() === 'POST', { timeout: 100_000 });
  await page.getByRole('button', { name: 'Nhận dạng lời nói', exact: true }).click();
  const response = await pending;
  expect(response.status(), await response.text()).toBe(200);
  const body = await response.json();
  expect(body.provider).toBe('local');
  expect(body.transcript.length).toBeGreaterThan(10);
  await expect(page.getByTestId('voice-transcript')).toHaveValue(body.transcript);
  await expect(page.getByText('Whisper CPU · tiếng Việt', { exact: true })).toBeVisible();
  await page.getByTestId('voice-transcript').fill('giày chạy bộ màu đen');
  await expect(page.getByText('Đã chỉnh sửa transcript', { exact: true })).toBeVisible();
  const search = await submitSearch(page);
  expect(search.query.voice_source).toBe('local');
  expect(search.results.length).toBeGreaterThan(0);
  expect(errors).toEqual([]);
});
