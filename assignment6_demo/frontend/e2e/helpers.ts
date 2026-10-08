import { expect, type Page, type APIResponse } from '@playwright/test';
import { fileURLToPath } from 'node:url';

export const productPhoto = fileURLToPath(new URL('../../data/images/P001.jpg', import.meta.url));
export const pizzaPhoto = fileURLToPath(new URL('../../data/queries/Q001.jpg', import.meta.url));
export const fakeMicrophone = fileURLToPath(new URL('./fixtures/fake-microphone-44100.wav', import.meta.url));
export const syntheticUpload = fileURLToPath(new URL('./fixtures/synthetic-upload-16000.wav', import.meta.url));

export function monitorConsole(page: Page): string[] {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error') errors.push(message.text());
  });
  return errors;
}

export async function assertBackendReady(response: APIResponse) {
  expect(response.status()).toBe(200);
  expect((await response.json()).search_available).toBe(true);
}

export async function expectNoHorizontalOverflow(page: Page) {
  const geometry = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    document: document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }));
  expect(geometry.document, JSON.stringify(geometry)).toBeLessThanOrEqual(geometry.viewport + 1);
  expect(geometry.body, JSON.stringify(geometry)).toBeLessThanOrEqual(geometry.viewport + 1);
}

export async function submitSearch(page: Page, endpoint = '/api/v1/search') {
  const pending = page.waitForResponse(response =>
    new URL(response.url()).pathname === endpoint && response.request().method() === 'POST');
  await page.getByTestId('search-submit').click();
  const response = await pending;
  expect(response.status(), await response.text()).toBe(200);
  return response.json();
}

export async function initialCatalog(page: Page) {
  const totalResponse = await page.request.get('/api/v1/products?limit=100');
  expect(totalResponse.ok()).toBe(true);
  const { total } = await totalResponse.json();
  await page.goto('/');
  await expect(page.getByTestId('product-card')).toHaveCount(total);
}

export async function waitForRouteHydration(page: Page, route: string) {
  const ready = route === '/' ? page.getByTestId('product-card').first()
    : route.startsWith('/products/') ? page.locator('.detail-copy h1')
    : route.startsWith('/orders/') ? page.locator('.order-detail-heading h1')
    : route === '/credits' ? page.locator('.credit-item').first()
    : page.locator('main h1');
  await expect(ready).toBeVisible();
  await expect(page.getByText(/Đang tải/)).toHaveCount(0);
}

export async function waitForAllImages(page: Page) {
  await page.evaluate(async () => { await document.fonts.ready; });
  const images = page.locator('main img');
  for (const image of await images.all()) {
    await image.scrollIntoViewIfNeeded();
    await expect.poll(() => image.evaluate((node: HTMLImageElement) =>
      node.complete && node.naturalWidth > 0)).toBe(true);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
}

export async function expectRealRankedResults(page: Page, response: any) {
  const ids = response.results.map((result: any) => result.product.product_id);
  expect(ids.length).toBeGreaterThan(0);
  await expect(page.getByTestId('result-card')).toHaveCount(ids.length);
  for (const result of response.results) {
    await expect(page.getByTestId('result-card').nth(result.rank - 1)).toContainText(result.product.name);
  }
  expect(response.meta.index_fingerprint).toMatch(/^[a-f0-9]{64}$/);
  expect(response.meta.model_fingerprint).toMatch(/^[a-f0-9]{64}$/);
}
