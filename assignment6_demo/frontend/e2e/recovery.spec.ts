import { test, expect } from '@playwright/test';
import { initialCatalog, productPhoto, submitSearch, expectRealRankedResults, syntheticUpload } from './helpers';

test('deterministic error stub: rejected query retains the draft and can retry against real API', async ({ page }) => {
  await initialCatalog(page);
  await page.getByTestId('search-text').fill('giày Converse đỏ cổ cao');
  await page.route('**/api/v1/search', async route => {
    await route.fulfill({
      status: 422,
      contentType: 'application/json',
      body: JSON.stringify({ error: {
        code: 'VALIDATION_ERROR', message: 'Vui lòng kiểm tra mô tả.',
        field_errors: [{ field: 'text', message: 'Vui lòng kiểm tra mô tả.' }],
        request_id: 'e2e-error-stub', retryable: false,
      } }),
    });
  }, { times: 1 });
  await page.getByTestId('search-submit').click();
  await expect(page.getByTestId('search-error')).toContainText('Vui lòng kiểm tra mô tả.');
  await expect(page.getByTestId('search-text')).toHaveValue('giày Converse đỏ cổ cao');
  await expect(page.getByTestId('search-submit')).toBeEnabled();
  const response = await submitSearch(page);
  await expectRealRankedResults(page, response);
  await expect(page.getByTestId('search-error')).toHaveCount(0);
});

test('deterministic race: an old real text response cannot overwrite a newer image search', async ({ page }) => {
  await initialCatalog(page);
  let release!: () => void;
  const blocked = new Promise<void>(resolve => { release = resolve; });
  let notifyStarted!: () => void;
  const started = new Promise<void>(resolve => { notifyStarted = resolve; });
  await page.route('**/api/v1/search', async route => {
    notifyStarted();
    const actual = await route.fetch();
    await blocked;
    // The browser may have aborted this request when the user changed mode.
    await route.fulfill({ response: actual }).catch(() => undefined);
  }, { times: 1 });
  await page.getByTestId('search-text').fill('giày Converse đỏ cổ cao');
  await page.getByTestId('search-submit').click();
  await started;
  await page.getByRole('tab', { name: 'Hình ảnh', exact: true }).click();
  await page.getByTestId('image-input').setInputFiles(productPhoto);
  const image = await submitSearch(page, '/api/v1/search/image');
  expect(image.results[0].product.product_id).toBe('P001');
  await expectRealRankedResults(page, image);
  release();
  await page.unrouteAll({ behavior: 'wait' });
  await expect(page.getByRole('tab', { name: 'Hình ảnh', exact: true })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByTestId('result-card').first()).toContainText('On Cloud');
  await expect(page.getByTestId('search-submit')).toBeEnabled();
});

test('unsupported image recovery and unconfigured Azure preserve manual voice fallback', async ({ page }) => {
  await initialCatalog(page);
  let speechRequests = 0;
  page.on('request', request => {
    if (new URL(request.url()).pathname === '/api/v1/speech/transcriptions') speechRequests += 1;
  });
  await page.getByRole('tab', { name: 'Hình ảnh', exact: true }).click();
  await page.getByTestId('image-input').setInputFiles({
    name: 'invalid.svg', mimeType: 'image/svg+xml', buffer: Buffer.from('<svg></svg>'),
  });
  await expect(page.getByText(/JPEG|PNG|WebP/).last()).toBeVisible();
  await page.getByTestId('image-input').setInputFiles(productPhoto);
  await expectRealRankedResults(page, await submitSearch(page, '/api/v1/search/image'));
  await page.getByRole('tab', { name: 'Giọng nói', exact: true }).click();
  await expect(page.getByText(/Azure.*chưa|chưa.*Azure|chưa cấu hình/i).first()).toBeVisible();
  expect(speechRequests).toBe(0);
  await page.getByTestId('voice-transcript').fill('giày Converse đỏ cổ cao');
  await expectRealRankedResults(page, await submitSearch(page));
});

test('real API WAV validation: malformed PCM header returns 422 before any Azure recognition', async ({ page }) => {
  await page.route('**/api/v1/meta', async route => {
    const response = await route.fetch();
    const metadata = await response.json();
    metadata.speech.configuration_state = 'configured_unverified';
    await route.fulfill({ response, json: metadata });
  });
  await initialCatalog(page);
  await page.getByRole('tab', { name: 'Giọng nói', exact: true }).click();
  await page.getByTestId('voice-audio-input').setInputFiles({
    name: 'broken.wav', mimeType: 'audio/wav', buffer: Buffer.from('RIFF\0\0\0\0WAVEbroken'),
  });
  const pending = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/speech/transcriptions');
  await page.getByRole('button', { name: 'Nhận dạng lời nói', exact: true }).click();
  const response = await pending;
  expect(response.status()).toBe(422);
  expect((await response.json()).error.code).toBe('AUDIO_INVALID');
  await expect(page.getByText(/Tệp WAV không hợp lệ/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Nhận dạng lời nói', exact: true })).toBeEnabled();
});

test('deterministic speech provider stub: editable transcript requires explicit real voice search', async ({ page }) => {
  await page.route('**/api/v1/meta', async route => {
    const response = await route.fetch();
    const metadata = await response.json();
    metadata.speech.configuration_state = 'configured_unverified';
    await route.fulfill({ response, json: metadata });
  });
  await page.route('**/api/v1/speech/transcriptions', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      request_id: 'e2e-speech-success-stub', transcript: 'giày Converse đỏ cổ cao',
      provider: 'azure', language: 'vi-VN', audio_duration_ms: 1500,
      timing_ms: { validation: 1, provider: 1, total: 2 },
    }) });
  });
  let searchCount = 0;
  page.on('request', request => {
    if (new URL(request.url()).pathname === '/api/v1/search') searchCount += 1;
  });
  await initialCatalog(page);
  await page.getByRole('tab', { name: 'Giọng nói', exact: true }).click();
  await page.getByTestId('voice-audio-input').setInputFiles(syntheticUpload);
  await page.getByRole('button', { name: 'Nhận dạng lời nói', exact: true }).click();
  await expect(page.getByTestId('voice-transcript')).toHaveValue('giày Converse đỏ cổ cao');
  expect(searchCount).toBe(0);
  await page.getByTestId('voice-transcript').fill('giày Nike Air Force trắng');
  await expect(page.getByText(/Đã chỉnh sửa transcript/)).toBeVisible();
  const response = await submitSearch(page);
  expect(searchCount).toBe(1);
  expect(response.query.voice_source).toBe('azure');
  expect(response.results[0].product.product_id).toBe('P007');
  await expectRealRankedResults(page, response);
});

test('deterministic permission denial: microphone error keeps manual voice fallback usable', async ({ page }) => {
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = async () => {
      throw new DOMException('Synthetic permission denial', 'NotAllowedError');
    };
  });
  await initialCatalog(page);
  await page.getByRole('tab', { name: 'Giọng nói', exact: true }).click();
  await page.getByRole('button', { name: /Bắt đầu/ }).click();
  await expect(page.getByTestId('search-error')).toContainText('Chưa truy cập được microphone.');
  await page.getByTestId('voice-transcript').fill('túi da màu nâu');
  const response = await submitSearch(page);
  expect(response.query.voice_source).toBe('manual_transcript');
  await expectRealRankedResults(page, response);
});

test('deterministic readiness stub: unavailable AI still permits the real catalog and orders', async ({ page }) => {
  await page.route('**/api/v1/meta', async route => {
    const response = await route.fetch();
    const metadata = await response.json();
    metadata.capabilities.search = { available: false, reason_code: 'INDEX_MISSING' };
    metadata.capabilities.relevant = { available: false, modes: [], multimodal_weights: [], reason_code: 'RELEVANCE_POLICY_UNAVAILABLE' };
    metadata.index.available = false;
    await route.fulfill({ response, json: metadata });
  });
  await initialCatalog(page);
  await expect(page.getByText(/Tìm kiếm AI chưa sẵn sàng/)).toBeVisible();
  await expect(page.getByTestId('search-submit')).toBeDisabled();
  await page.locator('a[href="/products/P001"]').first().click();
  await expect(page.getByRole('heading', { name: 'Giày chạy bộ On Cloud màu đen', exact: true })).toBeVisible();
  await page.goto('/orders/O001');
  await expect(page.getByRole('heading', { name: /O001/ })).toBeVisible();
});

