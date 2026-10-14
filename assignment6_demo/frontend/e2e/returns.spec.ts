import { test, expect, type Page } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { randomUUID } from 'node:crypto'
import AxeBuilder from '@axe-core/playwright'
import { expectNoHorizontalOverflow } from './helpers'

const origin = 'http://127.0.0.1:5173'
const email = `admin-e2e-return-${randomUUID()}@example.test`
const password = `Fixture-${randomUUID()}-${randomUUID()}`
const python = fileURLToPath(new URL('../../backend/.venv/Scripts/python.exe', import.meta.url))
const fixture = fileURLToPath(new URL('../../scripts/admin_browser_fixture.py', import.meta.url))
const ah = { 'X-Cortis-Intent': 'admin' }, ch = { 'X-Cortis-Intent': 'commerce' }
const buyers: string[] = []

test.beforeAll(() => execFileSync(python, [fixture, 'provision', '--email', email], { env: { ...process.env, CORTIS_E2E_ADMIN_PASSWORD: password }, stdio: 'pipe' }))
test.afterAll(() => {
  for (const buyer of buyers) execFileSync(python, [fixture, 'retire', '--email', buyer], { stdio: 'pipe' })
  execFileSync(python, [fixture, 'retire', '--email', email], { stdio: 'pipe' })
})

async function admin(page: Page) {
  expect((await page.request.post(`${origin}/api/v1/auth/login`, { headers: { 'X-Cortis-Intent': 'account' }, data: { email, password } })).status()).toBe(200)
}

test('real return lifecycle: partial quantities, withdrawal, approval, quarantine/restock and demo closure', async ({ page, browser }) => {
  await admin(page)
  const initial = await (await page.request.get('/api/v1/admin/inventory?q=P001')).json()
  const originalStock = initial.items[0].quantity
  if (originalStock < 2) expect((await page.request.post('/api/v1/admin/inventory/P001', { headers: ah, data: { quantity: 2, revision: initial.revision, reason: 'Prepare reserved returns fixture' } })).status()).toBe(200)
  const buyer = await browser.newContext(), buyerPage = await buyer.newPage()
  const buyerEmail = `admin-e2e-return-buyer-${randomUUID()}@example.test`
  buyers.push(buyerEmail)
  let activeReturn: { return_id: string; version: number; status: string } | undefined
  try {
    expect((await buyer.request.post(`${origin}/api/v1/auth/register`, { headers: { 'X-Cortis-Intent': 'account' }, data: { email: buyerEmail, password: `Buyer-${randomUUID()}-${randomUUID()}`, display_name: 'Return buyer demo' } })).status()).toBe(201)
    expect((await buyer.request.post(`${origin}/api/v1/cart/items`, { headers: ch, data: { product_id: 'P001', quantity: 2, version: 0 } })).status()).toBe(200)
    const quote = (await (await buyer.request.post(`${origin}/api/v1/checkout/quote`, { headers: ch, data: {} })).json()).quote
    const placed = await buyer.request.post(`${origin}/api/v1/purchases`, { headers: ch, data: { quote_id: quote.quote_id, idempotency_key: randomUUID(), shipping_address: { recipient: 'Return demo buyer', phone: '0900000000', address_line: 'Test demo address', city: 'Demo city' } } })
    expect(placed.status()).toBe(201)
    const order = (await placed.json()).order
    for (const [status, version] of [['shipped', 0], ['delivered', 1]]) expect((await page.request.post(`/api/v1/admin/purchases/${order.order_id}/status`, { headers: ah, data: { status, version, reason: 'Returns fixture delivery' } })).status()).toBe(200)
    const afterPurchase = (await (await page.request.get('/api/v1/products/P001')).json()).product.stock_quantity
    await buyerPage.goto(`${origin}/orders/${order.order_id}`)
    const returns = buyerPage.getByRole('region', { name: 'Trả hàng', exact: true })
    const quantity = returns.getByLabel(/Số lượng trả/)
    await quantity.fill('1')
    await returns.getByLabel('Lý do trả hàng').fill('Kích thước chưa phù hợp')
    await buyerPage.route('**/api/v1/purchases/*/returns', async route => {
      const response = await route.fetch()
      expect(response.status()).toBe(201)
      await route.abort('failed') // The real server committed, but its response is lost.
    }, { times: 1 })
    await returns.getByRole('button', { name: 'Gửi yêu cầu trả hàng', exact: true }).click()
    await expect(returns.getByRole('button', { name: 'Kiểm tra lại yêu cầu trả hàng', exact: true })).toBeVisible()
    await returns.getByRole('button', { name: 'Kiểm tra lại yêu cầu trả hàng', exact: true }).click()
    await expect(returns.getByText('Chờ duyệt', { exact: true })).toBeVisible()
    let rows = await (await buyer.request.get(`${origin}/api/v1/purchases/${order.order_id}/returns`)).json()
    expect(rows.returns).toHaveLength(1)
    activeReturn = rows.returns[0]
    await returns.getByRole('button', { name: `Rút yêu cầu ${activeReturn!.return_id}`, exact: true }).click()
    await expect(returns.getByText('Khách đã rút', { exact: true })).toBeVisible()
    await quantity.fill('2')
    await returns.getByLabel('Lý do trả hàng').fill('Kiểm tra đường may và kích thước')
    await returns.getByRole('button', { name: 'Gửi yêu cầu trả hàng', exact: true }).click()
    await expect(returns.getByText('Toàn bộ số lượng đã có yêu cầu trả hàng.')).toBeVisible()
    rows = await (await buyer.request.get(`${origin}/api/v1/purchases/${order.order_id}/returns`)).json()
    activeReturn = rows.returns[0]
    const id = activeReturn!.return_id
    const caseArticle = page.locator('article.admin-record').filter({ has: page.getByRole('heading', { name: id, exact: true }) })
    await page.goto('/admin')
    await page.getByRole('link', { name: 'Trả hàng', exact: true }).click()
    await page.getByLabel('Lý do xử lý').fill('Duyệt nhận hàng để kiểm tra')
    await page.getByRole('button', { name: `Duyệt ${id}`, exact: true }).click()
    await expect(page.getByRole('button', { name: `Xác nhận đã nhận hàng ${id}`, exact: true })).toBeVisible()
    expect((await (await page.request.get('/api/v1/products/P001')).json()).product.stock_quantity).toBe(afterPurchase)
    await page.getByLabel('Lý do xử lý').fill('Một sản phẩm đủ điều kiện, một sản phẩm cần cách ly')
    await page.getByLabel('Nhập lại kho P001', { exact: true }).fill('1')
    await page.getByRole('button', { name: `Xác nhận đã nhận hàng ${id}`, exact: true }).click()
    await expect(page.getByRole('button', { name: `Đóng hồ sơ demo ${id}`, exact: true })).toBeVisible()
    expect((await (await page.request.get('/api/v1/products/P001')).json()).product.stock_quantity).toBe(afterPurchase + 1)
    await page.getByLabel('Lý do xử lý').fill('Ghi nhận đối soát trong hệ thống demo')
    await page.getByRole('button', { name: `Đóng hồ sơ demo ${id}`, exact: true }).click()
    await expect(caseArticle.getByText('Đã đóng hồ sơ demo', { exact: true })).toBeVisible()
    await buyerPage.reload()
    await expect(returns.getByText('Đã đóng hồ sơ demo', { exact: true })).toBeVisible()
    await expect(returns.getByText(/Chưa thực hiện hoàn tiền thật/)).toBeVisible()
    expect((await (await buyer.request.get(`${origin}/api/v1/purchases/${order.order_id}`)).json()).order.payment_status).toBe('unpaid')
    // One bounded batch for both new surfaces; business assertions above use real APIs.
    for (const width of [360, 768, 1440]) {
      for (const [surface, target] of [['admin', page], ['customer', buyerPage]] as const) {
        await target.setViewportSize({ width, height: 1000 })
        await expectNoHorizontalOverflow(target)
        if (surface === 'admin') {
          const box = await caseArticle.locator(':scope > div').first().boundingBox()
          expect(box!.width).toBeGreaterThanOrEqual(260)
        }
        if (process.env.CORTIS_RETURNS_FUNCTIONAL_ONLY !== '1') {
          expect((await new AxeBuilder({ page: target }).analyze()).violations).toEqual([])
          await target.screenshot({ path: `../artifacts/frontend/screenshots/returns/${surface}-${width}.png`, fullPage: true })
        }
      }
    }
  } finally {
    if (activeReturn) {
      const currentRows = await (await page.request.get('/api/v1/admin/returns?limit=100')).json()
      const current = currentRows.returns?.find((r: { return_id: string }) => r.return_id === activeReturn?.return_id)
      if (current && ['requested', 'approved'].includes(current.status)) await page.request.post(`/api/v1/admin/returns/${current.return_id}/status`, { headers: ah, data: { status: 'rejected', version: current.version, reason: 'Retire unfinished returns fixture' } })
    }
    const stock = await (await page.request.get('/api/v1/admin/inventory?q=P001')).json()
    expect((await page.request.post('/api/v1/admin/inventory/P001', { headers: ah, data: { quantity: originalStock, revision: stock.revision, reason: 'Restore inventory after returns fixture' } })).status()).toBe(200)
    await buyer.close()
  }
})

test('admin return direct URL is denied for an anonymous browser', async ({ page }) => {
  await page.goto('/admin/returns')
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.getByLabel('Lý do xử lý')).toHaveCount(0)
  expect((await page.request.get('/api/v1/admin/returns')).status()).toBe(401)
})
