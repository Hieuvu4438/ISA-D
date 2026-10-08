import { test, expect } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { initialCatalog, expectNoHorizontalOverflow, waitForAllImages, waitForRouteHydration, syntheticUpload } from './helpers';

test('@visual bounded batched desktop/tablet/mobile inspection', async ({ page }) => {
  test.setTimeout(90_000);
  const round = process.env.VISUAL_ROUND || 'initial';
  const directory = fileURLToPath(new URL(`../../artifacts/frontend/screenshots/${round}/`, import.meta.url));
  mkdirSync(directory, { recursive: true });
  for (const [width, height] of [[1440, 1000], [768, 1024], [360, 800]]) {
    await page.setViewportSize({ width, height });
    await initialCatalog(page);
    await expectNoHorizontalOverflow(page);
    await waitForAllImages(page);
    await page.screenshot({ path: `${directory}/search-${width}.png`, fullPage: true });
    if (width === 1440 || width === 360) {
      await page.getByTestId('product-card').first().scrollIntoViewIfNeeded();
      await page.screenshot({ path: `${directory}/catalog-${width}.png` });
    }
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  for (const [name, route] of [
    ['product', '/products/P001'], ['orders', '/orders'], ['order-detail', '/orders/O001'], ['credits', '/credits'],
  ]) {
    await page.goto(route);
    await waitForRouteHydration(page, route);
    await waitForAllImages(page);
    await page.screenshot({ path: `${directory}/${name}-1440.png`, fullPage: true });
  }
  for (const [width, height] of [[1440, 1000], [360, 800]]) {
    await page.setViewportSize({ width, height });
    await initialCatalog(page);
    await page.getByRole('tab', { name: 'Giọng nói', exact: true }).click();
    await page.getByTestId('voice-audio-input').setInputFiles(syntheticUpload);
    await expect(page.getByRole('link', { name: 'Lưu bản ghi WAV', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Nhận dạng lời nói', exact: true })).toBeDisabled();
    await expect(page.locator('.voice-unavailable').first()).toHaveCSS('border-left-width', '0px');
    await expectNoHorizontalOverflow(page);
    await waitForAllImages(page);
    await page.screenshot({ path: `${directory}/voice-${width}.png`, fullPage: true });
  }
});
