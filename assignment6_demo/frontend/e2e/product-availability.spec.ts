import { test, expect } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { readFileSync, writeFileSync } from 'node:fs'
import { randomUUID } from 'node:crypto'
import AxeBuilder from '@axe-core/playwright'

const email = `admin-e2e-availability-${Date.now()}@example.test`
const password = `Fixture-${randomUUID()}-${randomUUID()}`
const python = fileURLToPath(new URL('../../backend/.venv/Scripts/python.exe', import.meta.url))
const fixture = fileURLToPath(new URL('../../scripts/admin_browser_fixture.py', import.meta.url))
const pid = 'P013', admin = { 'X-Cortis-Intent': 'admin' }, shop = { 'X-Cortis-Intent': 'commerce' }

test.beforeAll(() => execFileSync(python, [fixture, 'provision', '--email', email], { env: { ...process.env, CORTIS_E2E_ADMIN_PASSWORD: password }, stdio: 'pipe' }))
test.afterAll(async ({ request }) => {
  try {
    const login = await request.post('/api/v1/auth/login', { headers: { 'X-Cortis-Intent': 'account' }, data: { email, password } })
    expect(login.status()).toBe(200)
    const state = (await (await request.get(`/api/v1/admin/products/${pid}/draft`)).json()).draft
    if (state.sale_state === 'archived') {
      const restored = await request.post(`/api/v1/admin/products/${pid}/sale-state`, { headers: admin, data: { sale_state: 'active', revision: state.inventory_revision, reason: 'Restore E2E fixture product' } })
      expect(restored.status()).toBe(200)
    }
    const cart = (await (await request.get('/api/v1/cart')).json()).cart
    for (const item of cart.items) {
      const current = (await (await request.get('/api/v1/cart')).json()).cart
      expect((await request.post('/api/v1/cart/items', { headers: shop, data: { product_id: item.product_id, variant_id: item.variant_id, quantity: 0, version: current.version } })).status()).toBe(200)
    }
    await request.post('/api/v1/wishlist/items', { headers: shop, data: { product_id: pid, saved: false } })
  } finally { execFileSync(python, [fixture, 'retire', '--email', email], { stdio: 'pipe' }) }
})

test('real admin archive and restore: private audit, search visibility, cart and stale quote', async ({ page, context }) => {
  test.setTimeout(60_000)
  await page.goto('/account')
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).last().click()
  await page.getByRole('link', { name: 'Mở trang quản trị' }).click()
  await page.getByRole('button', { name: 'Sản phẩm', exact: true }).click()
  await page.getByLabel('Mã sản phẩm cần tạo hoặc mở', { exact: true }).fill(pid)
  await page.getByRole('button', { name: 'Mở mã sản phẩm', exact: true }).click()
  const before = (await (await page.request.get(`/api/v1/products/${pid}`)).json()).product
  expect(before.sale_state).toBe('active')
  expect(before.stock_quantity).toBeGreaterThan(0)
  const meta = await (await page.request.get('/api/v1/meta')).json()
  const count = (await (await page.request.get('/api/v1/products?limit=1')).json()).total
  const cart = (await (await page.request.get('/api/v1/cart')).json()).cart
  expect((await page.request.post('/api/v1/cart/items', { headers: shop, data: { product_id: pid, quantity: 1, version: cart.version } })).status()).toBe(200)
  expect((await page.request.post('/api/v1/wishlist/items', { headers: shop, data: { product_id: pid, saved: true } })).status()).toBe(200)
  const quote = (await (await page.request.post('/api/v1/checkout/quote', { headers: shop, data: {} })).json()).quote
  const region = page.getByRole('region', { name: 'Trạng thái bán', exact: true })
  await region.getByRole('button', { name: 'Tạm ngừng bán sản phẩm', exact: true }).click()
  await page.getByLabel('Lý do đổi trạng thái bán').fill('Review catalog fixture visibility')
  for (const width of [360, 1440]) {
    await page.setViewportSize({ width, height: 1000 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
    await region.screenshot({ path: `../artifacts/frontend/screenshots/availability/admin-${width}.png` })
  }
  const pending = page.waitForResponse(r => new URL(r.url()).pathname.endsWith('/sale-state'))
  await region.getByRole('button', { name: 'Xác nhận ngừng bán', exact: true }).click()
  expect((await pending).status()).toBe(200)
  await expect(region).toContainText('Đang tạm ngừng bán')
  const hidden = await (await page.request.get(`/api/v1/catalog?q=${pid}`)).json()
  expect(hidden.total).toBe(0)
  expect((await (await page.request.get(`/api/v1/suggestions?q=${pid}`)).json()).products).toEqual([])
  expect((await (await page.request.get('/api/v1/products?limit=1')).json()).total).toBe(count - 1)
  const archivedCart = (await (await page.request.get('/api/v1/cart')).json()).cart
  expect(archivedCart.items[0].issue).toBe('PRODUCT_ARCHIVED')
  const rejected = await page.request.post('/api/v1/purchases', { headers: shop, data: { quote_id: quote.quote_id, idempotency_key: randomUUID(), shipping_address: { recipient: 'E2E buyer', phone: '0900000000', address_line: 'Local test address', city: 'Demo city' } } })
  expect(rejected.status()).toBe(409)
  expect((await rejected.json()).error.code).toBe('PRODUCT_ARCHIVED')
  const customer = await context.newPage()
  try {
    await customer.goto(`/products/${pid}`)
    await expect(customer.getByRole('button', { name: 'Tạm ngừng bán', exact: true })).toBeDisabled()
    await expect(customer.getByText('Sản phẩm tạm ngừng bán', { exact: true })).toBeVisible()
    for (const width of [360, 1440]) {
      await customer.setViewportSize({ width, height: 1000 })
      expect(await customer.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(1)
      expect((await new AxeBuilder({ page: customer }).analyze()).violations).toEqual([])
      await customer.locator('.detail-copy').screenshot({ path: `../artifacts/frontend/screenshots/availability/customer-${width}.png` })
    }
  } finally { await customer.close() }
  const photo = readFileSync(new URL('../../data/images/P013.jpg', import.meta.url))
  const results = []
  for (const mode of ['text', 'voice', 'image', 'multimodal'] as const) {
    const options = { top_k: 20, search_strategy: 'hybrid' }
    const result = mode === 'text' || mode === 'voice'
      ? await page.request.post('/api/v1/search', { data: { mode, text: pid, options, ...(mode === 'voice' ? { voice_source: 'manual_transcript' } : {}) } })
      : await page.request.post(`/api/v1/search/${mode}`, { multipart: { options: JSON.stringify(options), image: { name: 'photo.jpg', mimeType: 'image/jpeg', buffer: photo }, ...(mode === 'multimodal' ? { text: pid, text_weight: '0.5' } : {}) } })
    expect(result.status()).toBe(200)
    const body = await result.json()
    expect(body.results.every((r: { product: { product_id: string } }) => r.product.product_id !== pid)).toBe(true)
    expect(body.meta.index_fingerprint).toBe(meta.index.index_fingerprint)
    results.push({ mode, response: body })
  }
  await region.getByRole('button', { name: 'Mở bán lại sản phẩm', exact: true }).click()
  await page.getByLabel('Lý do đổi trạng thái bán').fill('Restore reviewed fixture product')
  const restored = page.waitForResponse(r => new URL(r.url()).pathname.endsWith('/sale-state'))
  await region.getByRole('button', { name: 'Xác nhận mở bán lại', exact: true }).click()
  expect((await restored).status()).toBe(200)
  await expect(region).toContainText('Đang mở bán')
  const after = (await (await page.request.get(`/api/v1/products/${pid}`)).json()).product
  expect(after).toEqual(before)
  expect((await (await page.request.get(`/api/v1/catalog?q=${pid}`)).json()).total).toBe(1)
  const audit = await (await page.request.get('/api/v1/admin/audit?limit=100')).json()
  expect(audit.events.filter((e: { action: string; subject_id: string }) => e.action === 'product.sale_state' && e.subject_id === pid).length).toBeGreaterThanOrEqual(2)
  writeFileSync(new URL('../../artifacts/backend/availability-real-encoder.json', import.meta.url), JSON.stringify({ scope: 'Actual admin and CPU availability properties; image self-match input is not independent relevance, manual voice not STT', speech_calls: 0, before, after, meta, hidden, archived_cart_issue: archivedCart.items[0].issue, results }, null, 2))
})
