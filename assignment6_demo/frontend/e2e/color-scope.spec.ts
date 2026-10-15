import { test, expect } from '@playwright/test'
import { readFileSync, writeFileSync } from 'node:fs'
import AxeBuilder from '@axe-core/playwright'

const query = 'balo màu hồng'

test('color intent is visible, survives reload and reports filter conflicts', async ({ page }) => {
  await page.goto(`/catalog?q=${encodeURIComponent(query)}`)
  const notice = page.getByRole('status', { name: 'Phạm vi tìm kiếm đã hiểu' })
  await expect(notice).toContainText('Màu hồng')
  await expect(page.getByTestId('product-card')).toHaveCount(1)
  await expect(page.getByTestId('product-card')).toContainText('Balo hồng')
  await page.reload()
  await expect(notice).toContainText('Màu hồng')
  await page.getByLabel('Tự hiểu hãng, loại, màu và kích cỡ').uncheck()
  await expect(page).toHaveURL(/interpret_scope=false/)
  await expect(notice).toHaveCount(0)
  await page.goBack()
  await expect(notice).toContainText('Màu hồng')
  const conflict = await page.request.get(`/api/v1/catalog?q=${encodeURIComponent(query)}&color=${encodeURIComponent('đen')}`)
  expect(conflict.status()).toBe(422)
  expect((await conflict.json()).error.code).toBe('SCOPE_FILTER_CONFLICT')
  const suggestions = await (await page.request.get(`/api/v1/suggestions?q=${encodeURIComponent(query)}`)).json()
  expect(suggestions.products.map((p: { product_id: string }) => p.product_id)).toEqual(['P129'])
  await page.goto('/')
  await expect(page.getByTestId('product-card').first()).toBeVisible()
  await page.getByTestId('search-text').fill(query)
  const pending = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/search' && r.request().method() === 'POST')
  await page.getByTestId('search-submit').click()
  expect((await pending).status()).toBe(200)
  await expect(notice).toContainText('Màu hồng')
  await expect(page.getByTestId('result-card')).toHaveCount(1)
  await expect(page.getByTestId('result-card')).toContainText('Balo hồng')
  for (const width of [360, 1440]) {
    await page.setViewportSize({ width, height: 1000 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
    await page.screenshot({ path: `../artifacts/frontend/screenshots/color-scope/search-${width}.png`, fullPage: true })
  }
})

test('actual CPU color constraints apply to semantic, hybrid, manual voice and multimodal', async ({ request }) => {
  const photo = readFileSync(new URL('../../data/images/P121.jpg', import.meta.url))
  const results = []
  for (const [mode, strategy] of [['text', 'semantic'], ['text', 'hybrid'], ['voice', 'hybrid'], ['multimodal', 'hybrid']] as const) {
    const options = { search_strategy: strategy, top_k: 20 }
    const response = mode === 'multimodal'
      ? await request.post('/api/v1/search/multimodal', { multipart: { text: query, text_weight: '0.5', options: JSON.stringify(options), image: { name: 'gray-black-backpack.jpg', mimeType: 'image/jpeg', buffer: photo } } })
      : await request.post('/api/v1/search', { data: { mode, text: query, options, ...(mode === 'voice' ? { voice_source: 'manual_transcript' } : {}) } })
    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.query.text).toBe(query)
    expect(body.results.map((r: { product: { product_id: string } }) => r.product.product_id)).toEqual(['P129'])
    expect(body.meta.scope_interpretation.clauses).toContainEqual({ text: 'hồng', field: 'color', value: 'hồng' })
    results.push({ mode, strategy, response: body })
  }
  const either = await (await request.get(`/api/v1/catalog?q=${encodeURIComponent('balo màu hồng hoặc xám')}&limit=100`)).json()
  expect(either.products.some((p: { product_id: string }) => p.product_id === 'P129')).toBe(true)
  expect(either.products.some((p: { product_id: string }) => p.product_id === 'P121')).toBe(true)
  expect(either.products.every((p: { color: string }) => p.color.includes('hồng') || p.color.includes('xám'))).toBe(true)
  const missing = await (await request.get(`/api/v1/catalog?q=${encodeURIComponent('balo màu tím')}`)).json()
  expect(missing.products).toEqual([])
  const excluded = await request.post('/api/v1/search', { data: { mode: 'text', text: 'balo màu hồng; không màu hồng' } })
  expect(excluded.status()).toBe(422)
  expect((await excluded.json()).error.code).toBe('SCOPE_EXCLUSION_CONFLICT')
  const meta = await (await request.get('/api/v1/meta')).json()
  writeFileSync(new URL('../../artifacts/backend/color-scope-real-encoder.json', import.meta.url), JSON.stringify({ scope: 'Actual local CPU color hard-filter properties; not independent relevance or live STT', speech_calls: 0, meta, results, either, missing }, null, 2))
})
