import { test, expect } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { readFileSync } from 'node:fs'
import { randomUUID } from 'node:crypto'
import AxeBuilder from '@axe-core/playwright'
import { expectNoHorizontalOverflow } from './helpers'

const email = `admin-e2e-author-${Date.now()}@example.test`
const password = `Fixture-${randomUUID()}-${randomUUID()}`
const python = fileURLToPath(new URL('../../backend/.venv/Scripts/python.exe', import.meta.url))
const fixture = fileURLToPath(new URL('../../scripts/admin_browser_fixture.py', import.meta.url))
const photo = fileURLToPath(new URL('../../data/authoring/P181.jpg', import.meta.url))
const source = JSON.parse(readFileSync(new URL('../../data/authoring/P181-source.json', import.meta.url), 'utf8'))
const headers = { 'X-Cortis-Intent': 'admin' }

test.beforeAll(() => execFileSync(python, [fixture, 'provision', '--email', email], { env: { ...process.env, CORTIS_E2E_ADMIN_PASSWORD: password }, stdio: 'pipe' }))
test.afterAll(() => execFileSync(python, [fixture, 'retire', '--email', email], { stdio: 'pipe' }))

test('real admin authoring: create, photo provenance, CPU preflight, stale edit, discard and public isolation', async ({ page }) => {
  test.setTimeout(60_000)
  await page.goto('/account')
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).last().click()
  await page.getByRole('link', { name: 'Mở trang quản trị' }).click()
  await page.getByRole('button', { name: 'Sản phẩm', exact: true }).click()
  const endpoint = '/api/v1/admin/products/P181/draft'
  const initial = (await (await page.request.get(endpoint)).json()).draft
  expect(initial.has_draft).toBe(false)
  const before = (await (await page.request.get('/api/v1/meta')).json()).index
  try {
    await page.getByLabel('Mã sản phẩm cần tạo hoặc mở', { exact: true }).fill('P181')
    await page.getByRole('button', { name: 'Mở mã sản phẩm', exact: true }).click()
    await page.getByLabel('Tên sản phẩm', { exact: true }).fill('Áo polo Nike trắng viền đỏ rượu')
    await page.getByLabel('Thương hiệu', { exact: true }).fill('Nike')
    await page.getByLabel('Màu sắc theo ảnh', { exact: true }).fill('trắng, đỏ rượu, xám')
    await page.getByLabel('Giá minh họa (VND)', { exact: true }).fill('890000')
    await page.getByLabel('Mô tả theo ảnh và nguồn', { exact: true }).fill('Ảnh nghiêng áo polo trắng với cổ đỏ rượu và vai xám, tay áo có chữ ASB BANK. Nguồn Auckland Museum.')
    await page.getByRole('button', { name: 'Lưu bản nháp', exact: true }).click()
    await expect(page.getByRole('status').filter({ hasText: 'Đã lưu bản nháp.' })).toBeVisible()
    await page.getByText('Thay ảnh và ghi nguồn', { exact: true }).click()
    await page.getByLabel('Ảnh JPEG, PNG hoặc WebP · tối đa 5 MiB', { exact: true }).setInputFiles(photo)
    for (const [label, field] of [['Trang nguồn', 'source_page'], ['URL ảnh gốc', 'original_url'], ['URL đã tải ảnh', 'download_url'], ['Thay đổi so với ảnh gốc', 'transformations'], ['Tác giả ảnh', 'author'], ['Giấy phép', 'license'], ['Trang giấy phép', 'license_url'], ['Ngày lấy ảnh', 'retrieved_at']]) {
      await page.getByLabel(label, { exact: true }).fill(source[field])
    }
    await page.getByRole('checkbox', { name: /^Tôi đã xem ảnh/ }).check()
    await page.getByRole('button', { name: 'Lưu ảnh cho bản nháp', exact: true }).click()
    await expect(page.getByRole('status').filter({ hasText: 'Đã lưu ảnh và nguồn' })).toBeVisible()
    const preflight = page.waitForResponse(r => new URL(r.url()).pathname.endsWith('/draft/preflight'))
    await page.getByRole('button', { name: 'Kiểm tra dữ liệu và ảnh', exact: true }).click()
    const result = await preflight
    expect(result.status()).toBe(200)
    const draft = (await result.json()).draft
    expect(draft.validation.model_fingerprint).toMatch(/^[a-f0-9]{64}$/)
    expect(draft.validation.image_sha256).toBe(source.sha256)
    expect(draft.published).toBe(false)
    await expect(page.getByRole('status').filter({ hasText: 'Đã kiểm tra encoder CPU' })).toBeVisible()
    expect((await page.request.get('/api/v1/products/P181')).status()).toBe(404)
    expect((await (await page.request.get('/api/v1/meta')).json()).index).toEqual(before)
    await page.getByLabel('Tìm mã, tên hoặc thương hiệu', { exact: true }).fill('P181')
    await page.getByRole('button', { name: 'Tìm sản phẩm', exact: true }).click()
    await expect(page.getByRole('button', { name: 'Soạn P181', exact: true })).toBeVisible()
    const editor = page.getByRole('region', { name: 'Nội dung bản nháp', exact: true })
    for (const width of [360, 768, 1440]) {
      await page.setViewportSize({ width, height: 1000 })
      const overflow = await page.evaluate(() => [...document.querySelectorAll<HTMLElement>('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1 && e.getBoundingClientRect().width > 0).map(e => ({ tag: e.tagName, cls: e.className, id: e.id, right: e.getBoundingClientRect().right })))
      expect(overflow, JSON.stringify(overflow)).toEqual([])
      await expectNoHorizontalOverflow(page)
      expect.soft((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
      await editor.screenshot({ path: `../artifacts/frontend/screenshots/catalog-drafts/editor-${width}.png` })
    }
    const other = await page.request.post(endpoint, { headers, data: { version: draft.version, base_catalog_fingerprint: draft.base_catalog_fingerprint, product: { ...draft.product, price_vnd: 900000 } } })
    expect(other.status()).toBe(200)
    await page.getByLabel('Giá minh họa (VND)', { exact: true }).fill('910000')
    await page.getByRole('button', { name: 'Lưu bản nháp', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('phiên khác')
    await expect(page.getByLabel('Giá minh họa (VND)', { exact: true })).toHaveValue('910000')
    await page.getByRole('button', { name: 'Tải lại bản trên server, bỏ nội dung đang sửa', exact: true }).click()
    await expect(page.getByLabel('Giá minh họa (VND)', { exact: true })).toHaveValue('900000')
    await page.getByRole('button', { name: 'Xóa bản nháp đã lưu', exact: true }).click()
    await page.getByRole('button', { name: 'Xác nhận xóa bản nháp', exact: true }).click()
    await expect(page.getByRole('status').filter({ hasText: 'Đã xóa bản nháp.' })).toBeVisible()
    expect((await page.request.get(endpoint + '/image')).status()).toBe(404)
  } finally {
    const latest = (await (await page.request.get(endpoint)).json()).draft
    if (latest.has_draft) expect((await page.request.post(endpoint + '/discard', { headers, data: { version: latest.version } })).status()).toBe(200)
  }
})
