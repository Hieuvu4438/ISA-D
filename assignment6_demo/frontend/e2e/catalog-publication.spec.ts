import { test, expect } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { readFileSync, writeFileSync } from 'node:fs'
import { randomUUID } from 'node:crypto'
import AxeBuilder from '@axe-core/playwright'
import { expectNoHorizontalOverflow } from './helpers'

const email = `admin-e2e-publish-${Date.now()}@example.test`
const password = `Fixture-${randomUUID()}-${randomUUID()}`
const python = fileURLToPath(new URL('../../backend/.venv/Scripts/python.exe', import.meta.url))
const fixture = fileURLToPath(new URL('../../scripts/admin_browser_fixture.py', import.meta.url))
const photo = readFileSync(new URL('../../data/authoring/P181.jpg', import.meta.url))
const source = JSON.parse(readFileSync(new URL('../../data/authoring/P181-source.json', import.meta.url), 'utf8'))
const headers = { 'X-Cortis-Intent': 'admin' }

test.beforeAll(() => execFileSync(python, [fixture, 'provision', '--email', email], { env: { ...process.env, CORTIS_E2E_ADMIN_PASSWORD: password }, stdio: 'pipe' }))
test.afterAll(() => execFileSync(python, [fixture, 'retire', '--email', email], { stdio: 'pipe' }))

test('real CPU publication: activate catalog photo and index together, then query every modality', async ({ page }) => {
  test.setTimeout(60_000)
  await page.goto('/account')
  await page.getByLabel('Email', { exact: true }).fill(email)
  await page.getByLabel('Mật khẩu', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).last().click()
  await page.getByRole('link', { name: 'Mở trang quản trị' }).click()
  const endpoint = '/api/v1/admin/products/P181/draft'
  const before = (await (await page.request.get('/api/v1/meta')).json()).index
  const initial = (await (await page.request.get(endpoint)).json()).draft
  const saved = await page.request.post(endpoint, { headers, data: { version: initial.version, base_catalog_fingerprint: initial.base_catalog_fingerprint,
    product: { name: 'Áo polo Nike trắng viền đỏ rượu', brand: 'Nike', category: 't_shirt', color: 'trắng, đỏ rượu, xám', price_vnd: 890000,
      description: 'Ảnh nghiêng áo polo trắng, cổ đỏ rượu và vai xám; tay áo có chữ ASB BANK. Thông tin thương hiệu theo hồ sơ Auckland Museum.' } } })
  expect(saved.status()).toBe(200)
  const keys = ['source_page', 'original_url', 'download_url', 'transformations', 'author', 'license', 'license_url', 'retrieved_at', 'real_photo_review']
  const upload = await page.request.post(endpoint + '/image', { headers, multipart: { version: String((await saved.json()).draft.version), provenance: JSON.stringify(Object.fromEntries(keys.map(k => [k, source[k]]))), image: { name: 'photo.jpg', mimeType: 'image/jpeg', buffer: photo } } })
  expect(upload.status()).toBe(200)
  await page.getByRole('button', { name: 'Sản phẩm', exact: true }).click()
  await page.getByLabel('Mã sản phẩm cần tạo hoặc mở', { exact: true }).fill('P181')
  await page.getByRole('button', { name: 'Mở mã sản phẩm', exact: true }).click()
  await page.getByRole('button', { name: 'Xuất bản sản phẩm', exact: true }).click()
  for (const width of [360, 1440]) {
    await page.setViewportSize({ width, height: 1000 })
    await expectNoHorizontalOverflow(page)
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([])
    await page.getByRole('region', { name: 'Kiểm tra bản nháp', exact: true }).screenshot({ path: `../artifacts/frontend/screenshots/catalog-publication/confirm-${width}.png` })
  }
  const pending = page.waitForResponse(r => new URL(r.url()).pathname.endsWith('/draft/publish'))
  await page.getByRole('button', { name: 'Xác nhận xuất bản', exact: true }).click()
  const published = await pending
  expect(published.status()).toBe(200)
  const publication = (await published.json()).publication
  expect(publication.published).toBe(true)
  expect(publication.catalog_fingerprint).toMatch(/^[a-f0-9]{64}$/)
  const meta = await (await page.request.get('/api/v1/meta')).json()
  expect(meta.index.catalog_fingerprint).toBe(publication.catalog_fingerprint)
  expect(meta.index.index_fingerprint).toBe(publication.index_fingerprint)
  const product = (await (await page.request.get('/api/v1/products/P181')).json()).product
  expect(product.name).toBe('Áo polo Nike trắng viền đỏ rượu')
  expect(product.stock_quantity).toBe(0)
  await expect((await page.request.get('/api/v1/media/products/P181')).body()).resolves.toEqual(photo)
  const catalog = await (await page.request.get('/api/v1/catalog?q=P181')).json()
  expect(catalog.products.map((p: { product_id: string }) => p.product_id)).toEqual(['P181'])
  const results = []
  for (const mode of ['text', 'voice', 'image', 'multimodal']) {
    const options = { search_strategy: 'hybrid', top_k: 20, filters: { category: 't_shirt', max_price: 890000 } }
    const result = mode === 'text' || mode === 'voice'
      ? await page.request.post('/api/v1/search', { data: { mode, text: 'P181', options, ...(mode === 'voice' ? { voice_source: 'manual_transcript' } : {}) } })
      : await page.request.post(`/api/v1/search/${mode}`, { multipart: { options: JSON.stringify(options), image: { name: 'photo.jpg', mimeType: 'image/jpeg', buffer: photo }, ...(mode === 'multimodal' ? { text: 'P181', text_weight: '0.5' } : {}) } })
    expect(result.status()).toBe(200)
    const body = await result.json()
    expect(body.meta.index_fingerprint).toBe(publication.index_fingerprint)
    expect(body.results.some((r: { product: { product_id: string } }) => r.product.product_id === 'P181')).toBe(true)
    expect(body.results.every((r: { product: { price_vnd: number } }) => r.product.price_vnd <= 890000)).toBe(true)
    results.push({ mode, response: body })
  }
  writeFileSync(new URL('../../artifacts/backend/catalog-publication-real-encoder.json', import.meta.url), JSON.stringify({ scope: 'Live CPU publication and four-mode property smoke; image self-match, not independent relevance quality', speech_calls: 0, before, publication, meta, product, results }, null, 2))
  await page.goto('/products/P181')
  await expect(page.getByRole('heading', { name: 'Áo polo Nike trắng viền đỏ rượu', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Tạm hết hàng', exact: true })).toBeDisabled()
})
