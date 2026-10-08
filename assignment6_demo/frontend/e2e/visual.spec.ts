import { test, expect } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { initialCatalog, expectNoHorizontalOverflow, waitForAllImages } from './helpers';

test('@visual bounded batched desktop/tablet/mobile inspection', async ({ page }) => {
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
    await expect(page.locator('main')).toBeVisible();
    await expect(page.getByText(/Đang tải/)).toHaveCount(0);
    await waitForAllImages(page);
    await page.screenshot({ path: `${directory}/${name}-1440.png`, fullPage: true });
  }
});
