import { test, expect } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import AxeBuilder from '@axe-core/playwright'

const email = `admin-e2e-size-scope-${Date.now()}@example.test`
const password = `Fixture-${randomUUID()}-${randomUUID()}`
const python = fileURLToPath(new URL('../../backend/.venv/Scripts/python.exe', import.meta.url))
const fixture = fileURLToPath(new URL('../../scripts/admin_browser_fixture.py', import.meta.url))
const query = 'áo thun size M P041'
const adminHeaders = { 'X-Cortis-Intent': 'admin' }

test.beforeAll(() => {
  execFileSync(python, [fixture, 'provision', '--email', email], { env: { ...process.env, CORTIS_E2E_ADMIN_PASSWORD: password }, stdio: 'pipe' })
})
test.afterAll(() => { execFileSync(python, [fixture, 'retire', '--email', email], { stdio: 'pipe' }) })

test('real size intent: requested size stock, visible availability, live CPU modes and restoration', async ({ page }) => {
  test.setTimeout(60_000)
  const login = await page.request.post('/api/v1/auth/login', { headers: { 'X-Cortis-Intent': 'account' }, data: { email, password } })
  expect(login.status()).toBe(200)
  const before = (await (await page.request.get('/api/v1/products/P041')).json()).product
  const selected = before.variants.find((v: { size: string }) => v.size === 'M')
  expect(selected, 'Prepare P041-M/L with the documented admin size allocation flow first').toBeTruthy()
  expect(before.variants.find((v: { size: string }) => v.size === 'L').stock_quantity).toBeGreaterThan(0)
  const setStock = async (quantity: number) => {
    const inventory = await (await page.request.get('/api/v1/admin/inventory?q=P041')).json()
    const change = await page.request.post('/api/v1/admin/inventory/P041-M', { headers: adminHeaders, data: { quantity, revision: inventory.revision, reason: 'E2E requested-size search verification' } })
    expect(change.status()).toBe(200)
  }
  const evidence: Record<string, unknown> = { scope: 'Actual browser/API/CPU variant-stock properties; manual voice is not STT', speech_calls: 0, before }
  try {
    await setStock(0)
    await page.goto(`/catalog?q=${encodeURIComponent(query)}`)
    const notice = page.getByRole('status', { name: 'Phạm vi tìm kiếm đã hiểu' })
    await expect(notice).toContainText('Cỡ M')
    await expect(page.getByTestId('product-card')).toHaveCount(1)
    await expect(page.getByTestId('product-card')).toContainText('Cỡ M: hết hàng')
    await expect(page.getByTestId('product-card')).toContainText('Hết cỡ đã tìm')
    await page.reload()
    await expect(notice).toContainText('Cỡ M')
    const soldOut = await (await page.request.get(`/api/v1/catalog?q=${encodeURIComponent(query)}&in_stock=true`)).json()
    expect(soldOut.products).toEqual([])
    const suggestions = await (await page.request.get(`/api/v1/suggestions?q=${encodeURIComponent(query)}`)).json()
    expect(suggestions.products.map((p: { product_id: string }) => p.product_id)).toEqual(['P041'])
    expect(suggestions.products[0].available_sizes).not.toContain('M')
    const conflict = await page.request.get(`/api/v1/catalog?q=${encodeURIComponent(query)}&size=L`)
    expect(conflict.status()).toBe(422)
    expect((await conflict.json()).error.field_errors[0].field).toBe('filters.size')
    await page.getByLabel('Tự hiểu hãng, loại, màu và kích cỡ').uncheck()
    await expect(page).toHaveURL(/interpret_scope=false/)
    await expect(notice).toHaveCount(0)
    await page.goBack()
    await expect(notice).toContainText('Cỡ M')
    await page.goto('/')
    await expect(page.getByTestId('product-card').first()).toBeVisible()
    await page.getByTestId('search-text').fill(query)
    const pending = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/search' && r.request().method() === 'POST')
    await page.getByTestId('search-submit').click()
    expect((await pending).status()).toBe(200)
    await expect(page.getByTestId('result-card')).toHaveCount(1)
    await expect(page.getByTestId('result-card')).toContainText('Cỡ M: hết hàng')
    for (const width of [360, 1440]) {
      await page.setViewportSize({ width, height: 1000 })
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
      expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
      await page.screenshot({ path: `../artifacts/frontend/screenshots/size-scope/search-${width}.png`, fullPage: true })
    }
    const photo = readFileSync(new URL('../../data/images/P041.jpg', import.meta.url))
    const results = []
    for (const inStock of [false, true]) {
      for (const [mode, strategy] of [['text', 'semantic'], ['text', 'hybrid'], ['voice', 'hybrid'], ['multimodal', 'hybrid']] as const) {
        const options = { top_k: 20, search_strategy: strategy, filters: { in_stock: inStock } }
        const response = mode === 'multimodal'
          ? await page.request.post('/api/v1/search/multimodal', { multipart: { text: query, text_weight: '0.5', options: JSON.stringify(options), image: { name: 'shirt.jpg', mimeType: 'image/jpeg', buffer: photo } } })
          : await page.request.post('/api/v1/search', { data: { mode, text: query, options, ...(mode === 'voice' ? { voice_source: 'manual_transcript' } : {}) } })
        expect(response.status()).toBe(200)
        const body = await response.json()
        expect(body.results.map((r: { product: { product_id: string } }) => r.product.product_id)).toEqual(inStock ? [] : ['P041'])
        results.push({ mode, strategy, in_stock: inStock, response: body })
      }
    }
    Object.assign(evidence, { soldOut, suggestions, results, meta: await (await page.request.get('/api/v1/meta')).json() })
  } finally {
    await setStock(selected.stock_quantity)
    const after = (await (await page.request.get('/api/v1/products/P041')).json()).product
    expect(after).toEqual(before)
    Object.assign(evidence, { after, restored: true })
    writeFileSync(new URL('../../artifacts/backend/size-scope-real-encoder.json', import.meta.url), JSON.stringify(evidence, null, 2))
  }
})
