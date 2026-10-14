import { test, expect } from '@playwright/test'

test('false stock filter has no active badge and clear filters preserves keyword/sort', async ({ page }) => {
  await page.goto('/catalog?q=ao+thun&in_stock=false&sort=price_desc')
  await expect(page.getByTestId('product-card').first()).toBeVisible()
  await expect(page.getByLabel('Chỉ còn hàng')).not.toBeChecked()
  await expect(page.getByLabel('Bộ lọc đang áp dụng')).toHaveCount(0)
  await page.getByRole('button', { name: 'Xóa lọc', exact: true }).click()
  await expect(page).not.toHaveURL(/in_stock/)
  expect(new URL(page.url()).searchParams.get('q')).toBe('ao thun')
  expect(new URL(page.url()).searchParams.get('sort')).toBe('price_desc')
})

test('inverted price stays editable without a request; correction uses inclusive boundaries', async ({ page }) => {
  await page.goto('/catalog?category=t_shirt')
  await expect(page.getByTestId('product-card').first()).toBeVisible()
  const requests: string[] = []
  page.on('request', request => { if (new URL(request.url()).pathname === '/api/v1/catalog') requests.push(request.url()) })
  await page.getByLabel('Thấp nhất', { exact: true }).fill('2000000')
  await page.getByLabel('Cao nhất', { exact: true }).fill('1000000')
  await page.getByRole('button', { name: 'Áp dụng khoảng giá' }).click()
  await expect(page.getByRole('alert')).toHaveText('Giá thấp nhất phải nhỏ hơn hoặc bằng giá cao nhất.')
  await expect(page.getByLabel('Thấp nhất', { exact: true })).toHaveValue('2000000')
  expect(requests).toEqual([])
  expect(new URL(page.url()).searchParams.has('min_price')).toBe(false)
  await page.getByLabel('Thấp nhất', { exact: true }).fill('0')
  await expect(page.getByRole('alert')).toHaveCount(0)
  await page.getByRole('button', { name: 'Áp dụng khoảng giá' }).click()
  await expect(page).toHaveURL(/min_price=0/)
  await expect(page.getByTestId('product-card').first()).toBeVisible()
  const result = await page.request.get('/api/v1/catalog?category=t_shirt&min_price=0&max_price=1000000')
  const body = await result.json()
  await expect(page.getByTestId('product-card')).toHaveCount(body.products.length)
  expect(body.products.every((p: { price_vnd: number }) => p.price_vnd >= 0 && p.price_vnd <= 1000000)).toBe(true)
})

test('empty filters can be removed without losing the query, sort or page size', async ({ page }) => {
  await page.goto('/catalog?q=ao+thun&max_price=0&sort=price_asc&limit=5&offset=20')
  await expect(page.getByRole('heading', { name: 'Không có sản phẩm đáp ứng bộ lọc' })).toBeVisible()
  await page.getByRole('button', { name: 'Bỏ bộ lọc, giữ từ khóa' }).click()
  const params = new URL(page.url()).searchParams
  expect(Object.fromEntries(params)).toEqual({ q: 'ao thun', sort: 'price_asc', limit: '5' })
  await expect(page.getByTestId('product-card')).toHaveCount(5)
})

test('valid native numeric notation is serialized as API integer prices', async ({ page }) => {
  await page.goto('/catalog')
  await expect(page.getByTestId('product-card').first()).toBeVisible()
  await page.getByLabel('Thấp nhất', { exact: true }).fill('1e3')
  await page.getByLabel('Cao nhất', { exact: true }).fill('2000.0')
  await page.getByRole('button', { name: 'Áp dụng khoảng giá' }).click()
  await expect(page.getByRole('heading', { name: 'Không có sản phẩm đáp ứng bộ lọc' })).toBeVisible()
  const params = new URL(page.url()).searchParams
  expect(params.get('min_price')).toBe('1000')
  expect(params.get('max_price')).toBe('2000')
  await expect(page.getByRole('alert')).toHaveCount(0)
})

test('missing keyword can be removed without losing filters', async ({ page }) => {
  await page.goto('/catalog?q=P999&category=t_shirt&sort=price_desc&limit=5')
  await expect(page.getByRole('heading', { name: 'Chưa tìm thấy sản phẩm này' })).toBeVisible()
  await page.getByRole('button', { name: 'Xóa từ khóa, giữ bộ lọc' }).click()
  const params = new URL(page.url()).searchParams
  expect(Object.fromEntries(params)).toEqual({ category: 't_shirt', sort: 'price_desc', limit: '5' })
  await expect(page.getByRole('combobox', { name: 'Tên sản phẩm hoặc mã sản phẩm' })).toHaveValue('')
  await expect(page.getByTestId('product-card')).toHaveCount(5)
})

test('out of range page recovers in one action without contradictory page counts', async ({ page }) => {
  await page.goto('/catalog?category=t_shirt&sort=price_desc&limit=5&offset=100000')
  await expect(page.getByRole('heading', { name: 'Trang này không còn sản phẩm' })).toBeVisible()
  await expect(page.getByRole('navigation', { name: 'Phân trang bộ sưu tập' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Về trang đầu' }).click()
  await expect(page.getByTestId('product-card')).toHaveCount(5)
  expect(new URL(page.url()).searchParams.get('category')).toBe('t_shirt')
  expect(new URL(page.url()).searchParams.get('sort')).toBe('price_desc')
  await expect(page.getByRole('navigation', { name: 'Phân trang bộ sưu tập' })).toContainText('Trang 1 / 3')
})

test('invalid unknown/duplicate URL parameters have a working reset', async ({ page }) => {
  for (const suffix of ['unknown=1', 'q=a&q=b', 'in_stock=invalid']) {
    await page.goto(`/catalog?${suffix}`)
    await expect(page.getByRole('alert')).toBeVisible()
    await page.getByRole('button', { name: 'Đặt lại tìm kiếm' }).click()
    await expect(page.getByTestId('product-card')).toHaveCount(24)
    expect(new URL(page.url()).search).toBe('')
  }
})

test('suggestions close on escape and blur and only reference a mounted listbox', async ({ page }) => {
  await page.goto('/catalog')
  const input = page.getByRole('combobox', { name: 'Tên sản phẩm hoặc mã sản phẩm' })
  await input.fill('P00')
  await expect(input).toHaveAttribute('aria-expanded', 'true')
  await expect(page.locator(`#${await input.getAttribute('aria-controls')}`)).toHaveRole('listbox')
  await input.press('ArrowDown')
  await expect(input).toHaveAttribute('aria-activedescendant', 'suggestion-0')
  await input.press('Escape')
  await expect(input).toHaveAttribute('aria-expanded', 'false')
  await expect(input).not.toHaveAttribute('aria-controls')
  await expect(input).not.toHaveAttribute('aria-activedescendant')
  await input.press('ArrowDown')
  await expect(input).toHaveAttribute('aria-expanded', 'true')
  await input.press('Tab')
  await expect(page.getByRole('listbox')).toHaveCount(0)
  await expect(input).toHaveValue('P00')
})
