import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('real catalog: inferred price, explicit opt-out, URL history and suggestions', async ({ page }) => {
  const params = new URLSearchParams({ q: 'ao thun duoi 1 trieu', sort: 'price_desc', limit: '3' })
  await page.goto(`/catalog?${params}`)
  await expect(page.getByTestId('product-card')).toHaveCount(3)
  const notice = page.getByRole('status', { name: 'Điều kiện giá đã hiểu' })
  await expect(notice).toContainText('duoi 1 trieu')
  await expect(notice).toContainText('999.999')
  await expect(page.getByLabel('Cao nhất', { exact: true })).toHaveValue('')
  const result = await (await page.request.get(`/api/v1/catalog?${params}`)).json()
  expect(result.products.every((p: { price_vnd: number }) => p.price_vnd < 1000000)).toBe(true)
  await expect(page.getByTestId('product-card').first()).toContainText(result.products[0].name)
  const input = page.getByRole('combobox', { name: 'Tên sản phẩm hoặc mã sản phẩm' })
  await input.fill('ao thun duoi 1 trieu')
  await input.focus()
  await expect(page.getByRole('listbox')).toBeVisible()
  const suggested = await (await page.request.get('/api/v1/suggestions?q=ao+thun+duoi+1+trieu')).json()
  expect(suggested.products.every((p: { price_vnd: number }) => p.price_vnd < 1000000)).toBe(true)
  await page.getByLabel('Tự hiểu điều kiện giá trong mô tả').uncheck()
  await expect(page).toHaveURL(/interpret_price=false/)
  await expect(notice).toHaveCount(0)
  const unfiltered = await (await page.request.get(`/api/v1/catalog?${new URL(page.url()).searchParams}`)).json()
  expect(unfiltered.products.some((p: { price_vnd: number }) => p.price_vnd >= 1000000)).toBe(true)
  await expect(page.getByTestId('product-card').first()).toContainText(unfiltered.products[0].name)
  await page.goBack()
  await expect(notice).toBeVisible()
  await expect(page.getByLabel('Tự hiểu điều kiện giá trong mô tả')).toBeChecked()
  await page.getByLabel('Chỉ còn hàng').check()
  await expect(page).toHaveURL(/in_stock=true/)
  await page.getByLabel('Chỉ còn hàng').uncheck()
  await expect(page).not.toHaveURL(/in_stock=/)
})

test('real AI search: hard budget, visible effective bounds, conflict recovery and bounded visual batch', async ({ page, context }) => {
  await page.goto('/')
  await expect(page.getByTestId('product-card').first()).toBeVisible()
  await page.getByTestId('search-text').fill('áo thun dưới 1 triệu')
  await page.getByTestId('filter-category').selectOption('t_shirt')
  const pending = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/search' && response.request().method() === 'POST')
  await page.getByTestId('search-submit').click()
  const response = await pending
  expect(response.status()).toBe(200)
  const body = await response.json()
  expect(body.meta.model_fingerprint).toMatch(/^[0-9a-f]{64}$/)
  expect(body.results.length).toBeGreaterThan(0)
  expect(body.results.every((r: { product: { price_vnd: number } }) => r.product.price_vnd < 1000000)).toBe(true)
  expect(body.meta.price_interpretation.effective_filters.max_price).toBe(999999)
  await expect(page.getByRole('status', { name: 'Điều kiện giá đã hiểu' })).toContainText('dưới 1 triệu')
  const catalog = await context.newPage()
  try {
    await catalog.goto('/catalog?q=ao+thun+tu+500k+den+1tr&sort=price_asc')
    await expect(catalog.getByRole('status', { name: 'Điều kiện giá đã hiểu' })).toBeVisible()
    for (const width of [360, 768, 1440]) {
      for (const [surface, target] of [['search', page], ['catalog', catalog]] as const) {
        await target.setViewportSize({ width, height: 1000 })
        if (width <= 800) {
          const filter = target.getByRole('button', { name: /^Bộ lọc/, exact: false }).first()
          if (await filter.getAttribute('aria-expanded') === 'false') await filter.click()
        }
        const overflow = await target.evaluate(() => document.documentElement.scrollWidth - innerWidth)
        expect.soft(overflow).toBeLessThanOrEqual(1)
        expect.soft((await new AxeBuilder({ page: target }).analyze()).violations).toEqual([])
        await target.screenshot({ path: `../artifacts/frontend/screenshots/price-query/${surface}-${width}.png`, fullPage: true })
      }
    }
  } finally { await catalog.close() }
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.getByTestId('min-price').fill('2000000')
  const failed = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/search' && r.status() === 422)
  await page.getByTestId('search-submit').click()
  expect((await (await failed).json()).error.code).toBe('PRICE_FILTER_CONFLICT')
  await expect(page.getByRole('alert')).toContainText('mâu thuẫn với bộ lọc')
  await expect(page.getByTestId('min-price')).toHaveValue('2000000')
  await expect(page.getByTestId('search-text')).toHaveValue('áo thun dưới 1 triệu')
  await page.getByTestId('min-price').fill('')
  await page.getByLabel('Tự hiểu điều kiện giá trong mô tả').uncheck()
  const retry = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/search' && r.status() === 200)
  await page.getByTestId('search-submit').click()
  expect((await (await retry).json()).meta.price_interpretation.applied).toBe(false)
  await expect(page.getByRole('status', { name: 'Điều kiện giá đã hiểu' })).toHaveCount(0)
})

test('real ambiguous price and currency errors retain query and offer explicit recovery', async ({ page }) => {
  for (const query of ['áo thun dưới 1.500 triệu', 'áo dưới 100USD', 'áo dưới 1tr hoặc trên 2tr']) {
    await page.goto(`/catalog?q=${encodeURIComponent(query)}`)
    await expect(page.getByRole('alert')).toBeVisible()
    await expect(page.getByRole('combobox', { name: 'Tên sản phẩm hoặc mã sản phẩm' })).toHaveValue(query)
  }
  await page.getByRole('combobox', { name: 'Tên sản phẩm hoặc mã sản phẩm' }).fill('áo thun dưới 1 triệu')
  await page.getByRole('button', { name: 'Tìm trong bộ sưu tập', exact: true }).click()
  await expect(page.getByTestId('product-card').first()).toBeVisible()
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('real manual transcript: Vietnamese spoken price numbers constrain voice search without STT', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('product-card').first()).toBeVisible()
  await page.getByRole('tab', { name: 'Giọng nói', exact: true }).click()
  await page.getByTestId('voice-transcript').fill('áo thun từ năm trăm nghìn đến một triệu')
  await page.getByTestId('filter-category').selectOption('t_shirt')
  const pending = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/search' && r.request().method() === 'POST')
  await page.getByTestId('search-submit').click()
  const response = await pending
  expect(response.status()).toBe(200)
  const body = await response.json()
  expect(body.query.mode).toBe('voice')
  expect(body.query.voice_source).toBe('manual_transcript')
  expect(body.meta.price_interpretation.inferred_filters).toEqual({ min_price: 500000, max_price: 1000000 })
  expect(body.results.length).toBeGreaterThan(0)
  expect(body.results.every((r: { product: { price_vnd: number } }) => r.product.price_vnd >= 500000 && r.product.price_vnd <= 1000000)).toBe(true)
  await expect(page.getByRole('status', { name: 'Điều kiện giá đã hiểu' })).toContainText('năm trăm nghìn')
})
