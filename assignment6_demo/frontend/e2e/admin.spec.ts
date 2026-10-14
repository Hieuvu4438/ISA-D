import { test, expect, type Page, type BrowserContext } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { randomUUID } from 'node:crypto'
import AxeBuilder from '@axe-core/playwright'
import { expectNoHorizontalOverflow } from './helpers'

const email = `admin-e2e-${Date.now()}@example.test`
const password = `Fixture-${randomUUID()}-${randomUUID()}`
const python = fileURLToPath(new URL('../../backend/.venv/Scripts/python.exe', import.meta.url))
const fixture = fileURLToPath(new URL('../../scripts/admin_browser_fixture.py', import.meta.url))
const adminHeaders = { 'X-Cortis-Intent': 'admin' }
const buyerFixtures: string[] = []

test.beforeAll(() => {
  execFileSync(python, [fixture, 'provision', '--email', email], { env: { ...process.env, CORTIS_E2E_ADMIN_PASSWORD: password }, stdio: 'pipe' })
})
test.afterAll(() => {
  for (const buyerEmail of buyerFixtures) execFileSync(python, [fixture, 'retire', '--email', buyerEmail], { stdio: 'pipe' })
  execFileSync(python, [fixture, 'retire', '--email', email], { stdio: 'pipe' })
})

async function login(page: Page) {
  await page.goto('/account')
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).last().click()
  await page.getByRole('link', { name: 'Mở trang quản trị' }).click()
  await expect(page.getByRole('heading', { name: 'Quản trị Cortis.' })).toBeVisible()
  await expect(page.getByText('Đang tải dữ liệu quản trị…')).toHaveCount(0)
}

async function createBuyer(context: BrowserContext) {
  const buyerEmail = `admin-e2e-buyer-${randomUUID()}@example.test`
  const buyerPassword = `Buyer-${randomUUID()}-${randomUUID()}`
  buyerFixtures.push(buyerEmail)
  const response = await context.request.post('http://127.0.0.1:5173/api/v1/auth/register', { headers: { 'X-Cortis-Intent': 'account' }, data: { email: buyerEmail, display_name: 'Browser buyer demo', password: buyerPassword } })
  expect(response.status()).toBe(201)
  return { email: buyerEmail, password: buyerPassword, user: (await response.json()).user }
}

test('real admin inventory: adjust, audit and restore; version conflict never overwrites', async ({ page }) => {
  const auditReason = `Browser stock audit ${randomUUID()}`
  await login(page)
  await page.getByLabel('Tìm tên hoặc mã sản phẩm').fill('P001')
  await page.getByRole('button', { name: 'Tìm', exact: true }).click()
  const input = page.getByLabel('Số lượng mới P001', { exact: true })
  await expect(input).toBeVisible()
  const before = Number(await input.inputValue())
  try {
    await page.getByLabel('Lý do thay đổi').fill(auditReason)
    await input.fill('0')
    await page.getByRole('button', { name: 'Lưu tồn kho P001', exact: true }).click()
    await expect(page.getByRole('status').filter({ hasText: 'Đã xử lý yêu cầu' })).toBeVisible()
    expect((await (await page.request.get('/api/v1/products/P001')).json()).product.in_stock).toBe(false)
    await expect(input).toHaveValue('0')
    const snapshot = await (await page.request.get('/api/v1/admin/inventory?q=P001')).json()
    await page.request.post('/api/v1/admin/inventory/P001', { headers: adminHeaders, data: { quantity: 1, revision: snapshot.revision, reason: 'Other tab stock change' } })
    await input.fill('2')
    await page.getByRole('button', { name: 'Lưu tồn kho P001', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('Tồn kho đã thay đổi')
    expect((await (await page.request.get('/api/v1/products/P001')).json()).product.stock_quantity).toBe(1)
    await page.getByRole('button', { name: 'Lịch sử thao tác', exact: true }).click()
    await expect(page.getByText(`Lý do: ${auditReason}`, { exact: true })).toBeVisible()
  } finally {
    const current = await (await page.request.get('/api/v1/admin/inventory?q=P001')).json()
    const restored = await page.request.post('/api/v1/admin/inventory/P001', { headers: adminHeaders, data: { quantity: before, revision: current.revision, reason: 'E2E stock restoration' } })
    expect(restored.status()).toBe(200)
  }
})

test('real admin role UI: promote user, revoke previous session, deny normal user access', async ({ page, browser }) => {
  const buyer = await browser.newContext()
  const target = await createBuyer(buyer)
  expect((await buyer.request.get('http://127.0.0.1:5173/api/v1/admin/users')).status()).toBe(403)
  await login(page)
  try {
    await page.getByRole('button', { name: 'Tài khoản', exact: true }).click()
    await page.getByLabel('Tìm email tài khoản').fill(target.email)
    await page.getByRole('button', { name: 'Tìm', exact: true }).click()
    await page.getByLabel(`Quyền của ${target.email}`, { exact: true }).selectOption('admin')
    await page.getByLabel('Lý do thay đổi').fill('Approved E2E operator promotion')
    await page.getByRole('button', { name: `Lưu quyền ${target.email}`, exact: true }).click()
    await expect(page.getByRole('status').filter({ hasText: 'Đã xử lý yêu cầu' })).toBeVisible()
    expect((await buyer.request.get('http://127.0.0.1:5173/api/v1/auth/me')).status()).toBe(401)
    const response = await buyer.request.post('http://127.0.0.1:5173/api/v1/auth/login', { headers: { 'X-Cortis-Intent': 'account' }, data: { email: target.email, password: target.password } })
    expect(response.status()).toBe(200)
    expect((await buyer.request.get('http://127.0.0.1:5173/api/v1/admin/users')).status()).toBe(200)
  } finally {
    const rows = await (await page.request.get(`/api/v1/admin/users?q=${encodeURIComponent(target.email)}`)).json()
    const targetRow = rows.users[0]
    await page.request.post(`/api/v1/admin/users/${target.user.user_id}/role`, { headers: adminHeaders, data: { role: 'user', version: targetRow.version, reason: 'Retire E2E promoted role' } })
    await buyer.close()
  }
})

test('real admin fulfillment: owner order -> shipped -> delivered with private detail access', async ({ page, browser }) => {
  const buyer = await browser.newContext()
  await createBuyer(buyer)
  const commerce = { 'X-Cortis-Intent': 'commerce' }
  await buyer.request.post('http://127.0.0.1:5173/api/v1/cart/items', { headers: commerce, data: { product_id: 'P001', quantity: 1, version: 0 } })
  const q = (await (await buyer.request.post('http://127.0.0.1:5173/api/v1/checkout/quote', { headers: commerce, data: {} })).json()).quote
  const placed = await buyer.request.post('http://127.0.0.1:5173/api/v1/purchases', { headers: commerce, data: { quote_id: q.quote_id, idempotency_key: randomUUID(), shipping_address: { recipient: 'Admin fulfillment demo', phone: '0900000000', address_line: 'Test demo address', city: 'Demo city' } } })
  expect(placed.status()).toBe(201)
  const id = (await placed.json()).order.order_id
  await login(page)
  const stock = (await (await page.request.get('/api/v1/products/P001')).json()).product.stock_quantity
  try {
    await page.getByRole('button', { name: 'Đơn hàng', exact: true }).click()
    await page.getByRole('button', { name: `Xem thông tin nhận hàng ${id}`, exact: true }).click()
    await expect(page.getByRole('region', { name: 'Chi tiết nhận hàng' })).toContainText('Admin fulfillment demo')
    await page.getByRole('button', { name: 'Đóng thông tin nhận hàng' }).click()
    await page.getByLabel('Lý do thay đổi').fill('E2E demo dispatch')
    await page.getByRole('button', { name: `Chuyển sang giao hàng ${id}`, exact: true }).click()
    await expect(page.getByRole('button', { name: `Xác nhận đã giao ${id}`, exact: true })).toBeVisible()
    expect((await buyer.request.post(`http://127.0.0.1:5173/api/v1/purchases/${id}/cancel`, { headers: commerce, data: { version: 1 } })).status()).toBe(409)
    await page.getByRole('button', { name: `Xác nhận đã giao ${id}`, exact: true }).click()
    await expect(page.getByRole('button', { name: `Xác nhận đã giao ${id}`, exact: true })).toHaveCount(0)
    const owner = await (await buyer.request.get(`http://127.0.0.1:5173/api/v1/purchases/${id}`)).json()
    expect(owner.order.status).toBe('delivered')
    expect(owner.order.payment_status).toBe('unpaid')
  } finally {
    const current = await (await page.request.get('/api/v1/admin/inventory?q=P001')).json()
    await page.request.post('/api/v1/admin/inventory/P001', { headers: adminHeaders, data: { quantity: stock + 1, revision: current.revision, reason: 'Replenish demo fixture inventory' } })
    await buyer.close()
  }
})

test('admin direct URL denial and responsive accessibility on inventory', async ({ page }) => {
  await page.goto('/admin')
  await expect(page.getByRole('link', { name: 'Đăng nhập bằng tài khoản quản trị' })).toBeVisible()
  await login(page)
  await page.getByLabel('Tìm tên hoặc mã sản phẩm').fill('P001')
  await page.getByRole('button', { name: 'Tìm', exact: true }).click()
  await expect(page.getByLabel('Số lượng mới P001', { exact: true })).toBeVisible()
  for (const width of [360, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 })
    await expectNoHorizontalOverflow(page)
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
    await page.screenshot({ path: `../artifacts/frontend/screenshots/admin/inventory-${width}.png`, fullPage: true })
  }
})
