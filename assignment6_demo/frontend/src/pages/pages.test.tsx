import { act } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ProductPage } from './ProductPage'
import { OrdersPage } from './OrdersPage'
import { OrderPage } from './OrderPage'
import { CreditsPage } from './CreditsPage'

let node: HTMLDivElement
let root: Root

beforeEach(() => {
  Object.assign(globalThis, { IS_REACT_ACT_ENVIRONMENT: true })
  node = document.createElement('div')
  document.body.append(node)
  root = createRoot(node)
})

afterEach(async () => {
  await act(async () => root.unmount())
  node.remove()
  vi.unstubAllGlobals()
})

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function product(id: string, name: string) {
  return { request_id: 'test-request', product: {
    product_id: id, name, category: 'running_shoes', brand: 'Test brand', color: 'đen',
    price_vnd: 1000000, in_stock: true, stock_quantity: 3,
    image_url: `/api/v1/media/products/${id}`, description: 'Dữ liệu kiểm thử.',
    image_credit: { source_page: 'https://commons.wikimedia.org/wiki/Test',
      author: 'Test author', license: 'CC BY', license_url: 'https://creativecommons.org/licenses/by/4.0/', transformations: [] },
  } }
}

async function renderPage(path: string) {
  const router = createMemoryRouter([
    { path: '/products/:productId', element: <ProductPage /> },
    { path: '/orders', element: <OrdersPage /> },
    { path: '/orders/:orderId', element: <OrderPage /> },
    { path: '/credits', element: <CreditsPage /> },
  ], { initialEntries: [path] })
  await act(async () => { root.render(<RouterProvider router={router} />) })
  return router
}

async function changeInput(value: string) {
  const input = node.querySelector('input')!
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')!.set!
  await act(async () => {
    setter.call(input, value)
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })
}

async function submitForm() {
  await act(async () => {
    node.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
  })
}

describe('secondary page workflows', () => {
  it('loads product directly and ignores a late response after changing route', async () => {
    let first!: (value: Response) => void
    let second!: (value: Response) => void
    const fetch = vi.fn()
      .mockImplementationOnce(() => new Promise<Response>(resolve => { first = resolve }))
      .mockImplementationOnce(() => new Promise<Response>(resolve => { second = resolve }))
    vi.stubGlobal('fetch', fetch)
    const router = await renderPage('/products/P001')
    expect(node.textContent).toContain('Đang tải sản phẩm')
    await act(async () => { await router.navigate('/products/P002') })
    expect(fetch.mock.calls[0][1].signal.aborted).toBe(true)
    await act(async () => { second(response(product('P002', 'Sản phẩm mới'))) })
    await act(async () => { first(response(product('P001', 'Phản hồi cũ'))) })
    expect(node.querySelector('h1')?.textContent).toBe('Sản phẩm mới')
    expect(node.textContent).not.toContain('Phản hồi cũ')
    expect(fetch.mock.calls.every(([url]) => String(url).startsWith('/api/v1/products/'))).toBe(true)
  })

  it('requires explicit order submit, rejects invalid IDs, normalizes and links the summary', async () => {
    const fetch = vi.fn().mockResolvedValue(response({ request_id: 'test-request', order: {
      order_id: 'O001', date: '2026-09-20T03:00:00Z', status: 'delivered', total_vnd: 1500000,
    } }))
    vi.stubGlobal('fetch', fetch)
    await renderPage('/orders')
    expect(fetch).not.toHaveBeenCalled()
    await changeInput('001')
    await submitForm()
    expect(fetch).not.toHaveBeenCalled()
    expect(node.querySelector('[role="alert"]')?.textContent).toContain('3 chữ số')
    await changeInput(' o001 ')
    expect(fetch).not.toHaveBeenCalled()
    await submitForm()
    expect(fetch.mock.calls[0][0]).toBe('/api/v1/orders?order_id=O001')
    expect(node.textContent).toContain('Đã giao hàng')
    expect(node.querySelector('a[href="/orders/O001"]')).not.toBeNull()
  })

  it('keeps missing and foreign order UI generic', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ error: {
      code: 'ORDER_NOT_FOUND', message: 'Không tìm thấy đơn hàng.', field_errors: [], retryable: false,
      request_id: 'test-request',
    } }, 404)))
    await renderPage('/orders/O002')
    expect(node.querySelector('[role="alert"]')?.textContent).toContain('Không tìm thấy đơn hàng.')
    expect(node.textContent).not.toMatch(/C002|chủ sở hữu|khách hàng khác/)
    expect(node.querySelector('table')).toBeNull()
  })

  it('uses catalog credits and real backend media paths', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ request_id: 'test-request', credits: [{
      product_id: 'P001', asset_id: 'test-asset', author: 'Test photographer', license: 'CC BY',
      source_page: 'https://commons.wikimedia.org/wiki/Test',
      license_url: 'https://creativecommons.org/licenses/by/4.0/', transformations: ['resize'],
    }] })))
    await renderPage('/credits')
    expect(node.querySelector('img')?.getAttribute('src')).toBe('/api/v1/media/products/P001')
    expect(node.textContent).toContain('Test photographer')
    expect(node.textContent).toContain('resize')
    expect(node.querySelector('a[href="https://commons.wikimedia.org/wiki/Test"]')?.getAttribute('rel'))
      .toBe('noopener noreferrer')
  })
})
