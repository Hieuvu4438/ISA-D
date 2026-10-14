import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { expectNoHorizontalOverflow } from './helpers'

test('real account API: register, reload, profile, change password, logout and login', async ({ page }) => {
  const email = `browser-${Date.now()}@example.test`
  const password = 'Browser account passphrase 2026'
  await page.goto('/account')
  await page.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click()
  await page.getByLabel('Tên hiển thị').fill('Nguyễn An')
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Tạo tài khoản', exact: true }).last().click()
  await expect(page.getByRole('button', { name: 'Đăng xuất' })).toBeVisible()
  expect((await page.context().cookies()).find(cookie => cookie.name === 'cortis_session')?.httpOnly).toBe(true)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Nguyễn An', exact: true })).toBeVisible()
  await page.getByLabel('Tên hiển thị').fill('Nguyễn An Cortis')
  await page.getByRole('button', { name: 'Lưu thông tin' }).click()
  await expect(page.getByRole('heading', { name: 'Nguyễn An Cortis', exact: true })).toBeVisible()
  await page.getByLabel('Mật khẩu hiện tại').fill(password)
  await page.getByLabel('Mật khẩu mới', { exact: true }).fill(password + ' changed')
  await page.getByLabel('Xác nhận mật khẩu mới').fill(password + ' changed')
  await page.getByRole('button', { name: 'Đổi mật khẩu', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('Đã đổi mật khẩu')
  const forbidden = await page.request.get('/api/v1/admin/overview')
  expect(forbidden.status()).toBe(403)
  expect((await page.request.get('/api/v1/orders/O001')).status()).toBe(404)
  await page.getByRole('button', { name: 'Đăng xuất' }).click()
  await expect(page.getByRole('button', { name: 'Đăng nhập', exact: true }).last()).toBeVisible()
  expect((await page.request.get('/api/v1/auth/me')).status()).toBe(401)
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).last().click()
  await expect(page.getByRole('alert')).toContainText('Email hoặc mật khẩu chưa đúng')
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password + ' changed')
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).last().click()
  await expect(page.getByRole('button', { name: 'Đăng xuất' })).toBeVisible()
})

test('real account API: denied orders recover through login; mobile/desktop account accessibility', async ({ page }) => {
  await page.goto('/orders/O001')
  await expect(page.getByRole('alert')).toContainText('Vui lòng đăng nhập')
  await page.getByRole('link', { name: 'Đăng nhập hoặc kiểm tra tài khoản' }).click()
  await expect(page.getByRole('heading', { name: 'Tài khoản của bạn.' })).toBeVisible()
  for (const width of [360, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 })
    await expectNoHorizontalOverflow(page)
    await expect(page.getByLabel('Email', { exact: true })).toBeVisible()
    const result = await new AxeBuilder({ page }).analyze()
    expect(result.violations).toEqual([])
    await page.screenshot({ path: `../artifacts/frontend/screenshots/accounts/account-${width}.png`, fullPage: true })
  }
})
