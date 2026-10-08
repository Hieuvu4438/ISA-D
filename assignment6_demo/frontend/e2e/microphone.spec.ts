import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { initialCatalog, fakeMicrophone } from './helpers';

// Synthetic native device + provider stub: no Azure call or speech-accuracy claim.
test.use({
  launchOptions: { args: [
    '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream',
    `--use-file-for-fake-audio-capture=${fakeMicrophone}`,
  ] },
  permissions: ['microphone'],
});

test('synthetic native microphone + provider stub: converts WAV PCM16 mono 16 kHz before upload', async ({ page }) => {
  await page.addInitScript(() => {
    const original = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    (window as any).__e2eStreams = [];
    navigator.mediaDevices.getUserMedia = async constraints => {
      const stream = await original(constraints);
      (window as any).__e2eStreams.push(stream);
      return stream;
    };
  });
  await page.addInitScript(() => {
    const revoke = URL.revokeObjectURL.bind(URL);
    (window as any).__e2eRevoked = [];
    URL.revokeObjectURL = value => {
      (window as any).__e2eRevoked.push(value);
      revoke(value);
    };
  });
  await page.route('**/api/v1/meta', async route => {
    const response = await route.fetch();
    const metadata = await response.json();
    metadata.speech.configuration_state = 'configured_unverified';
    await route.fulfill({ response, json: metadata });
  });
  let receivedWav!: Buffer;
  await page.route('**/api/v1/speech/transcriptions', async route => {
    const multipart = route.request().postDataBuffer()!;
    const offset = multipart.indexOf(Buffer.from('RIFF'));
    expect(offset).toBeGreaterThan(0);
    const size = multipart.readUInt32LE(offset + 4) + 8;
    receivedWav = multipart.subarray(offset, offset + size);
    await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: {
      code: 'SPEECH_UNAVAILABLE', message: 'Provider stub: chưa cấu hình Azure.',
      field_errors: [], retryable: false, request_id: 'e2e-microphone-stub',
    } }) });
  });
  await initialCatalog(page);
  await page.getByRole('tab', { name: 'Giọng nói', exact: true }).click();
  await page.getByRole('button', { name: /Bắt đầu/ }).click();
  await expect(page.getByRole('button', { name: /Dừng/ })).toBeEnabled();
  // Native recording must gather at least one second of real browser PCM frames.
  await page.waitForTimeout(1500);
  await page.getByRole('button', { name: /Dừng/ }).click();
  const savedLink = page.getByRole('link', { name: 'Lưu bản ghi WAV', exact: true });
  await expect(savedLink).toBeVisible();
  const blobUrl = (await savedLink.getAttribute('href'))!;
  const downloadEvent = page.waitForEvent('download');
  await savedLink.click();
  const download = await downloadEvent;
  expect(download.suggestedFilename()).toBe('cortis-voice.wav');
  const savedWav = await readFile((await download.path())!);
  await page.getByRole('button', { name: 'Nhận dạng lời nói', exact: true }).click();
  await expect(page.getByText(/Provider stub/)).toBeVisible();
  expect(receivedWav.toString('ascii', 0, 4)).toBe('RIFF');
  expect(receivedWav.toString('ascii', 8, 12)).toBe('WAVE');
  expect(receivedWav.readUInt16LE(20)).toBe(1); // PCM
  expect(receivedWav.readUInt16LE(22)).toBe(1); // mono
  expect(receivedWav.readUInt32LE(24)).toBe(16000);
  expect(receivedWav.readUInt16LE(34)).toBe(16);
  expect(receivedWav.readUInt32LE(40)).toBeGreaterThanOrEqual(32000);
  expect(receivedWav.readUInt32LE(40)).toBeLessThanOrEqual(480000);
  expect(savedWav.equals(receivedWav)).toBe(true);
  await page.getByRole('button', { name: 'Xóa âm thanh', exact: true }).click();
  await expect(savedLink).toHaveCount(0);
  await expect.poll(() => page.evaluate(url => (window as any).__e2eRevoked.includes(url), blobUrl)).toBe(true);
  await page.getByRole('tab', { name: 'Mô tả', exact: true }).click();
  const tracks = await page.evaluate(() =>
    (window as any).__e2eStreams.flatMap((stream: MediaStream) => stream.getTracks().map(track => track.readyState)));
  expect(tracks.length).toBeGreaterThan(0);
  expect(tracks.every((state: string) => state === 'ended')).toBe(true);
});

test('synthetic native microphone: changing mode while recording stops every track', async ({ page }) => {
  await page.addInitScript(() => {
    const original = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    (window as any).__e2eStreams = [];
    navigator.mediaDevices.getUserMedia = async constraints => {
      const stream = await original(constraints);
      (window as any).__e2eStreams.push(stream);
      return stream;
    };
  });
  let transcriptionRequests = 0;
  page.on('request', request => {
    if (new URL(request.url()).pathname === '/api/v1/speech/transcriptions') transcriptionRequests += 1;
  });
  await initialCatalog(page);
  await page.getByRole('tab', { name: 'Giọng nói', exact: true }).click();
  await page.getByRole('button', { name: /Bắt đầu/ }).click();
  await expect(page.getByRole('button', { name: /Dừng/ })).toBeEnabled();
  await page.getByRole('tab', { name: 'Mô tả', exact: true }).click();
  await expect.poll(() => page.evaluate(() =>
    (window as any).__e2eStreams.every((stream: MediaStream) => stream.getTracks().every(track => track.readyState === 'ended')),
  )).toBe(true);
  expect(transcriptionRequests).toBe(0);
  await page.getByRole('tab', { name: 'Giọng nói', exact: true }).click();
  await expect(page.getByRole('button', { name: /Bắt đầu/ })).toBeEnabled();
});
