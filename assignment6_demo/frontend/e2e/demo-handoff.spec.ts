import { test, expect } from '@playwright/test'
import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

test('demo catalog: nine corrected products, real photos and real CPU queries', async ({ page }) => {
  const reviews = JSON.parse(readFileSync(new URL('../../data/catalog_repair_batch3_review.json', import.meta.url), 'utf8')) as { product_id: string; sha256: string; metadata: Record<string, string> }[]
  const checks = []
  for (const row of reviews) {
    const response = await page.request.get(`/api/v1/products/${row.product_id}`)
    expect(response.status()).toBe(200)
    const product = (await response.json()).product
    for (const [key, value] of Object.entries(row.metadata)) expect(product[key]).toBe(value)
    const photo = await page.request.get(product.image_url)
    expect(createHash('sha256').update(await photo.body()).digest('hex')).toBe(row.sha256)
    const search = await page.request.post('/api/v1/search', { data: { mode: 'text', text: product.name, options: { search_strategy: 'hybrid', top_k: 3 } } })
    expect(search.status()).toBe(200)
    const body = await search.json()
    expect(body.results.map((r: { product: { product_id: string } }) => r.product.product_id)).toContain(row.product_id)
    checks.push({ product, photo_sha256: row.sha256, search: body })
  }
  await page.goto(`/catalog?q=${encodeURIComponent('đồng hồ Fossil')}`)
  await expect(page.getByTestId('product-card')).toHaveCount(1)
  await expect(page.getByTestId('product-card')).toContainText('Fossil')
  expect(await page.getByTestId('product-card').locator('img').evaluate(img => (img as HTMLImageElement).naturalWidth)).toBeGreaterThan(0)
  writeFileSync(new URL('../../artifacts/validation/demo-catalog-browser-model.json', import.meta.url), JSON.stringify({ scope: 'Catalog-derived demo regression, not independent relevance quality', checks }, null, 2))
})

test('explicit live Groq upload, editable transcript and product search', async ({ page }) => {
  test.skip(process.env.CORTIS_RUN_LIVE_SPEECH !== '1', 'Live paid-provider request requires explicit operator opt-in')
  test.setTimeout(60_000)
  await page.goto('/')
  await page.getByRole('tab', { name: 'Giọng nói', exact: true }).click()
  await page.getByTestId('voice-audio-input').setInputFiles(fileURLToPath(new URL('../../runtime/speech-evaluation/fleurs-vi-01.wav', import.meta.url)))
  const pending = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/speech/transcriptions')
  await page.getByRole('button', { name: 'Nhận dạng lời nói', exact: true }).click()
  const response = await pending
  expect(response.status()).toBe(200)
  const transcript = await response.json()
  expect(transcript.provider).toBe('groq')
  expect(transcript.transcript.length).toBeGreaterThan(10)
  await expect(page.getByTestId('voice-transcript')).toHaveValue(transcript.transcript)
  await page.getByTestId('voice-transcript').fill('đồng hồ Citizen')
  await expect(page.getByText('Đã chỉnh sửa transcript', { exact: true })).toBeVisible()
  const searchPending = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/search' && r.request().method() === 'POST')
  await page.getByTestId('search-submit').click()
  const search = await searchPending
  expect(search.status()).toBe(200)
  const body = await search.json()
  expect(body.results.map((r: { product: { product_id: string } }) => r.product.product_id)).toEqual(['P167'])
  await expect(page.getByTestId('result-card')).toContainText('Citizen')
  writeFileSync(new URL('../../artifacts/backend/demo-groq-browser-live.json', import.meta.url), JSON.stringify({ scope: 'One real human FLEURS upload to Groq in browser, followed by explicitly edited fashion transcript; not a fashion recording or physical microphone test', groq_calls: 1, azure_calls: 0, transcript, edited_query: 'đồng hồ Citizen', search: body }, null, 2))
})
