import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError, createQuote, placePurchase, getPurchases } from '../lib/api'
import type { CheckoutQuote, PurchaseRequest, OrderSummary, ShippingAddress } from '../lib/types'
import { ErrorPanel, formatMoney } from '../ui'
import { formatOrderDate, orderStatusLabels } from './OrdersPage'

export function CheckoutPage() {
  const [quote, setQuote] = useState<CheckoutQuote | null>(null)
  const [address, setAddress] = useState<ShippingAddress>({ recipient: '', phone: '', address_line: '', city: '' })
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [uncertain, setUncertain] = useState(false), [auth, setAuth] = useState(false)
  const locked = useRef(false), alive = useRef(true), key = useRef(''), submitted = useRef<PurchaseRequest | null>(null)
  const navigate = useNavigate()
  useEffect(() => { alive.current = true; return () => { alive.current = false } }, [])
  async function loadQuote() {
    if (locked.current || uncertain) return
    locked.current = true; setBusy(true); setError(''); setAuth(false)
    try { const result = await createQuote(); if (alive.current) { setQuote(result.quote); key.current = crypto.randomUUID(); submitted.current = null } }
    catch (reason) { if (alive.current) { setError(reason instanceof Error ? reason.message : 'Chưa lấy được báo giá.'); setAuth(reason instanceof ApiError && reason.status === 401) } }
    finally { locked.current = false; if (alive.current) setBusy(false) }
  }
  async function place(body: PurchaseRequest) {
    if (locked.current) return
    locked.current = true; setBusy(true); setError('')
    try { const result = await placePurchase(body); if (alive.current) navigate(`/orders/${result.order.order_id}`, { replace: true }) }
    catch (reason) {
      if (alive.current) {
        setError(reason instanceof Error ? reason.message : 'Chưa xác nhận được đơn hàng.')
        const ambiguous = !(reason instanceof ApiError) || reason.status === 0 || reason.status >= 500
        setUncertain(ambiguous)
        if (!ambiguous) { submitted.current = null; setQuote(null); setAuth(reason instanceof ApiError && reason.status === 401) }
      }
    } finally { locked.current = false; if (alive.current) setBusy(false) }
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!quote || locked.current || uncertain) return
    const fields = new FormData(event.currentTarget)
    const body: PurchaseRequest = { quote_id: quote.quote_id, idempotency_key: key.current, shipping_address: { recipient: String(fields.get('recipient')), phone: String(fields.get('phone')), address_line: String(fields.get('address_line')), city: String(fields.get('city')) } }
    submitted.current = body; setAddress(body.shipping_address); void place(body)
  }
  return <div className="page-shell shopping-page" aria-busy={busy}><header className="page-heading"><h1>Xác nhận đặt hàng.</h1><p>Đơn hàng demo · thanh toán khi nhận hàng (COD). Không thu tiền trực tuyến.</p></header>
    <Link className="text-link" to="/cart">Trở lại giỏ hàng</Link>
    {error && <ErrorPanel message={error} />}{auth && <Link className="primary-button" to="/account">Đăng nhập để đặt hàng</Link>}
    {uncertain && <section className="account-panel"><h2>Chưa xác nhận được kết quả</h2><p>Đơn có thể đã được ghi nhận. Kiểm tra lại cùng yêu cầu để tránh đặt trùng.</p><button className="primary-button" disabled={busy} onClick={() => { if (submitted.current) void place(submitted.current) }}>Kiểm tra lại yêu cầu đặt đơn</button><Link className="text-link" to="/purchases">Xem đơn đã đặt</Link></section>}
    {!quote && !uncertain && <button className="primary-button" disabled={busy} onClick={() => { void loadQuote() }}>{busy ? 'Đang kiểm tra giỏ hàng…' : 'Kiểm tra giỏ và lấy báo giá'}</button>}
    {quote && <div className="shopping-layout checkout-layout"><form className="account-panel account-form" onSubmit={submit}><h2>Thông tin nhận hàng</h2><fieldset disabled={busy || uncertain}>
      <label>Người nhận<input name="recipient" defaultValue={address.recipient} autoComplete="shipping name" required minLength={2} maxLength={80} /></label>
      <label>Số điện thoại<input name="phone" defaultValue={address.phone} type="tel" autoComplete="shipping tel" required pattern="(0[0-9]{9}|\+84[0-9]{9})" placeholder="10 chữ số, bắt đầu bằng 0" /></label>
      <label>Địa chỉ nhận hàng<input name="address_line" defaultValue={address.address_line} autoComplete="shipping street-address" required minLength={5} maxLength={250} /></label>
      <label>Tỉnh / thành phố<input name="city" defaultValue={address.city} autoComplete="shipping address-level1" required minLength={2} maxLength={80} /></label>
      <p>COD · phí vận chuyển demo 30.000 ₫; miễn phí từ 2.000.000 ₫.</p>
      <button className="primary-button" type="submit">{busy ? 'Đang xác nhận…' : `Đặt đơn COD · ${formatMoney(quote.total_vnd)}`}</button>
    </fieldset></form><aside className="shopping-summary"><h2>Kiểm tra đơn hàng</h2><ul>{quote.items.map(item => <li key={item.variant_id ?? item.product_id}>{item.product_name}{item.size ? ` (${item.size})` : ''} × {item.quantity}<br />{formatMoney(item.line_total_vnd)}</li>)}</ul><dl className="account-counts"><dt>Tạm tính</dt><dd>{formatMoney(quote.subtotal_vnd)}</dd><dt>Vận chuyển</dt><dd>{formatMoney(quote.shipping_fee_vnd)}</dd><dt>Tổng cộng</dt><dd>{formatMoney(quote.total_vnd)}</dd></dl><p>Báo giá có hiệu lực 10 phút. Hàng chỉ được trừ khi đơn được xác nhận.</p><button className="secondary-button" disabled={busy || uncertain} onClick={() => { void loadQuote() }}>Cập nhật báo giá</button></aside></div>}
  </div>
}

export function PurchaseHistoryPage() {
  const [data, setData] = useState<{ orders: OrderSummary[]; total: number; offset: number; limit: number } | null>(null)
  const [offset, setOffset] = useState(0), [attempt, setAttempt] = useState(0), [loading, setLoading] = useState(true), [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError(''); setData(null)
    getPurchases(offset, controller.signal).then(result => { if (!controller.signal.aborted) setData(result) }).catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Chưa tải được đơn hàng.') }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [offset, attempt])
  return <div className="page-shell shopping-page"><header className="page-heading"><h1>Đơn đã đặt.</h1><p>Các đơn hàng được tạo từ tài khoản của bạn.</p></header>{loading && <p role="status">Đang tải đơn hàng…</p>}{error && <><ErrorPanel message={error} onRetry={() => setAttempt(value => value + 1)} /><Link to="/account" className="text-link">Đăng nhập hoặc kiểm tra tài khoản</Link></>}
    {data && (data.total === 0 ? <div className="empty-state"><h2>Bạn chưa đặt đơn nào</h2><Link className="primary-button" to="/catalog">Khám phá bộ sưu tập</Link></div> : <section className="shopping-list" aria-label="Lịch sử đơn hàng">{data.orders.map(order => <article className="shopping-row" key={order.order_id}><div className="shopping-copy"><h2><Link to={`/orders/${order.order_id}`}>{order.order_id}</Link></h2><p>{formatOrderDate(order.date)} · {orderStatusLabels[order.status]}</p><strong>{formatMoney(order.total_vnd)}</strong><p>Đơn demo · COD</p></div><Link className="secondary-button" to={`/orders/${order.order_id}`}>Xem chi tiết</Link></article>)}<nav className="browse-pagination" aria-label="Phân trang đơn đã đặt"><button className="secondary-button" disabled={offset === 0} onClick={() => setOffset(value => Math.max(0, value - 20))}>Trang trước</button><span>{offset + 1}–{Math.min(offset + 20, data.total)} / {data.total}</span><button className="secondary-button" disabled={offset + 20 >= data.total} onClick={() => setOffset(value => value + 20)}>Trang sau</button></nav></section>)}
  </div>
}
