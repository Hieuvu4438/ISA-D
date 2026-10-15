import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';

test('public demo admin: HTTPS login, secure cookie and catalog management', async ({ page }) => {
  test.skip(!process.env.PUBLIC_DEMO_URL, 'Explicit public deployment verification only.');
  const saved = JSON.parse(readFileSync(new URL('../../runtime/public-demo/app/runtime/demo/access.json', import.meta.url), 'utf8'));
  const account = saved.accounts.find((entry: { role: string }) => entry.role === 'admin');
  await page.goto('/account');
  await page.getByLabel('Email', { exact: true }).fill(account.email);
  await page.getByLabel('Mật khẩu', { exact: true }).fill(account.password);
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).last().click();
  await page.getByRole('link', { name: 'Mở trang quản trị' }).click();
  await expect(page.getByRole('heading', { name: 'Quản trị Cortis.' })).toBeVisible();
  const cookie = (await page.context().cookies()).find(entry => entry.name === 'cortis_session');
  expect(cookie?.secure).toBe(true);
  expect(cookie?.httpOnly).toBe(true);
  expect(cookie?.sameSite).toBe('Lax');
  expect((await page.request.get('/api/v1/admin/inventory')).status()).toBe(200);
  await page.getByRole('button', { name: 'Sản phẩm', exact: true }).click();
  await expect(page.getByText('Đang tải dữ liệu quản trị…')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Mở mã sản phẩm' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Quản trị Cortis.' })).toBeVisible();
});
