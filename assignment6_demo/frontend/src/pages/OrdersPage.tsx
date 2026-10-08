import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Search } from 'lucide-react'
import { ApiError, getOrderSummary } from '../lib/api'
import type { OrderSummary } from '../lib/types'
import { ErrorPanel, formatMoney } from '../ui'

export const orderStatusLabels: Record<OrderSummary['status'], string> = {
  processing: 'Đang xử lý', shipped: 'Đang giao hàng', delivered: 'Đã giao hàng', cancelled: 'Đã hủy',
}

export function formatOrderDate(date: string) {
  return new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric',
    timeZone: 'Asia/Ho_Chi_Minh' }).format(new Date(date))
}

export function OrdersPage() {
  const [input, setInput] = useState('')
  const [order, setOrder] = useState<OrderSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldError, setFieldError] = useState<string | null>(null)
  const active = useRef<AbortController | null>(null)
  const sequence = useRef(0)
  const inputRef = useRef<HTMLInputElement>(null)
  useEffect(() => () => { sequence.current += 1; active.current?.abort() }, [])

  async function lookup(event?: FormEvent) {
    event?.preventDefault()
    active.current?.abort()
    const id = ++sequence.current
    const normalized = input.trim().toUpperCase()
    setInput(normalized)
    setOrder(null)
    setError(null)
    if (!/^O[0-9]{3}$/.test(normalized)) {
      setFieldError('Nhập mã gồm chữ O và 3 chữ số, ví dụ O001.')
      setLoading(false)
      inputRef.current?.focus()
      return
    }
    setFieldError(null)
    setLoading(true)
    const controller = new AbortController()
    active.current = controller
    try {
      const result = await getOrderSummary(normalized, controller.signal)
      if (sequence.current === id && !controller.signal.aborted) setOrder(result.order)
    } catch (reason) {
      if (sequence.current === id && !controller.signal.aborted) setError(
        reason instanceof ApiError && reason.status === 404 ? 'Không tìm thấy đơn hàng.' :
        reason instanceof ApiError ? reason.message : 'Chưa tải được đơn hàng. Vui lòng thử lại.',
      )
    } finally {
      if (sequence.current === id && !controller.signal.aborted) setLoading(false)
    }
  }

  return <div className="page-shell">
    <header className="page-heading">
      <h1>Đơn hàng của bạn.</h1>
      <p>Nhập mã đơn hàng để xem trạng thái và chi tiết sản phẩm.</p>
    </header>
    <div className="order-search">
      <form onSubmit={lookup} noValidate>
        <label htmlFor="order-id">Mã đơn hàng</label>
        <div className="order-input-row">
          <input ref={inputRef} id="order-id" name="order_id" value={input} placeholder="Ví dụ O001"
            autoComplete="off" autoCapitalize="characters" spellCheck={false}
            aria-invalid={Boolean(fieldError)} aria-describedby={fieldError ? 'order-id-error' : 'order-id-help'}
            onChange={event => {
              sequence.current += 1
              active.current?.abort()
              setLoading(false)
              setInput(event.target.value)
              setFieldError(null)
              setError(null)
              setOrder(null)
            }} />
          <button type="submit" className="primary-button" disabled={loading}>
            <Search size={18} aria-hidden="true" />{loading ? 'Đang tra cứu…' : 'Tra cứu đơn hàng'}
          </button>
        </div>
        {fieldError ? <p id="order-id-error" className="field-error" role="alert">{fieldError}</p> :
          <p id="order-id-help" className="field-help">Mã gồm chữ O và 3 chữ số.</p>}
      </form>
      <p className="order-search-copy">Dữ liệu đơn hàng trong phiên này là dữ liệu minh họa.</p>
    </div>
    <div aria-live="polite" aria-atomic="true">
      {loading && <p className="page-loading" role="status">Đang kiểm tra mã đơn hàng…</p>}
      {error && <ErrorPanel title="Chưa tìm được đơn hàng" message={error} onRetry={() => { void lookup() }} />}
      {order && <section className="order-summary" aria-labelledby="order-summary-title">
        <div>
          <h2 id="order-summary-title">Đơn hàng {order.order_id}</h2>
          <p className="order-date">Ngày đặt: <time dateTime={order.date}>{formatOrderDate(order.date)}</time></p>
          <span className="status-label order-status">{orderStatusLabels[order.status]}</span>
        </div>
        <div className="order-summary-action">
          <p className="order-total">{formatMoney(order.total_vnd)}</p>
          <Link className="text-link" to={`/orders/${order.order_id}`}>Xem chi tiết đơn hàng <ArrowRight size={18} aria-hidden="true" /></Link>
        </div>
      </section>}
    </div>
  </div>
}
