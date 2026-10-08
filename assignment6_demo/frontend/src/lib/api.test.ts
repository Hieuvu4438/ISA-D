import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, getMeta, getOrder, searchImage, searchText, transcribe } from './api'

const options = { top_k: 3, result_policy: 'nearest' as const, filters: {} }

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers() })

describe('real API contract and cancellation', () => {
  it('preserves structured errors and Retry-After without automatically retrying', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: {
      code: 'SEARCH_BUSY', message: 'Hệ thống đang xử lý.', field_errors: [], retryable: true, request_id: 'test-id',
    } }), { status: 429, headers: { 'retry-after': '2' } }))
    vi.stubGlobal('fetch', fetcher)
    const error = await searchText({ mode: 'text', text: 'giày', options }).catch(value => value)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ code: 'SEARCH_BUSY', status: 429, retryAfter: 2, request_id: 'test-id', retryable: true })
    expect(fetcher).toHaveBeenCalledTimes(1)
  })

  it('sends multipart upload bytes with options JSON and browser-generated boundary', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('{}'))
    vi.stubGlobal('fetch', fetcher)
    await searchImage(new File(['photo'], 'photo.jpg', { type: 'image/jpeg' }), options)
    const [url, init] = fetcher.mock.calls[0]
    expect(url).toBe('/api/v1/search/image')
    expect(init.headers).toBeUndefined()
    expect(init.body.get('image').name).toBe('photo.jpg')
    expect(JSON.parse(init.body.get('options'))).toEqual(options)
  })

  it('propagates caller cancellation and never fetches an already canceled request', async () => {
    const fetcher = vi.fn()
    vi.stubGlobal('fetch', fetcher)
    const controller = new AbortController()
    controller.abort()
    await expect(getMeta(controller.signal)).rejects.toMatchObject({ name: 'AbortError' })
    expect(fetcher).not.toHaveBeenCalled()
  })

  it('aborts active calls and cleans up the caller abort listener', async () => {
    const controller = new AbortController()
    const remove = vi.spyOn(controller.signal, 'removeEventListener')
    vi.stubGlobal('fetch', (_url: string, init: RequestInit) => new Promise((_resolve, reject) => {
      init.signal?.addEventListener('abort', () => reject(new DOMException('abort', 'AbortError')))
    }))
    const result = getMeta(controller.signal)
    controller.abort()
    await expect(result).rejects.toMatchObject({ name: 'AbortError' })
    expect(remove).toHaveBeenCalledWith('abort', expect.any(Function))
  })

  it('caps search at 15 seconds and allows CPU transcription 95 seconds', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', (_url: string, init: RequestInit) => new Promise((_resolve, reject) => {
      init.signal?.addEventListener('abort', () => reject(new DOMException('abort', 'AbortError')))
    }))
    const search = searchText({ mode: 'text', text: 'giày', options }).catch(error => error)
    const speech = transcribe(new File(['wave'], 'audio.wav', { type: 'audio/wav' })).catch(error => error)
    await vi.advanceTimersByTimeAsync(15_000)
    expect(await search).toMatchObject({ code: 'CLIENT_TIMEOUT' })
    let settled = false
    void speech.then(() => { settled = true })
    await Promise.resolve()
    expect(settled).toBe(false)
    await vi.advanceTimersByTimeAsync(15_000)
    expect(settled).toBe(false)
    await vi.advanceTimersByTimeAsync(65_000)
    expect(await speech).toMatchObject({ code: 'CLIENT_TIMEOUT' })
  })

  it('maps connectivity errors and rejects malformed HTML safely', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('secret endpoint details')))
    await expect(getMeta()).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>private diagnostics</html>', { status: 502 })))
    await expect(getMeta()).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
  })

  it('normalizes order ID and encodes route segments', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('{}'))
    vi.stubGlobal('fetch', fetcher)
    await getOrder(' o001 ')
    expect(fetcher.mock.calls[0][0]).toBe('/api/v1/orders/O001')
  })
})
