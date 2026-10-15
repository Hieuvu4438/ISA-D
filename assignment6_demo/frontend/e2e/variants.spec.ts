import { test, expect, type Page } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { randomUUID } from 'node:crypto'
import AxeBuilder from '@axe-core/playwright'
import { expectNoHorizontalOverflow } from './helpers'

const email = `admin-e2e-variants-${Date.now()}@example.test`
const password = `Fixture-${randomUUID()}-${randomUUID()}`
const python = fileURLToPath(new URL('../../backend/.venv/Scripts/python.exe', import.meta.url))
const fixture = fileURLToPath(new URL('../../scripts/admin_browser_fixture.py', import.meta.url))
const adminHeaders = { 'X-Cortis-Intent': 'admin' }
const buyerEmail = `admin-e2e-variant-buyer-${randomUUID()}@example.test`

test.beforeAll(() => {
  execFileSync(python, [fixture, 'provision', '--email', email], { env: { ...process.env, CORTIS_E2E_ADMIN_PASSWORD: password }, stdio: 'pipe' })
})
test.afterAll(() => {
  for (const address of [email, buyerEmail]) execFileSync(python, [fixture, 'retire', '--email', address], { stdio: 'pipe' })
})

async function inspect(page: Page, surface: string) {
  for (const width of [360, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 })
    await expectNoHorizontalOverflow(page)
    expect.soft((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
    await page.screenshot({ path: `../artifacts/frontend/screenshots/variants/${surface}-${width}.png`, fullPage: true })
  }
}

test('real variants: admin allocation, size choice, two cart lines, COD, partial return and exact restock', async ({ page, browser }) => {
  test.setTimeout(90_000)
  await page.goto('/account')
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).last().click()
  await page.getByRole('link', { name: 'Mở trang quản trị' }).click()
  await page.getByLabel('Tìm tên hoặc mã sản phẩm').fill('P041')
  await page.getByRole('button', { name: 'Tìm', exact: true }).click()
  await expect(page.getByLabel('Số lượng mới P041', { exact: true })).toBeVisible()
  const initial = await (await page.request.get('/api/v1/admin/inventory?q=P041')).json()
  for (const [size, quantity] of [['M', 3], ['L', 2]] as const) {
    if (!initial.items.some((i: { product_id: string }) => i.product_id === `P041-${size}`)) {
      const parent = page.locator('article.admin-record').filter({ has: page.getByRole('button', { name: 'Lưu tồn kho P041', exact: true }) })
      if (await parent.locator('details').getAttribute('open') === null) await parent.getByText('Phân hàng sang kích cỡ', { exact: true }).click()
      await page.getByLabel('Kích cỡ mới P041', { exact: true }).selectOption(size)
      await page.getByLabel('Số lượng chuyển P041', { exact: true }).fill(String(quantity))
      await page.getByLabel('Lý do thay đổi').fill(`E2E demo size allocation ${size}`)
      await page.getByRole('button', { name: 'Tạo kích cỡ P041', exact: true }).click()
      await expect(page.getByLabel(`Số lượng mới P041-${size}`, { exact: true })).toBeVisible()
    }
  }
  const baseline = await (await page.request.get('/api/v1/admin/inventory?q=P041')).json()
  const buyer = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' })
  const shopper = await buyer.newPage()
  try {
    const registered = await buyer.request.post('/api/v1/auth/register', { headers: { 'X-Cortis-Intent': 'account' }, data: { email: buyerEmail, display_name: 'Variant buyer demo', password: `Buyer-${randomUUID()}-${randomUUID()}` } })
    expect(registered.status()).toBe(201)
    await shopper.goto('/products/P041')
    await expect(shopper.getByRole('button', { name: 'Thêm vào giỏ', exact: true })).toBeDisabled()
    await shopper.getByLabel('Kích cỡ', { exact: true }).selectOption('P041-M')
    await inspect(shopper, 'product')
    for (const sku of ['P041-M', 'P041-L']) {
      await shopper.getByLabel('Kích cỡ', { exact: true }).selectOption(sku)
      const pending = shopper.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/cart/items' && r.request().method() === 'POST')
      await shopper.getByRole('button', { name: 'Thêm vào giỏ', exact: true }).click()
      expect((await pending).status()).toBe(200)
      await expect(shopper.getByRole('button', { name: 'Thêm vào giỏ', exact: true })).toBeEnabled()
    }
    await shopper.goto('/cart')
    await expect(shopper.getByTestId('cart-item')).toHaveCount(2)
    await expect(shopper.locator('#quantity-P041-M')).toHaveValue('1')
    await expect(shopper.locator('#quantity-P041-L')).toHaveValue('1')
    await inspect(shopper, 'cart')
    await shopper.getByRole('link', { name: 'Tiếp tục đặt hàng', exact: true }).click()
    await shopper.getByRole('button', { name: 'Kiểm tra giỏ và lấy báo giá', exact: true }).click()
    await expect(shopper.getByRole('heading', { name: 'Kiểm tra đơn hàng', exact: true })).toBeVisible()
    await expect(shopper.locator('.shopping-summary li')).toHaveCount(2)
    await shopper.getByLabel('Người nhận', { exact: true }).fill('Khách demo')
    await shopper.getByLabel('Số điện thoại', { exact: true }).fill('0900000000')
    await shopper.getByLabel('Địa chỉ nhận hàng', { exact: true }).fill('Địa chỉ kiểm thử')
    await shopper.getByLabel('Tỉnh / thành phố', { exact: true }).fill('Thành phố demo')
    const placed = shopper.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/purchases' && r.request().method() === 'POST')
    await shopper.getByRole('button', { name: /^Đặt đơn COD/ }).click()
    const response = await placed
    expect(response.status()).toBe(201)
    const order = (await response.json()).order
    expect(order.items.map((i: { variant_id: string }) => i.variant_id).sort()).toEqual(['P041-L', 'P041-M'])
    for (const [status, version] of [['shipped', 0], ['delivered', 1]] as const) {
      expect((await page.request.post(`/api/v1/admin/purchases/${order.order_id}/status`, { headers: adminHeaders, data: { status, version, reason: 'E2E demo variant delivery' } })).status()).toBe(200)
    }
    await shopper.goto(`/orders/${order.order_id}`)
    await shopper.getByLabel(/Số lượng trả .*\(M\)/).fill('1')
    await shopper.getByLabel(/Số lượng trả .*\(L\)/).fill('1')
    await shopper.getByLabel('Lý do trả hàng', { exact: true }).fill('Kiểm thử trả hai kích cỡ')
    const created = shopper.waitForResponse(r => new URL(r.url()).pathname.endsWith('/returns') && r.request().method() === 'POST')
    await shopper.getByRole('button', { name: 'Gửi yêu cầu trả hàng', exact: true }).click()
    const returned = await created
    expect(returned.status()).toBe(201)
    const rma = (await returned.json()).return
    await expect(shopper.getByRole('heading', { name: rma.return_id, exact: true })).toBeVisible()
    await inspect(shopper, 'returns')
    await page.goto('/admin/returns')
    await page.getByLabel('Lý do xử lý', { exact: true }).fill('E2E demo inspect size and quarantine')
    await page.getByRole('button', { name: `Duyệt ${rma.return_id}`, exact: true }).click()
    const record = page.locator('article').filter({ has: page.getByRole('heading', { name: rma.return_id, exact: true }) })
    await record.getByLabel('Nhập lại kho P041-M', { exact: true }).fill('1')
    await record.getByLabel('Nhập lại kho P041-L', { exact: true }).fill('0')
    await page.getByRole('button', { name: `Xác nhận đã nhận hàng ${rma.return_id}`, exact: true }).click()
    await expect(record.getByText('Đã nhận và kiểm tra', { exact: true })).toBeVisible()
    await inspect(page, 'admin-receipt')
    const after = await (await page.request.get('/api/v1/admin/inventory?q=P041')).json()
    const quantity = (body: typeof after, sku: string) => body.items.find((i: { product_id: string }) => i.product_id === sku).quantity
    expect(quantity(after, 'P041-M')).toBe(quantity(baseline, 'P041-M'))
    expect(quantity(after, 'P041-L')).toBe(quantity(baseline, 'P041-L') - 1)
    expect(quantity(after, 'P041')).toBe(quantity(baseline, 'P041'))
    await page.getByRole('button', { name: `Đóng hồ sơ demo ${rma.return_id}`, exact: true }).click()
    await expect(record.getByText(/Đã ghi nhận số tiền đối soát demo/)).toBeVisible()
    await page.goto('/admin')
    await page.getByLabel('Tìm tên hoặc mã sản phẩm').fill('P041')
    await page.getByRole('button', { name: 'Tìm', exact: true }).click()
    await expect(page.getByLabel('Số lượng mới P041-M', { exact: true })).toBeVisible()
    await inspect(page, 'admin-inventory')
    await shopper.goto('/catalog?size=M&in_stock=true')
    await expect(shopper.getByTestId('product-card')).toHaveCount(1)
    await expect(shopper.getByLabel('Kích cỡ', { exact: true })).toHaveValue('M')
  } finally {
    // Restore demo stock exactly; keep audited variant definitions and historical orders.
    for (const item of baseline.items) {
      const current = await (await page.request.get('/api/v1/admin/inventory?q=P041')).json()
      expect((await page.request.post(`/api/v1/admin/inventory/${item.product_id}`, { headers: adminHeaders, data: { quantity: item.quantity, revision: current.revision, reason: 'E2E variant stock restoration' } })).status()).toBe(200)
    }
    await buyer.close()
  }
})
