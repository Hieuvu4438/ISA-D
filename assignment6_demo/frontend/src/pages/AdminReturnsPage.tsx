import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, adminChange, getAdminReturns } from '../lib/api'
import type { ReturnCase, ReturnStatus } from '../lib/types'
import { ErrorPanel } from '../ui'
import { ReturnRecord, returnStatusLabels } from '../components/ReturnPanel'

export function AdminReturnsPage() {
  const [data, setData] = useState<{ returns: ReturnCase[]; total: number } | null>(null), [offset, setOffset] = useState(0), [status, setStatus] = useState(''), [generation, setGeneration] = useState(0)
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false), [error, setError] = useState(''), [notice, setNotice] = useState(''), [reason, setReason] = useState('')
  const alive = useRef(true), locked = useRef(false)
  useEffect(() => {
    const controller = new AbortController(); alive.current = true; setLoading(true); setError(''); setData(null)
    const params = new URLSearchParams({ offset: String(offset), limit: '20' }); if (status) params.set('status', status)
    getAdminReturns(params, controller.signal).then(result => { if (!controller.signal.aborted) setData(result) }).catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Chưa tải được yêu cầu trả hàng.') }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => { alive.current = false; controller.abort() }
  }, [offset, status, generation])
  async function change(item: ReturnCase, next: ReturnStatus, receipt?: { product_id: string; restock_quantity: number }[]) {
    if (locked.current) return
    if (reason.trim().length < 3) { setError('Hãy ghi lý do xử lý từ 3 đến 200 ký tự.'); return }
    locked.current = true; setBusy(true); setError(''); setNotice('')
    try { await adminChange(`returns/${item.return_id}/status`, { status: next, version: item.version, reason, ...(receipt ? { receipt } : {}) }); if (alive.current) { setNotice('Đã xử lý yêu cầu. Kiểm tra trạng thái và lịch sử thao tác.'); setGeneration(value => value + 1) } }
    catch (failure) { if (alive.current) { setError(failure instanceof Error ? failure.message : 'Chưa xác nhận được thao tác. Hãy tải lại để kiểm tra.'); if (failure instanceof ApiError && [401, 403].includes(failure.status)) setData(null) } }
    finally { locked.current = false; if (alive.current) setBusy(false) }
  }
  function receive(event: FormEvent<HTMLFormElement>, item: ReturnCase) {
    event.preventDefault(); const fields = new FormData(event.currentTarget)
    void change(item, 'received', item.items.map(line => ({ product_id: line.product_id, restock_quantity: Number(fields.get(line.product_id)) })))
  }
  return <div className="page-shell shopping-page admin-page" aria-busy={loading || busy}><header className="page-heading"><h1>Xử lý trả hàng.</h1><p>Nhận hàng và nhập lại kho sau kiểm tra. Đối soát tiền chỉ là bản ghi demo.</p></header><nav className="shopping-actions" aria-label="Điều hướng quản trị"><Link className="text-link" to="/admin">Quản trị tồn kho, đơn và tài khoản</Link><Link className="text-link" to="/account">Tài khoản</Link></nav>
    {loading && <p role="status">Đang tải yêu cầu trả hàng…</p>}{error && <ErrorPanel message={error} onRetry={busy ? undefined : () => setGeneration(value => value + 1)} />}{notice && <p role="status">{notice}</p>}
    {data && <><div className="admin-toolbar"><p role="status">{data.total} yêu cầu</p><div><label htmlFor="return-status">Trạng thái trả hàng</label><select id="return-status" value={status} disabled={busy} onChange={event => { setStatus(event.target.value); setOffset(0) }}><option value="">Tất cả</option>{Object.entries(returnStatusLabels).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></div></div>
      <label className="admin-reason">Lý do xử lý<input value={reason} disabled={busy} maxLength={200} onChange={event => setReason(event.target.value)} /></label>
      {data.total === 0 && <p>Chưa có yêu cầu phù hợp.</p>}{data.total > 0 && data.returns.length === 0 && <button className="secondary-button" onClick={() => setOffset(0)}>Về trang đầu</button>}
      <h2 className="visually-hidden">Danh sách yêu cầu trả hàng</h2><div className="admin-records">{data.returns.map(item => <article className="admin-record admin-return-record" key={`${item.return_id}:${item.version}`}><div><ReturnRecord item={item} /><p>Đơn hàng: {item.order_id}</p></div><div className="shopping-actions">
        {item.status === 'requested' && <button className="primary-button" disabled={busy} onClick={() => { void change(item, 'approved') }}>Duyệt {item.return_id}</button>}
        {['requested', 'approved'].includes(item.status) && <button className="secondary-button" disabled={busy} onClick={() => { void change(item, 'rejected') }}>Từ chối {item.return_id}</button>}
        {item.status === 'approved' && <form onSubmit={event => receive(event, item)}><fieldset disabled={busy}><legend>Kiểm nhận {item.return_id}</legend><p>Mặc định cách ly toàn bộ. Chỉ nhập số lượng đủ điều kiện bán lại; phần còn lại không tăng tồn kho.</p>{item.items.map(line => <label key={line.product_id}>Nhập lại kho {line.product_id}<input name={line.product_id} type="number" min="0" max={line.quantity} step="1" defaultValue="0" required /></label>)}<button className="primary-button">Xác nhận đã nhận hàng {item.return_id}</button></fieldset></form>}
        {item.status === 'received' && <div><p>Đóng hồ sơ sẽ ghi nhận giá trị hàng trả để đối soát demo, không xác nhận chuyển tiền.</p><button className="primary-button" disabled={busy} onClick={() => { void change(item, 'closed') }}>Đóng hồ sơ demo {item.return_id}</button></div>}
      </div></article>)}</div>
      {data.returns.length > 0 && <nav className="browse-pagination" aria-label="Phân trang trả hàng"><button className="secondary-button" disabled={busy || offset === 0} onClick={() => setOffset(value => Math.max(0, value - 20))}>Trang trước</button><span>Trang {Math.floor(offset / 20) + 1} / {Math.max(1, Math.ceil(data.total / 20))}</span><button className="secondary-button" disabled={busy || offset + 20 >= data.total} onClick={() => setOffset(value => value + 20)}>Trang sau</button></nav>}
    </>}
  </div>
}
