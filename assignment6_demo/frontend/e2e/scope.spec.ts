import { test, expect } from '@playwright/test'
import { readFileSync, writeFileSync } from 'node:fs'
import AxeBuilder from '@axe-core/playwright'

const query = 'giày chạy bộ Nike; dưới 1 triệu; không màu đỏ'

test('real catalog scope, suggestions, exact SKU, opt-out history and conflicts', async ({ page }) => {
  await page.goto(`/catalog?q=${encodeURIComponent(query)}`)
  const notice = page.getByRole('status', { name: 'Phạm vi tìm kiếm đã hiểu' })
  await expect(notice).toContainText('Nike')
  await expect(notice).toContainText('Giày chạy bộ')
  await expect(page.getByTestId('product-card')).toHaveCount(1)
  const result = await (await page.request.get(`/api/v1/catalog?q=${encodeURIComponent(query)}`)).json()
  expect(result.products.map((p: { product_id: string }) => p.product_id)).toEqual(['P013'])
  expect(result.query.filters.brand).toBeNull()
  expect(result.scope_interpretation.clauses).toHaveLength(2)
  const suggestions = await (await page.request.get(`/api/v1/suggestions?q=${encodeURIComponent(query)}`)).json()
  expect(suggestions.products.map((p: { product_id: string }) => p.product_id)).toEqual(['P013'])
  const missing = await (await page.request.get('/api/v1/catalog?q=giay+chay+bo+Nike+P999')).json()
  expect(missing.products).toEqual([])
  expect(missing.retrieval).toBe('exact_sku')
  await page.getByLabel('Tự hiểu hãng, loại và màu sản phẩm').uncheck()
  await expect(page).toHaveURL(/interpret_scope=false/)
  await expect(notice).toHaveCount(0)
  await page.goBack()
  await expect(notice).toBeVisible()
  await expect(page.getByLabel('Tự hiểu hãng, loại và màu sản phẩm')).toBeChecked()
  await page.getByLabel('Thương hiệu', { exact: true }).selectOption('Adidas')
  await expect(page.getByRole('alert')).toContainText('mâu thuẫn')
  await expect(page.getByRole('combobox', { name: 'Tên sản phẩm hoặc mã sản phẩm' })).toHaveValue(query)
  await page.getByLabel('Thương hiệu', { exact: true }).selectOption('')
  await expect(notice).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('real CPU search scope notice, filter conflict recovery and responsive batch', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('product-card').first()).toBeVisible()
  await page.getByTestId('search-text').fill(query)
  const pending = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/search' && r.request().method() === 'POST')
  await page.getByTestId('search-submit').click()
  const response = await pending
  expect(response.status()).toBe(200)
  const body = await response.json()
  expect(body.results.map((r: { product: { product_id: string } }) => r.product.product_id)).toEqual(['P013'])
  const notice = page.getByRole('status', { name: 'Phạm vi tìm kiếm đã hiểu' })
  await expect(notice).toContainText('Nike')
  await expect(page.getByTestId('filter-brand')).toHaveValue('')
  const productPhoto = page.getByTestId('result-card').locator('img')
  await productPhoto.scrollIntoViewIfNeeded()
  await expect.poll(() => productPhoto.evaluate(img => (img as HTMLImageElement).naturalWidth)).toBeGreaterThan(0)
  for (const width of [360, 1440]) {
    await page.setViewportSize({ width, height: 1000 })
    if (width <= 800) {
      const filter = page.getByRole('button', { name: /^Bộ lọc/ }).first()
      if (await filter.getAttribute('aria-expanded') === 'false') await filter.click()
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
    await page.screenshot({ path: `../artifacts/frontend/screenshots/scope/search-${width}.png`, fullPage: true })
  }
  await page.getByTestId('filter-brand').selectOption('Adidas')
  await page.getByTestId('search-submit').click()
  await expect(page.getByRole('alert')).toContainText('mâu thuẫn')
  await expect(page.getByTestId('search-text')).toHaveValue(query)
  await page.getByLabel('Tự hiểu hãng, loại và màu sản phẩm').uncheck()
  const retry = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/search' && r.status() === 200)
  await page.getByTestId('search-submit').click()
  expect((await (await retry).json()).meta.scope_interpretation.applied).toBe(false)
  await expect(notice).toHaveCount(0)
})

test('real CPU scope properties: semantic, manual transcript, multimodal and OR', async ({ request }) => {
  const photo = readFileSync(new URL('../../data/images/P013.jpg', import.meta.url))
  const results = []
  for (const mode of ['text', 'voice', 'multimodal'] as const) {
    const options = { search_strategy: mode === 'text' ? 'semantic' : 'hybrid', top_k: 20 }
    const response = mode === 'multimodal'
      ? await request.post('/api/v1/search/multimodal', { multipart: { text: query, text_weight: '0.5', options: JSON.stringify(options), image: { name: 'photo.jpg', mimeType: 'image/jpeg', buffer: photo } } })
      : await request.post('/api/v1/search', { data: { mode, text: query, options, ...(mode === 'voice' ? { voice_source: 'manual_transcript' } : {}) } })
    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.query.text).toBe(query)
    expect(body.results.map((r: { product: { product_id: string } }) => r.product.product_id)).toEqual(['P013'])
    expect(body.meta.scope_interpretation.clauses).toHaveLength(2)
    results.push({ mode, response: body })
  }
  const either = await (await request.get('/api/v1/catalog?q=giay+chay+bo+Nike+hoac+Asics&limit=100')).json()
  expect(either.products.some((p: { brand: string }) => p.brand === 'Nike')).toBe(true)
  expect(either.products.some((p: { brand: string }) => p.brand === 'Asics')).toBe(true)
  expect(either.products.every((p: { brand: string; category: string }) => ['Nike', 'Asics'].includes(p.brand) && p.category === 'running_shoes')).toBe(true)
  const uncertain = await (await request.get('/api/v1/catalog?q=Nike+hoac+ao+thun')).json()
  expect(uncertain.scope_interpretation.applied).toBe(false)
  expect(uncertain.scope_interpretation.warnings.length).toBeGreaterThan(0)
  writeFileSync(new URL('../../artifacts/backend/scope-real-encoder.json', import.meta.url), JSON.stringify({ scope: 'Live CPU metadata-scope property smoke, not independent relevance quality or STT', speech_calls: 0, results, either, uncertain }, null, 2))
})
