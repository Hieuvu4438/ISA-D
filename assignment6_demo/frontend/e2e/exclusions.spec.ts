import { test, expect } from '@playwright/test'
import { readFileSync, writeFileSync } from 'node:fs'
import AxeBuilder from '@axe-core/playwright'

test('real catalog exclusion: facets, suggestions, opt-out history and ambiguous recovery', async ({ page }) => {
  const query = 'không màu đỏ và đen'
  await page.goto(`/catalog?q=${encodeURIComponent(query)}&limit=100`)
  const notice = page.getByRole('status', { name: 'Điều kiện loại trừ đã hiểu' })
  await expect(notice).toContainText('đỏ')
  await expect(notice).toContainText('đen')
  const catalog = await (await page.request.get(`/api/v1/catalog?q=${encodeURIComponent(query)}&limit=100`)).json()
  expect(catalog.products.length).toBeGreaterThan(0)
  expect(catalog.products.every((p: { color: string }) => !/đỏ|đen/.test(p.color))).toBe(true)
  expect(catalog.facets.color.filter((f: { value: string }) => /đỏ|đen/.test(f.value)).every((f: { count: number }) => f.count === 0)).toBe(true)
  const suggestions = await (await page.request.get(`/api/v1/suggestions?q=${encodeURIComponent(query)}`)).json()
  expect(suggestions.products.length).toBeGreaterThan(0)
  expect(suggestions.products.every((p: { color: string }) => !/đỏ|đen/.test(p.color))).toBe(true)
  await page.getByLabel('Tự hiểu loại trừ màu, hãng, danh mục').uncheck()
  await expect(page).toHaveURL(/interpret_exclusions=false/)
  await expect(notice).toHaveCount(0)
  await page.goBack()
  await expect(notice).toBeVisible()
  await expect(page.getByLabel('Tự hiểu loại trừ màu, hãng, danh mục')).toBeChecked()
  await page.goto(`/catalog?q=${encodeURIComponent('áo thun; không màu')}`)
  await expect(page.getByRole('alert')).toContainText('Chưa rõ điều kiện loại trừ')
  await expect(page.getByRole('combobox', { name: 'Tên sản phẩm hoặc mã sản phẩm' })).toHaveValue('áo thun; không màu')
  await page.getByLabel('Tự hiểu loại trừ màu, hãng, danh mục').uncheck()
  await expect(page.getByRole('alert')).toHaveCount(0)
  await expect(page.getByTestId('product-card').first()).toBeVisible()
})

test('real CPU text UI exclusion, conflict correction and responsive notice', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('product-card').first()).toBeVisible()
  await page.getByTestId('search-text').fill('áo thun; không màu đỏ; dưới 1 triệu')
  await page.getByTestId('filter-category').selectOption('t_shirt')
  const pending = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/search' && r.request().method() === 'POST')
  await page.getByTestId('search-submit').click()
  const response = await pending
  expect(response.status()).toBe(200)
  const body = await response.json()
  expect(body.results.length).toBeGreaterThan(0)
  expect(body.results.every((r: { product: { category: string; color: string; price_vnd: number } }) => r.product.category === 't_shirt' && !/đỏ/.test(r.product.color) && r.product.price_vnd < 1000000)).toBe(true)
  const notice = page.getByRole('status', { name: 'Điều kiện loại trừ đã hiểu' })
  await expect(notice).toContainText('Màu: đỏ')
  for (const width of [360, 1440]) {
    await page.setViewportSize({ width, height: 1000 })
    if (width <= 800) {
      const filter = page.getByRole('button', { name: /^Bộ lọc/ }).first()
      if (await filter.getAttribute('aria-expanded') === 'false') await filter.click()
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
    await page.screenshot({ path: `../artifacts/frontend/screenshots/exclusions/search-${width}.png`, fullPage: true })
  }
  await page.getByTestId('search-text').fill('ngoại trừ thương hiệu Nike')
  await page.getByTestId('filter-brand').selectOption('Nike')
  await page.getByTestId('search-submit').click()
  await expect(page.getByRole('alert')).toContainText('mâu thuẫn')
  await expect(page.getByTestId('search-text')).toHaveValue('ngoại trừ thương hiệu Nike')
  await page.getByLabel('Tự hiểu loại trừ màu, hãng, danh mục').uncheck()
  const retry = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/search' && r.status() === 200)
  await page.getByTestId('search-submit').click()
  expect((await (await retry).json()).meta.exclusion_interpretation.applied).toBe(false)
  await expect(notice).toHaveCount(0)
})

test('real CPU multimodal, semantic and manual voice retain exclusion constraints', async ({ request }) => {
  const photo = readFileSync(new URL('../../data/authoring/P181.jpg', import.meta.url))
  const results = []
  for (const [mode, strategy] of [['text', 'semantic'], ['voice', 'hybrid'], ['multimodal', 'hybrid']] as const) {
    const text = 'áo thun; không màu đỏ'
    const options = { search_strategy: strategy, filters: { category: 't_shirt' }, top_k: 20 }
    const response = mode === 'multimodal'
      ? await request.post('/api/v1/search/multimodal', { multipart: { text, text_weight: '0.5', options: JSON.stringify(options), image: { name: 'photo.jpg', mimeType: 'image/jpeg', buffer: photo } } })
      : await request.post('/api/v1/search', { data: { mode, text, options, ...(mode === 'voice' ? { voice_source: 'manual_transcript' } : {}) } })
    expect(response.status()).toBe(200)
    const body = await response.json()
    expect(body.query.text).toBe(text)
    expect(body.results.length).toBeGreaterThan(0)
    expect(body.results.every((r: { product: { color: string; product_id: string } }) => !/đỏ/.test(r.product.color) && r.product.product_id !== 'P181')).toBe(true)
    expect(body.meta.exclusion_interpretation.applied).toBe(true)
    results.push({ mode, strategy, response: body })
  }
  writeFileSync(new URL('../../artifacts/backend/exclusions-real-encoder.json', import.meta.url), JSON.stringify({ scope: 'Live CPU hard exclusion properties, not independent relevance quality or speech recognition', speech_calls: 0, results }, null, 2))
})
