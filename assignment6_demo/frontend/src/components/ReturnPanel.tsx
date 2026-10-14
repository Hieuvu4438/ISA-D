import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError, createReturn, getOrderReturns, withdrawReturn } from '../lib/api'
import type { CreateReturnRequest, OrderReturns, ReturnCase, ReturnStatus } from '../lib/types'
import { ErrorPanel, formatMoney } from '../ui'

export const returnStatusLabels: Record<ReturnStatus, string> = { requested: 'Chờ duyệt', approved: 'Đã duyệt, chờ nhận hàng', rejected: 'Từ chối', withdrawn: 'Khách đã rút', received: 'Đã nhận và kiểm tra', closed: 'Đã đóng hồ sơ demo' }
const eligibilityLabels: Record<string, string> = { not_delivered: 'Chỉ đơn đã giao mới có thể yêu cầu trả hàng.', delivery_unconfirmed: 'Chưa có mốc xác nhận giao hàng để tính thời hạn trả.', window_expired: 'Đã ngoài thời hạn trả hàng demo.', quantity_exhausted: 'Toàn bộ số lượng đã có yêu cầu trả hàng.' }

export function ReturnRecord({ item }: { item: ReturnCase }) {
  return <><h3>{item.return_id}</h3><p>{returnStatusLabels[item.status]}</p><p>Lý do: {item.reason}</p><ul>{item.items.map(line => <li key={line.product_id}>{line.product_name} × {line.quantity}</li>)}</ul><p>Giá trị hàng trả: {formatMoney(item.merchandise_value_vnd)} · không gồm phí giao hàng</p>{item.operator_note && <p>Phản hồi xử lý: {item.operator_note}</p>}{item.receipt && <ul aria-label="Kết quả kiểm nhận">{item.receipt.map(line => <li key={line.product_id}>{line.product_id}: nhập lại kho {line.restock_quantity}, cách ly {item.items.find(i => i.product_id === line.product_id)!.quantity - line.restock_quantity}</li>)}</ul>}{item.refund_status === 'demo_recorded' && <p>Đã ghi nhận số tiền đối soát demo: {formatMoney(item.refund_amount_vnd)}. Chưa thực hiện hoàn tiền thật.</p>}</>
}

export function ReturnPanel({ orderId }: { orderId: string }) {
  const [data, setData] = useState<OrderReturns | null>(null), [generation, setGeneration] = useState(0)
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false), [error, setError] = useState(''), [notice, setNotice] = useState(''), [uncertain, setUncertain] = useState(false)
  const alive = useRef(true), locked = useRef(false), submitted = useRef<CreateReturnRequest | null>(null)
  useEffect(() => {
    const controller = new AbortController(); alive.current = true; setLoading(true); setError(''); setData(null)
    getOrderReturns(orderId, controller.signal).then(result => { if (!controller.signal.aborted) setData(result) }).catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Chưa tải được trả hàng.') }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => { alive.current = false; controller.abort() }
  }, [orderId, generation])
  async function send(body: CreateReturnRequest) {
    if (locked.current) return
    locked.current = true; setBusy(true); setError('')
    try {
      const result = await createReturn(orderId, body)
      if (alive.current) { submitted.current = null; setUncertain(false); setNotice(`Đã ghi nhận ${result.return.return_id}.`); setGeneration(value => value + 1) }
    } catch (reason) {
      if (alive.current) {
        const ambiguous = !(reason instanceof ApiError) || reason.status === 0 || reason.status >= 500
        setUncertain(ambiguous); if (!ambiguous) submitted.current = null
        if (reason instanceof ApiError && [401, 403].includes(reason.status)) setData(null)
        setError(reason instanceof Error ? reason.message : 'Chưa xác nhận được yêu cầu.')
      }
    } finally { locked.current = false; if (alive.current) setBusy(false) }
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!data || locked.current || uncertain) return
    const fields = new FormData(event.currentTarget)
    const items = data.eligibility.items.map(item => ({ product_id: item.product_id, quantity: Number(fields.get(item.product_id) ?? 0) })).filter(item => item.quantity > 0)
    if (!items.length) { setError('Chọn ít nhất một sản phẩm với số lượng từ 1.'); return }
    const body = { version: data.order_version, idempotency_key: crypto.randomUUID(), reason: String(fields.get('reason') ?? '').trim(), items }
    if (body.reason.length < 3) { setError('Hãy ghi lý do trả hàng từ 3 đến 200 ký tự.'); return }
    submitted.current = body; void send(body)
  }
  async function withdraw(item: ReturnCase) {
    if (locked.current || uncertain) return
    locked.current = true; setBusy(true); setError('')
    try { await withdrawReturn(item.return_id, item.version); if (alive.current) { setNotice('Đã rút yêu cầu trả hàng.'); setGeneration(value => value + 1) } }
    catch (reason) { if (alive.current) setError(reason instanceof Error ? reason.message : 'Chưa rút được yêu cầu. Hãy tải lại để kiểm tra.') }
    finally { locked.current = false; if (alive.current) setBusy(false) }
  }
  return <section className="account-panel purchase-info" aria-label="Trả hàng" aria-busy={loading || busy}><h2>Trả hàng</h2><p>Chính sách demo: yêu cầu trong 30 ngày từ lúc xác nhận giao hàng. Giá trị đối soát theo giá sản phẩm lúc đặt; không gồm phí giao hàng. Không chuyển tiền thật.</p>
    {loading && <p role="status">Đang tải yêu cầu trả hàng…</p>}{error && <ErrorPanel message={error} />}{notice && <p role="status">{notice}</p>}
    {uncertain && <div><p>Yêu cầu có thể đã được ghi nhận. Kiểm tra lại cùng nội dung để tránh gửi trùng.</p><button className="primary-button" disabled={busy} onClick={() => { if (submitted.current) void send(submitted.current) }}>Kiểm tra lại yêu cầu trả hàng</button></div>}
    {!uncertain && <button className="text-link" disabled={loading || busy} onClick={() => setGeneration(value => value + 1)}>Tải lại trạng thái trả hàng</button>}
    {data && !loading && <>{data.eligibility.eligible ? <form className="account-form" key={generation} onSubmit={submit}><fieldset disabled={busy || uncertain}><legend>Sản phẩm muốn trả</legend>{data.eligibility.items.filter(item => item.remaining_quantity > 0).map(item => <label key={item.product_id}>Số lượng trả {item.product_name}<input name={item.product_id} type="number" min="0" max={item.remaining_quantity} step="1" defaultValue="0" required /><span>Còn có thể yêu cầu: {item.remaining_quantity}</span></label>)}<label>Lý do trả hàng<textarea name="reason" required minLength={3} maxLength={200} /></label><p>Hạn gửi: {data.eligibility.deadline && new Date(data.eligibility.deadline).toLocaleString('vi-VN')}</p><button className="primary-button" type="submit">Gửi yêu cầu trả hàng</button></fieldset></form> : <p>{eligibilityLabels[data.eligibility.ineligible_reason ?? ''] ?? 'Đơn chưa đủ điều kiện trả hàng.'}</p>}
      {data.returns.map(item => <article className="admin-record" key={item.return_id}><div><ReturnRecord item={item} />{item.status === 'requested' && <button className="secondary-button" disabled={busy || uncertain} onClick={() => { void withdraw(item) }}>Rút yêu cầu {item.return_id}</button>}</div></article>)}
    </>}
  </section>
}
