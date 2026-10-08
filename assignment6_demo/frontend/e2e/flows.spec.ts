import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {
  initialCatalog, monitorConsole, submitSearch, expectRealRankedResults,
  expectNoHorizontalOverflow, productPhoto, pizzaPhoto,
  assertBackendReady,
} from './helpers';

test.beforeAll(async ({ request }) => {
  await assertBackendReady(await request.get('http://127.0.0.1:8000/health/ready'));
});

test('real API: Vietnamese search, submitted state and detail return', async ({ page }) => {
  const errors = monitorConsole(page);
  await initialCatalog(page);
  await page.getByTestId('search-text').fill('giày Converse đỏ cổ cao');
  const response = await submitSearch(page);
  expect(response.results[0].product.product_id).toBe('P006');
  await expectRealRankedResults(page, response);
  await expect(page.getByTestId('result-card').first()).toContainText(/Cosine/i);
  await page.getByTestId('search-text').fill('túi da màu nâu');
  await expect(page.getByText(/Đã đổi điều kiện/)).toBeVisible();
  // Editing a draft must retain the last submitted results and their labels.
  await expect(page.getByTestId('result-card').first()).toContainText(response.results[0].product.name);
  const productLink = page.locator('a[href="/products/P006"]').first();
  await productLink.scrollIntoViewIfNeeded();
  const scrollBeforeDetail = await page.evaluate(() => window.scrollY);
  await productLink.click();
  await expect(page.getByRole('heading', { name: 'Giày Converse All Star đỏ cổ cao', exact: true })).toBeVisible();
  await page.goBack();
  await expect(page.getByTestId('search-text')).toHaveValue('túi da màu nâu');
  await expect(page.getByTestId('result-card').first()).toContainText('Converse');
  await expect.poll(async () => Math.abs(await page.evaluate(() => window.scrollY) - scrollBeforeDetail)).toBeLessThan(100);
  await page.getByTestId('search-text').fill('giày Converse đỏ cổ cao');
  await page.getByText('Xem cách hệ thống xử lý').click();
  await expect(page.getByTestId('processing-panel')).toContainText(/validation|Kiểm tra/i);
  expect(errors).toEqual([]);
});

test('real API: all six curated Vietnamese descriptions have the expected first result', async ({ page }) => {
  await initialCatalog(page);
  const cases = [
    ['giày chạy bộ On màu đen', 'P001'],
    ['giày chạy bộ Asics màu xanh đậm', 'P003'],
    ['giày Converse đỏ cổ cao', 'P006'],
    ['giày Nike Air Force trắng', 'P007'],
    ['túi da màu nâu có dây đeo', 'P011'],
    ['túi Hermès Kelly màu đỏ', 'P012'],
  ];
  for (const [text, expected] of cases) {
    await page.getByTestId('search-text').fill(text);
    const response = await submitSearch(page);
    expect(response.results[0].product.product_id, text).toBe(expected);
    await expectRealRankedResults(page, response);
  }
});

test('real API: image bytes and multimodal fusion preserve user inputs', async ({ page }) => {
  const errors = monitorConsole(page);
  await initialCatalog(page);
  await page.getByRole('tab', { name: 'Hình ảnh', exact: true }).click();
  await page.getByTestId('image-input').setInputFiles(productPhoto);
  const image = await submitSearch(page, '/api/v1/search/image');
  expect(image.query.mode).toBe('image');
  expect(image.results[0].product.product_id).toBe('P001');
  expect(image.query.image_summary.format).toBe('JPEG');
  await expectRealRankedResults(page, image);
  await page.getByRole('tab', { name: 'Mô tả + ảnh', exact: true }).click();
  await page.getByTestId('search-text').fill('giày chạy bộ On màu đen');
  await page.getByTestId('image-input').setInputFiles(productPhoto);
  const multimodal = await submitSearch(page, '/api/v1/search/multimodal');
  expect(multimodal.query.mode).toBe('multimodal');
  expect(multimodal.query.text_weight).toBe(0.5);
  expect(multimodal.results[0].product.product_id).toBe('P001');
  await expectRealRankedResults(page, multimodal);
  await page.getByTestId('text-weight').fill('0.7');
  const weighted = await submitSearch(page, '/api/v1/search/multimodal');
  expect(weighted.query.text_weight).toBe(0.7);
  expect(weighted.query.options.result_policy).toBe('nearest');
  expect(errors).toEqual([]);
});

test('real API: price/brand/stock filters, zero price and relevant OOD recovery', async ({ page }) => {
  await initialCatalog(page);
  await page.getByTestId('search-text').fill('giày màu đỏ');
  await page.getByTestId('filter-brand').selectOption('Converse');
  await page.getByTestId('min-price').fill('1100000');
  await page.getByTestId('max-price').fill('1100000');
  await page.getByLabel('Chỉ còn hàng', { exact: true }).check();
  const filtered = await submitSearch(page);
  expect(filtered.results.map((r: any) => r.product.product_id)).toEqual(['P006']);
  await expect(page.getByTestId('result-card')).toHaveCount(1);
  await page.getByTestId('filter-brand').selectOption('');
  await page.getByTestId('min-price').fill('');
  await page.getByTestId('max-price').fill('0');
  const empty = await submitSearch(page);
  expect(empty.query.options.filters.max_price).toBe(0);
  expect(empty.meta.empty_reason).toBe('filters');
  await expect(page.getByText('Không có sản phẩm đáp ứng bộ lọc', { exact: true })).toBeVisible();
  await page.getByTestId('max-price').fill('');
  await page.getByTestId('search-text').fill('bánh pizza cà chua và phô mai');
  await page.getByTestId('result-policy').selectOption('relevant');
  const ood = await submitSearch(page);
  expect(ood.meta.empty_reason).toBe('threshold');
  await expect(page.getByText('Chưa có sản phẩm đạt ngưỡng liên quan', { exact: true })).toBeVisible();
  await page.getByRole('tab', { name: 'Hình ảnh', exact: true }).click();
  await page.getByTestId('image-input').setInputFiles(pizzaPhoto);
  await page.getByTestId('result-policy').selectOption('relevant');
  const imageOOD = await submitSearch(page, '/api/v1/search/image');
  expect(imageOOD.results).toEqual([]);
  await page.getByTestId('result-policy').selectOption('nearest');
  const recovered = await submitSearch(page, '/api/v1/search/image');
  expect(recovered.results.length).toBeGreaterThan(0);
  await expectRealRankedResults(page, recovered);
  await page.getByRole('tab', { name: 'Mô tả + ảnh', exact: true }).click();
  await page.getByTestId('search-text').fill('bánh pizza phô mai cà chua');
  await page.getByTestId('image-input').setInputFiles(pizzaPhoto);
  await page.getByTestId('result-policy').selectOption('relevant');
  const multiOOD = await submitSearch(page, '/api/v1/search/multimodal');
  expect(multiOOD.query.text_weight).toBe(0.5);
  expect(multiOOD.meta.empty_reason).toBe('threshold');
  await expect(page.getByText('Chưa có sản phẩm đạt ngưỡng liên quan', { exact: true })).toBeVisible();
});

test('real API: manual voice transcript is labelled and sent honestly', async ({ page }) => {
  await initialCatalog(page);
  await page.getByRole('tab', { name: 'Giọng nói', exact: true }).click();
  await page.getByTestId('voice-transcript').fill('túi da màu nâu');
  const response = await submitSearch(page);
  expect(response.query.mode).toBe('voice');
  expect(response.query.voice_source).toBe('manual_transcript');
  expect(response.results[0].product.product_id).toBe('P011');
  await expect(page.getByText(/Transcript nhập tay.*mô phỏng/)).toBeVisible();
  await expectRealRankedResults(page, response);
});

test('real API: direct product route/reload, honest demo fields and photo credits', async ({ page }) => {
  const errors = monitorConsole(page);
  await page.goto('/products/P001');
  await expect(page.getByRole('heading', { name: 'Giày chạy bộ On Cloud màu đen', exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Giày chạy bộ On Cloud màu đen', exact: true })).toBeVisible();
  await expect(page.getByText(/Giá.*tồn kho.*(demo|minh họa)/i).first()).toBeVisible();
  const image = page.locator('img[src*="/api/v1/media/products/P001"]');
  await expect(image).toBeVisible();
  await expect.poll(() => image.evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
  const source = page.locator('a[href*="commons.wikimedia.org/wiki/File:"]');
  await expect(source).toHaveAttribute('rel', /noopener/);
  expect(errors).toEqual([]);
});

test('real API: own order detail and indistinguishable foreign/missing orders', async ({ page }) => {
  await page.goto('/orders');
  await page.getByLabel('Mã đơn hàng', { exact: true }).fill('o001');
  await page.getByRole('button', { name: /Tra cứu/ }).click();
  await expect(page.getByRole('heading', { name: /Đơn hàng O001/ })).toBeVisible();
  await page.locator('a[href="/orders/O001"]').click();
  await expect(page.getByRole('heading', { name: /O001/ })).toBeVisible();
  await expect(page.getByText('Giày Converse All Star đỏ cổ cao', { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: /O001/ })).toBeVisible();
  await page.goto('/orders');
  for (const id of ['O002', 'O999']) {
    await page.getByLabel('Mã đơn hàng', { exact: true }).fill(id);
    await page.getByRole('button', { name: /Tra cứu/ }).click();
    await expect(page.getByText('Không tìm thấy đơn hàng.', { exact: true })).toBeVisible();
    await expect(page.getByLabel('Mã đơn hàng', { exact: true })).toHaveValue(id);
    await expect(page.getByText('C002', { exact: true })).toHaveCount(0);
  }
});

test('real API: all twelve credits and unknown-route recovery', async ({ page }) => {
  const errors = monitorConsole(page);
  const credits = await (await page.request.get('/api/v1/credits')).json();
  await page.goto('/credits');
  await expect(page.locator('a[href*="commons.wikimedia.org/wiki/File:"]')).toHaveCount(credits.credits.length);
  await expect(page.getByText(/Goodreg3/)).toBeVisible();
  for (const link of await page.locator('a[target="_blank"]').all()) {
    await expect(link).toHaveAttribute('rel', /noopener/);
  }
  await page.goto('/khong-ton-tai');
  await expect(page.getByRole('heading', { name: /không có|không tồn tại/i })).toBeVisible();
  await page.getByRole('link', { name: /Tìm sản phẩm|Về trang/i }).first().click();
  await expect(page).toHaveURL('/');
  expect(errors).toEqual([]);
});

test('keyboard tab arrows and serious/critical accessibility checks', async ({ page }) => {
  const errors = monitorConsole(page);
  await initialCatalog(page);
  const description = page.getByRole('tab', { name: 'Mô tả', exact: true });
  await description.focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: 'Giọng nói', exact: true })).toBeFocused();
  await page.keyboard.press('ArrowLeft');
  await expect(description).toBeFocused();
  for (const route of ['/', '/products/P001', '/orders', '/orders/O001', '/credits']) {
    await page.goto(route);
    await expect(page.locator('main')).toBeVisible();
    // Scan after the route's real API hydration, without ignoring any application region.
    await expect(page.getByText(/Đang tải/)).toHaveCount(0);
    const audit = await new AxeBuilder({ page }).analyze();
    expect(audit.violations.filter(v => v.impact === 'serious' || v.impact === 'critical'), route).toEqual([]);
  }
  expect(errors).toEqual([]);
});

test('responsive routes remain usable at 360, 768 and 1440 pixels', async ({ page }) => {
  for (const width of [360, 768, 1440]) {
    await page.setViewportSize({ width, height: width === 360 ? 800 : 1000 });
    for (const route of ['/', '/products/P001', '/orders', '/orders/O001', '/credits']) {
      await page.goto(route);
      await expect(page.locator('main')).toBeVisible();
      await expect(page.getByText(/Đang tải/)).toHaveCount(0);
      await expectNoHorizontalOverflow(page);
    }
  }
});
