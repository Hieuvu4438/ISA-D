import type {
  CreditsResponse, FieldError, MetaResponse, OrderResponse, OrderSummaryResponse,
  ProductResponse, ProductsResponse, SearchOptions, SearchResponse,
  TextSearchRequest, TranscriptionResponse,
} from './types'

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly field_errors: FieldError[]
  readonly retryable: boolean
  readonly request_id: string | null
  readonly retryAfter: number | null

  constructor(message: string, options: {
    code?: string; status?: number; field_errors?: FieldError[]; retryable?: boolean
    request_id?: string | null; retryAfter?: number | null
  } = {}) {
    super(message)
    this.name = 'ApiError'
    this.code = options.code ?? 'NETWORK_ERROR'
    this.status = options.status ?? 0
    this.field_errors = options.field_errors ?? []
    this.retryable = options.retryable ?? false
    this.request_id = options.request_id ?? null
    this.retryAfter = options.retryAfter ?? null
  }
}

function retryDelay(value: string | null): number | null {
  if (!value) return null
  const seconds = /^\d+$/.test(value) ? Number(value) : Math.ceil((Date.parse(value) - Date.now()) / 1000)
  return Number.isFinite(seconds) && seconds >= 0 && seconds <= 3600 ? seconds : null
}

async function request<T>(path: string, init: RequestInit = {}, signal?: AbortSignal, timeoutMs = 15_000): Promise<T> {
  const controller = new AbortController()
  let timedOut = false
  const cancel = () => controller.abort(signal?.reason)
  if (signal?.aborted) cancel()
  signal?.addEventListener('abort', cancel, { once: true })
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)
  try {
    if (controller.signal.aborted) throw new DOMException('Đã hủy yêu cầu.', 'AbortError')
    const response = await fetch(`/api/v1${path}`, { ...init, signal: controller.signal, cache: 'no-store' })
    let payload: unknown
    try {
      payload = await response.json()
    } catch {
      throw new ApiError('Máy chủ trả về dữ liệu không hợp lệ. Vui lòng thử lại.', {
        code: 'INVALID_RESPONSE', status: response.status, request_id: response.headers.get('x-request-id'),
      })
    }
    if (!response.ok) {
      const envelope = payload as { error?: { code?: unknown; message?: unknown; field_errors?: unknown; retryable?: unknown; request_id?: unknown } }
      const error = envelope && typeof envelope === 'object' ? envelope.error : undefined
      const fields = Array.isArray(error?.field_errors) ? error.field_errors.filter((field): field is FieldError => (
        typeof field === 'object' && field !== null && typeof field.field === 'string' && typeof field.message === 'string'
      )) : []
      throw new ApiError(typeof error?.message === 'string' ? error.message : 'Không thể xử lý yêu cầu. Vui lòng thử lại.', {
        code: typeof error?.code === 'string' ? error.code : 'HTTP_ERROR',
        status: response.status, field_errors: fields, retryable: error?.retryable === true,
        request_id: typeof error?.request_id === 'string' ? error.request_id : response.headers.get('x-request-id'),
        retryAfter: retryDelay(response.headers.get('retry-after')),
      })
    }
    if (payload === null || typeof payload !== 'object') throw new ApiError('Dữ liệu máy chủ không hợp lệ.', { code: 'INVALID_RESPONSE' })
    if (controller.signal.aborted) throw new DOMException('Đã hủy yêu cầu.', 'AbortError')
    return payload as T
  } catch (error) {
    if (timedOut) throw new ApiError('Yêu cầu quá thời gian. Vui lòng thử lại.', { code: 'CLIENT_TIMEOUT', retryable: true })
    if (signal?.aborted || (error instanceof DOMException && error.name === 'AbortError')) throw new DOMException('Đã hủy yêu cầu.', 'AbortError')
    if (error instanceof ApiError) throw error
    throw new ApiError('Không kết nối được máy chủ. Kiểm tra kết nối và thử lại.', { code: 'NETWORK_ERROR', retryable: true })
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', cancel)
  }
}

export const getMeta = (signal?: AbortSignal) => request<MetaResponse>('/meta', {}, signal)
export const getProducts = (offset = 0, limit = 12, signal?: AbortSignal) => request<ProductsResponse>(`/products?offset=${offset}&limit=${limit}`, {}, signal)
export const getProduct = (id: string, signal?: AbortSignal) => request<ProductResponse>(`/products/${encodeURIComponent(id)}`, {}, signal)
export const getCredits = (signal?: AbortSignal) => request<CreditsResponse>('/credits', {}, signal)
export const getOrder = (id: string, signal?: AbortSignal) => request<OrderResponse>(`/orders/${encodeURIComponent(id.trim().toUpperCase())}`, {}, signal)
export const getOrderSummary = (id: string, signal?: AbortSignal) => request<OrderSummaryResponse>(`/orders?order_id=${encodeURIComponent(id.trim().toUpperCase())}`, {}, signal)

export function searchText(body: TextSearchRequest, signal?: AbortSignal): Promise<SearchResponse> {
  return request('/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }, signal)
}

export function searchImage(file: File, options: SearchOptions, signal?: AbortSignal): Promise<SearchResponse> {
  const body = new FormData()
  body.append('image', file)
  body.append('options', JSON.stringify(options))
  return request('/search/image', { method: 'POST', body }, signal)
}

export function searchMultimodal(text: string, file: File, weight: number, options: SearchOptions, signal?: AbortSignal): Promise<SearchResponse> {
  const body = new FormData()
  body.append('image', file)
  body.append('text', text)
  body.append('text_weight', JSON.stringify(weight))
  body.append('options', JSON.stringify(options))
  return request('/search/multimodal', { method: 'POST', body }, signal)
}

export function transcribe(file: File, signal?: AbortSignal): Promise<TranscriptionResponse> {
  const body = new FormData()
  body.append('audio', file)
  body.append('language', 'vi-VN')
  return request('/speech/transcriptions', { method: 'POST', body }, signal, 95_000)
}
