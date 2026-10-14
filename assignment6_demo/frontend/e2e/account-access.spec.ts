import { test, expect, type Page } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { randomUUID } from 'node:crypto'
import AxeBuilder from '@axe-core/playwright'
import { expectNoHorizontalOverflow } from './helpers'

const origin = 'http://127.0.0.1:5173'
const email = `admin-e2e-access-${randomUUID()}@example.test`
const password = `Fixture-${randomUUID()}-${randomUUID()}`
const python = fileURLToPath(new URL('../../backend/.venv/Scripts/python.exe', import.meta.url))
const fixture = fileURLToPath(new URL('../../scripts/admin_browser_fixture.py', import.meta.url))
const ah = { 'X-Cortis-Intent': 'admin' }, ch = { 'X-Cortis-Intent': 'commerce' }, accountHeaders = { 'X-Cortis-Intent': 'account' }
const buyers: string[] = []

test.beforeAll(() => { execFileSync(python, [fixture, 'provision', '--email', email], { env: { ...process.env, CORTIS_E2E_ADMIN_PASSWORD: password }, stdio: 'pipe' }) })
test.afterAll(() => {
  for (const buyer of buyers) execFileSync(python, [fixture, 'retire', '--email', buyer], { stdio: 'pipe' })
  execFileSync(python, [fixture, 'retire', '--email', email], { stdio: 'pipe' })
})

async function loginAdmin(page: Page) {
  expect((await page.request.post(`${origin}/api/v1/auth/login`, { headers: accountHeaders, data: { email, password } })).status()).toBe(200)
  await page.goto('/admin')
  await page.getByRole('button', { name: 'Tài khoản', exact: true }).click()
}

async function findUser(page: Page, target: string) {
  await page.getByLabel('Tìm email tài khoản').fill(target)
  await page.getByRole('button', { name: 'Tìm', exact: true }).click()
  const card = page.locator('article.admin-record').filter({ has: page.getByText(target, { exact: true }) })
  await expect(card).toBeVisible()
  return card
}

test('real access controls: lock/unlock, session revocation, preserved cart and fresh login', async ({ page, browser }) => {
  await loginAdmin(page)
  const own = await findUser(page, email)
  await expect(own.getByRole('button', { name: `Khóa tài khoản ${email}`, exact: true })).toBeDisabled()
  const buyer = await browser.newContext(), second = await browser.newContext()
  const buyerEmail = `admin-e2e-access-buyer-${randomUUID()}@example.test`, buyerPassword = `Buyer-${randomUUID()}-${randomUUID()}`
  buyers.push(buyerEmail)
  const buyerPage = await buyer.newPage()
  let userId = ''
  try {
    const registered = await buyer.request.post(`${origin}/api/v1/auth/register`, { headers: accountHeaders, data: { email: buyerEmail, password: buyerPassword, display_name: 'Access test buyer' } })
    expect(registered.status()).toBe(201)
    userId = (await registered.json()).user.user_id
    expect((await second.request.post(`${origin}/api/v1/auth/login`, { headers: accountHeaders, data: { email: buyerEmail, password: buyerPassword } })).status()).toBe(200)
    expect((await buyer.request.post(`${origin}/api/v1/cart/items`, { headers: ch, data: { product_id: 'P001', quantity: 1, version: 0 } })).status()).toBe(200)
    const before = (await (await buyer.request.get(`${origin}/api/v1/cart`)).json()).cart
    const card = await findUser(page, buyerEmail)
    const lockReason = `Manual access review ${randomUUID()}`, unlockReason = `Review complete ${randomUUID()}`
    await page.getByLabel('Lý do thay đổi').fill(lockReason)
    await card.getByRole('button', { name: `Khóa tài khoản ${buyerEmail}`, exact: true }).click()
    await expect(card.getByText('Đã khóa', { exact: true })).toBeVisible()
    await page.getByLabel('Trạng thái tài khoản').selectOption('locked')
    await expect(card).toBeVisible()
    for (const context of [buyer, second]) expect((await context.request.get(`${origin}/api/v1/auth/me`)).status()).toBe(401)
    expect((await buyer.request.post(`${origin}/api/v1/cart/items`, { headers: ch, data: { product_id: 'P001', quantity: 2, version: before.version } })).status()).toBe(401)
    await buyerPage.goto(`${origin}/account`)
    await buyerPage.getByLabel('Email', { exact: true }).fill(buyerEmail)
    await buyerPage.getByLabel('Mật khẩu', { exact: true }).fill(buyerPassword)
    await buyerPage.getByRole('button', { name: 'Đăng nhập', exact: true }).last().click()
    await expect(buyerPage.getByRole('alert')).toContainText('Email hoặc mật khẩu chưa đúng')
    // One bounded capture batch for the new controls, before any further UI changes.
    for (const width of [360, 768, 1440]) {
      await page.setViewportSize({ width, height: 1000 })
      await expectNoHorizontalOverflow(page)
      const recordWidth = await card.locator(':scope > div').first().boundingBox()
      expect.soft(recordWidth!.width).toBeGreaterThanOrEqual(260)
      expect.soft((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
      await page.screenshot({ path: `../artifacts/frontend/screenshots/account-access/locked-${width}.png`, fullPage: true })
    }
    await page.getByLabel('Lý do thay đổi').fill(unlockReason)
    await card.getByRole('button', { name: `Mở khóa ${buyerEmail}`, exact: true }).click()
    await expect(page.getByText('Chưa có dữ liệu phù hợp', { exact: true })).toBeVisible()
    expect((await second.request.get(`${origin}/api/v1/auth/me`)).status()).toBe(401)
    await buyerPage.getByRole('button', { name: 'Đăng nhập', exact: true }).last().click()
    await expect(buyerPage.getByRole('button', { name: 'Đăng xuất', exact: true })).toBeVisible()
    expect((await (await buyer.request.get(`${origin}/api/v1/cart`)).json()).cart).toEqual(before)
    await page.getByRole('button', { name: 'Lịch sử thao tác', exact: true }).click()
    await expect(page.getByText(`Lý do: ${lockReason}`, { exact: true })).toBeVisible()
    await expect(page.getByText(`Lý do: ${unlockReason}`, { exact: true })).toBeVisible()
  } finally {
    if (userId) {
      const listing = await (await page.request.get(`/api/v1/admin/users?q=${encodeURIComponent(buyerEmail)}`)).json()
      const user = listing.users?.[0]
      if (user?.access_state === 'locked') expect((await page.request.post(`/api/v1/admin/users/${userId}/access`, { headers: ah, data: { access_state: 'active', version: user.version, reason: 'Retire access test fixture' } })).status()).toBe(200)
    }
    await buyer.close(); await second.close()
  }
})

test('real stale access update keeps reason and requires reload before further edits', async ({ page, browser }) => {
  await loginAdmin(page)
  const buyer = await browser.newContext()
  const buyerEmail = `admin-e2e-access-stale-${randomUUID()}@example.test`
  buyers.push(buyerEmail)
  const registered = await buyer.request.post(`${origin}/api/v1/auth/register`, { headers: accountHeaders, data: { email: buyerEmail, password: `Buyer-${randomUUID()}-${randomUUID()}`, display_name: 'Stale access buyer' } })
  expect(registered.status()).toBe(201)
  const id = (await registered.json()).user.user_id
  try {
    const card = await findUser(page, buyerEmail)
    const reason = `Stale page ${randomUUID()}`
    await page.getByLabel('Lý do thay đổi').fill(reason)
    expect((await page.request.post(`/api/v1/admin/users/${id}/access`, { headers: ah, data: { access_state: 'locked', version: 0, reason: 'Concurrent operator access change' } })).status()).toBe(200)
    await card.getByRole('button', { name: `Khóa tài khoản ${buyerEmail}`, exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('Tài khoản đã thay đổi')
    await expect(page.getByLabel('Lý do thay đổi')).toHaveValue(reason)
    await page.getByRole('button', { name: 'Thử lại', exact: true }).click()
    await expect(card.getByRole('button', { name: `Mở khóa ${buyerEmail}`, exact: true })).toBeVisible()
    await card.getByRole('button', { name: `Mở khóa ${buyerEmail}`, exact: true }).click()
    await expect(card.getByText('Đang hoạt động', { exact: true })).toBeVisible()
  } finally {
    const listing = await (await page.request.get(`/api/v1/admin/users?q=${encodeURIComponent(buyerEmail)}`)).json()
    const user = listing.users?.[0]
    if (user?.access_state === 'locked') await page.request.post(`/api/v1/admin/users/${id}/access`, { headers: ah, data: { access_state: 'active', version: user.version, reason: 'Retire stale access fixture' } })
    await buyer.close()
  }
})
