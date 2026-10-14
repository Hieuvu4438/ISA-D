import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { expectNoHorizontalOverflow } from './helpers'

async function prepare(page: Page) {
  const response = await page.request.post('/api/v1/auth/register', { headers: { 'X-Cortis-Intent': 'account' }, data: { email: `checkout-${Date.now()}@example.test`, display_name: 'Checkout demo', password: 'Browser checkout passphrase 2026' } })
  expect(response.status()).toBe(201)
  const before = (await (await page.request.get('/api/v1/products/P001')).json()).product.stock_quantity
  expect(before).toBeGreaterThan(0)
  expect((await page.request.post('/api/v1/cart/items', { headers: { 'X-Cortis-Intent': 'commerce' }, data: { product_id: 'P001', quantity: 1, version: 0 } })).status()).toBe(200)
  await page.goto('/cart')
  await page.getByRole('link', { name: 'Tiếp tục đặt hàng', exact: true }).click()
  await page.getByRole('button', { name: 'Kiểm tra giỏ và lấy báo giá' }).click()
  await expect(page.getByRole('heading', { name: 'Thông tin nhận hàng' })).toBeVisible()
  return before
}

async function address(page: Page) {
  await page.getByLabel('Người nhận', { exact: true }).fill('Khách demo')
  await page.getByLabel('Số điện thoại', { exact: true }).fill('0900000000')
  await page.getByLabel('Địa chỉ nhận hàng', { exact: true }).fill('Địa chỉ kiểm thử')
  await page.getByLabel('Tỉnh / thành phố', { exact: true }).fill('Thành phố demo')
}

test('real checkout API: quote, COD placement, history, detail reload and cancel', async ({ page }) => {
  const before = await prepare(page)
  await expect(page.getByText('1.830.000 ₫', { exact: true })).toBeVisible()
  await address(page)
  await page.getByRole('button', { name: /^Đặt đơn COD/ }).click()
  await expect(page).toHaveURL(/\/orders\/ORD-[A-F0-9]{16}$/)
  const id = page.url().split('/').pop()!
  await expect(page.getByRole('heading', { name: `Đơn hàng ${id}.` })).toBeVisible()
  await page.reload()
  await expect(page.getByText('Khách demo', { exact: false })).toBeVisible()
  expect((await (await page.request.get('/api/v1/cart')).json()).cart.item_count).toBe(0)
  expect((await (await page.request.get('/api/v1/products/P001')).json()).product.stock_quantity).toBe(before - 1)
  await page.goto('/orders')
  await page.getByLabel('Mã đơn hàng', { exact: true }).fill(id)
  await page.getByRole('button', { name: /Tra cứu/ }).click()
  await expect(page.locator(`a[href="/orders/${id}"]`)).toBeVisible()
  await page.goto('/purchases')
  await expect(page.getByRole('link', { name: id, exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Xem chi tiết', exact: true }).click()
  await page.getByRole('button', { name: 'Hủy đơn hàng', exact: true }).click()
  await page.getByRole('button', { name: 'Xác nhận hủy đơn', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('Đã hủy đơn và hoàn lại tồn kho')
  expect((await (await page.request.get('/api/v1/products/P001')).json()).product.stock_quantity).toBe(before)
})

test('real checkout commit then lost HTTP response: explicit retry returns same single order', async ({ page }) => {
  const before = await prepare(page)
  await address(page)
  let committed = ''
  await page.route('**/api/v1/purchases', async route => {
    if (route.request().method() === 'POST' && !committed) {
      const response = await route.fetch()
      expect(response.status()).toBe(201)
      committed = (await response.json()).order.order_id
      await route.abort('failed')
    } else await route.continue()
  })
  await page.getByRole('button', { name: /^Đặt đơn COD/ }).click()
  await expect(page.getByRole('heading', { name: 'Chưa xác nhận được kết quả' })).toBeVisible()
  await page.getByRole('button', { name: 'Kiểm tra lại yêu cầu đặt đơn' }).click()
  await expect(page).toHaveURL(new RegExp(`/orders/${committed}$`))
  const history = await page.request.get('/api/v1/purchases')
  expect((await history.json()).total).toBe(1)
  expect((await (await page.request.get('/api/v1/products/P001')).json()).product.stock_quantity).toBe(before - 1)
  await page.request.post(`/api/v1/purchases/${committed}/cancel`, { headers: { 'X-Cortis-Intent': 'commerce' }, data: { version: 0 } })
})

test('real checkout stale quote keeps submitted address when getting a fresh quote', async ({ page }) => {
  await prepare(page)
  await address(page)
  await page.request.post('/api/v1/cart/items', { headers: { 'X-Cortis-Intent': 'commerce' }, data: { product_id: 'P001', quantity: 2, version: 1 } })
  await page.getByRole('button', { name: /^Đặt đơn COD/ }).click()
  await expect(page.getByRole('alert')).toContainText('Giỏ hàng đã thay đổi')
  await page.getByRole('button', { name: 'Kiểm tra giỏ và lấy báo giá' }).click()
  await expect(page.getByLabel('Người nhận', { exact: true })).toHaveValue('Khách demo')
  await expect(page.getByRole('button', { name: /^Đặt đơn COD/ })).toContainText('3.600.000')
})

test('real inventory ledger and encoder agree after buying final units; cancel restores availability', async ({ page }) => {
  const before = await prepare(page)
  expect(before).toBeLessThanOrEqual(99)
  const meta = await (await page.request.get('/api/v1/meta')).json()
  expect(meta.capabilities.search.available).toBe(true)
  await page.request.post('/api/v1/cart/items', { headers: { 'X-Cortis-Intent': 'commerce' }, data: { product_id: 'P001', quantity: before, version: 1 } })
  const q = (await (await page.request.post('/api/v1/checkout/quote', { headers: { 'X-Cortis-Intent': 'commerce' }, data: {} })).json()).quote
  const placed = await page.request.post('/api/v1/purchases', { headers: { 'X-Cortis-Intent': 'commerce' }, data: { quote_id: q.quote_id, idempotency_key: crypto.randomUUID(), shipping_address: { recipient: 'Khách demo', phone: '0900000000', address_line: 'Địa chỉ kiểm thử', city: 'Thành phố demo' } } })
  expect(placed.status()).toBe(201)
  const order = (await placed.json()).order
  try {
    const search = await page.request.post('/api/v1/search', { data: { mode: 'text', text: 'P001', options: { search_strategy: 'hybrid', filters: { in_stock: true } } } })
    expect(search.status()).toBe(200)
    const body = await search.json()
    expect(body.results).toEqual([])
    expect(body.meta.index_fingerprint).toBe(meta.index.index_fingerprint)
    expect((await (await page.request.get('/api/v1/catalog?q=P001&in_stock=true')).json()).total).toBe(0)
    expect((await (await page.request.get('/api/v1/products/P001')).json()).product.in_stock).toBe(false)
  } finally {
    const cancel = await page.request.post(`/api/v1/purchases/${order.order_id}/cancel`, { headers: { 'X-Cortis-Intent': 'commerce' }, data: { version: 0 } })
    expect(cancel.status()).toBe(200)
  }
  expect((await (await page.request.get('/api/v1/products/P001')).json()).product.stock_quantity).toBe(before)
})

test('real checkout page: responsive/accessibility at all viewports', async ({ page }) => {
  await prepare(page)
  for (const width of [360, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 })
    await expectNoHorizontalOverflow(page)
    const axe = await new AxeBuilder({ page }).analyze()
    expect(axe.violations).toEqual([])
    await page.screenshot({ path: `../artifacts/frontend/screenshots/checkout/checkout-${width}.png`, fullPage: true })
  }
})
