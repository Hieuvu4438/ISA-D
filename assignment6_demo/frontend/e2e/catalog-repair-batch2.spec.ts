import { test, expect } from '@playwright/test'
import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync } from 'node:fs'
import AxeBuilder from '@axe-core/playwright'

const reviews = JSON.parse(readFileSync(new URL('../../data/catalog_repair_batch2_review.json', import.meta.url), 'utf8')) as { product_id: string; sha256: string; metadata: { name: string; brand: string; color: string; description: string } }[]
const regression = JSON.parse(readFileSync(new URL('../../evaluation/catalog_repair_batch2.json', import.meta.url), 'utf8')) as { cases: { query: string; expected_ids: string[] }[] }

test('real repaired backpacks: public photo bytes, credits, visible catalog and CPU descriptive search', async ({ page }) => {
  test.setTimeout(60_000)
  await page.goto('/catalog?category=backpack')
  await expect(page.getByTestId('product-card')).toHaveCount(15)
  const photos = []
  for (const row of reviews) {
    const response = await page.request.get(`/api/v1/products/${row.product_id}`)
    expect(response.status()).toBe(200)
    const product = (await response.json()).product
    for (const [key, value] of Object.entries(row.metadata)) expect(product[key]).toBe(value)
    expect(product.category).toBe('backpack')
    const media = await page.request.get(product.image_url)
    expect(media.status()).toBe(200)
    expect(createHash('sha256').update(await media.body()).digest('hex')).toBe(row.sha256)
    expect(product.image_credit.source_page.startsWith('https://commons.wikimedia.org/wiki/File:')).toBe(true)
    expect(product.image_credit.license).toMatch(/^CC BY-SA/)
    const photo = page.locator(`a[href="/products/${row.product_id}"] img`)
    await photo.scrollIntoViewIfNeeded()
    await expect.poll(() => photo.evaluate(img => (img as HTMLImageElement).naturalWidth)).toBeGreaterThan(0)
    photos.push({ product_id: row.product_id, photo_sha256: row.sha256, product })
  }
  for (const width of [360, 1440]) {
    await page.setViewportSize({ width, height: 1000 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
    await page.locator('.catalog-content').screenshot({ path: `../artifacts/frontend/screenshots/catalog-repair-batch2/backpacks-${width}.png` })
  }
  await page.goto('/')
  await expect(page.getByTestId('product-card').first()).toBeVisible()
  await page.getByTestId('search-text').fill('balo Eastpak')
  const pending = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/search' && r.request().method() === 'POST')
  await page.getByTestId('search-submit').click()
  expect((await pending).status()).toBe(200)
  await expect(page.getByTestId('result-card')).toHaveCount(1)
  await expect(page.getByTestId('result-card')).toContainText('Eastpak Sugarbush')
  await expect(page.getByRole('status', { name: 'Phạm vi tìm kiếm đã hiểu' })).toContainText('Eastpak')
  const results = []
  for (const row of regression.cases) {
    const response = await page.request.post('/api/v1/search', { data: { mode: 'text', text: row.query, options: { search_strategy: 'hybrid', top_k: 3 } } })
    expect(response.status()).toBe(200)
    const body = await response.json()
    const ids = body.results.map((r: { product: { product_id: string } }) => r.product.product_id)
    expect(row.expected_ids.some(id => ids.includes(id)), row.query).toBe(true)
    expect(body.results.every((r: { product: { category: string } }) => r.product.category === 'backpack')).toBe(true)
    results.push({ query: row.query, expected_ids: row.expected_ids, response: body })
  }
  writeFileSync(new URL('../../artifacts/validation/catalog-repair-batch2-browser-model.json', import.meta.url), JSON.stringify({ scope: 'Actual browser and CPU catalog-derived descriptive regression; not independent frozen relevance quality', speech_calls: 0, photos, results }, null, 2))
})
