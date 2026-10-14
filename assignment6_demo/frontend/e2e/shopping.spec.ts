import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { expectNoHorizontalOverflow } from './helpers'

async function signUp(page: import('@playwright/test').Page) {
  await page.goto('/account')
  await page.getByRole('button', { name: 'Tạo tài khoản', exact: true }).click()
  await page.getByLabel('Tên hiển thị').fill('Shopping browser')
  await page.getByLabel('Email', { exact: true }).fill(`shopping-${Date.now()}@example.test`)
  await page.getByLabel('Mật khẩu', { exact: true }).fill('Browser shopping passphrase 2026')
  await page.getByRole('button', { name: 'Tạo tài khoản', exact: true }).last().click()
  await expect(page.getByRole('button', { name: 'Đăng xuất' })).toBeVisible()
}

test('real shopping API: product save, wishlist add, quantity update, reload and removal', async ({ page }) => {
  await signUp(page)
  await page.goto('/products/P001')
  await page.getByRole('button', { name: 'Lưu yêu thích' }).click()
  await expect(page.getByRole('button', { name: 'Bỏ lưu', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await page.goto('/wishlist')
  await expect(page.getByTestId('wishlist-item')).toHaveCount(1)
  await page.getByRole('button', { name: 'Thêm vào giỏ', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('Đã thêm một sản phẩm')
  await page.goto('/cart')
  await expect(page.getByTestId('cart-item')).toHaveCount(1)
  await page.getByLabel('Số lượng', { exact: true }).fill('3')
  await page.getByRole('button', { name: 'Cập nhật', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('Đã cập nhật số lượng')
  const response = await page.request.get('/api/v1/cart')
  const cart = (await response.json()).cart
  expect(cart.items[0].quantity).toBe(3)
  expect(cart.subtotal_vnd).toBe(cart.items[0].unit_price_vnd * 3)
  await page.reload()
  await expect(page.getByLabel('Số lượng', { exact: true })).toHaveValue('3')
  await page.getByRole('button', { name: /^Xóa/ }).click()
  await expect(page.getByRole('heading', { name: 'Giỏ hàng đang trống' })).toBeVisible()
  await page.goto('/wishlist')
  await expect(page.getByTestId('wishlist-item')).toHaveCount(1)
  await page.getByRole('button', { name: /^Bỏ lưu/ }).click()
  await expect(page.getByRole('heading', { name: 'Bạn chưa lưu món đồ nào' })).toBeVisible()
})

test('real shopping API: anonymous recovery and out of stock cannot add', async ({ page }) => {
  await page.goto('/cart')
  await expect(page.getByRole('link', { name: 'Đăng nhập để xem giỏ hàng' })).toBeVisible()
  await page.goto('/products/P001')
  await page.getByRole('button', { name: 'Thêm vào giỏ', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Đăng nhập để lưu hoặc thêm sản phẩm' })).toBeVisible()
  const rows = await page.request.get('/api/v1/products?limit=100')
  const product = (await rows.json()).products.find((row: { in_stock: boolean }) => !row.in_stock)
  await page.goto(`/products/${product.product_id}`)
  await expect(page.getByRole('button', { name: 'Tạm hết hàng', exact: true })).toBeDisabled()
})

test('real shopping API: stale cart version reloads other-tab state, no overwrite', async ({ page }) => {
  await signUp(page)
  await page.request.post('/api/v1/cart/items', { headers: { 'X-Cortis-Intent': 'commerce' }, data: { product_id: 'P001', quantity: 1, version: 0 } })
  await page.goto('/cart')
  await expect(page.getByLabel('Số lượng', { exact: true })).toHaveValue('1')
  const change = await page.request.post('/api/v1/cart/items', { headers: { 'X-Cortis-Intent': 'commerce' }, data: { product_id: 'P001', quantity: 2, version: 1 } })
  expect(change.status()).toBe(200)
  await page.getByLabel('Số lượng', { exact: true }).fill('3')
  await page.getByRole('button', { name: 'Cập nhật', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('Giỏ hàng đã thay đổi')
  await expect(page.getByLabel('Số lượng', { exact: true })).toHaveValue('2')
  expect((await (await page.request.get('/api/v1/cart')).json()).cart.items[0].quantity).toBe(2)
})

test('real shopping API: late wishlist read does not overwrite save and logout removes private state', async ({ page }) => {
  await signUp(page)
  let resolveRead!: () => void
  const initialRead = new Promise<void>(resolve => { resolveRead = resolve })
  await page.route('**/api/v1/wishlist', async route => {
    const response = await route.fetch()
    resolveRead()
    await new Promise(resolve => setTimeout(resolve, 700))
    await route.fulfill({ response })
  })
  await page.goto('/products/P001')
  await initialRead
  await page.getByRole('button', { name: 'Lưu yêu thích' }).click()
  await expect(page.getByRole('button', { name: 'Bỏ lưu', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await page.waitForTimeout(800)
  await expect(page.getByRole('button', { name: 'Bỏ lưu', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await page.unroute('**/api/v1/wishlist')
  await page.goto('/wishlist')
  await expect(page.getByTestId('wishlist-item')).toHaveCount(1)
  const logout = await page.request.post('/api/v1/auth/logout', { headers: { 'X-Cortis-Intent': 'account' }, data: {} })
  expect(logout.status()).toBe(200)
  await page.getByRole('button', { name: /^Bỏ lưu/ }).click()
  await expect(page.getByTestId('wishlist-item')).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'Đăng nhập để xem món đã lưu' })).toBeVisible()
})

test('real shopping pages: responsive screenshots and accessibility', async ({ page }) => {
  await signUp(page)
  await page.request.post('/api/v1/cart/items', { headers: { 'X-Cortis-Intent': 'commerce' }, data: { product_id: 'P001', quantity: 1, version: 0 } })
  await page.request.post('/api/v1/wishlist/items', { headers: { 'X-Cortis-Intent': 'commerce' }, data: { product_id: 'P001', saved: true } })
  for (const width of [360, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 })
    for (const route of ['/cart', '/wishlist', '/products/P001']) {
      await page.goto(route)
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
      await expect(page.getByText(/Đang tải/)).toHaveCount(0)
      await expectNoHorizontalOverflow(page)
      const axe = await new AxeBuilder({ page }).analyze()
      expect(axe.violations).toEqual([])
      await page.screenshot({ path: `../artifacts/frontend/screenshots/shopping/${route.split('/')[1]}-${width}.png`, fullPage: true })
    }
  }
})
