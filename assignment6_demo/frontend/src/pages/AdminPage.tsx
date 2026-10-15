import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, adminChange, getAccount, getAdminPage, getAdminOrder, type AdminSection } from '../lib/api'
import type { AdminPageData, OrderDetail } from '../lib/types'
import { ErrorPanel, formatMoney } from '../ui'
import { orderStatusLabels, formatOrderDate } from './OrdersPage'
import { AdminCatalogPanel } from '../components/AdminCatalogPanel'

const sections: { id: AdminSection; label: string }[] = [{ id: 'inventory', label: 'Tồn kho' }, { id: 'purchases', label: 'Đơn hàng' }, { id: 'users', label: 'Tài khoản' }, { id: 'audit', label: 'Lịch sử thao tác' }]
const actionLabels: Record<string, string> = { 'inventory.set': 'Điều chỉnh tồn kho', 'order.status': 'Đổi trạng thái đơn', 'account.role': 'Đổi quyền tài khoản', 'account.access': 'Khóa hoặc mở khóa tài khoản', 'return.request': 'Tạo yêu cầu trả hàng', 'return.status': 'Xử lý trả hàng' }
actionLabels['variant.allocate'] = 'Phân kho theo kích cỡ'
const sizeOptions = (category?: string) => ['t_shirt', 'jacket'].includes(category ?? '') ? ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL'] : ['running_shoes', 'trail_shoes', 'casual_shoes', 'boots', 'sandals'].includes(category ?? '') ? Array.from({ length: 15 }, (_, i) => String(34 + i)) : ['ONE']

export function AdminPage() {
  const [showCatalog, setShowCatalog] = useState(false), [catalogOpened, setCatalogOpened] = useState(false)
  const [section, setSection] = useState<AdminSection>('inventory')
  const [offset, setOffset] = useState(0), [generation, setGeneration] = useState(0)
  const [query, setQuery] = useState(''), [filter, setFilter] = useState(''), [status, setStatus] = useState('')
  const [accessState, setAccessState] = useState('')
  const [data, setData] = useState<AdminPageData | null>(null), [detail, setDetail] = useState<OrderDetail | null>(null)
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false), [denied, setDenied] = useState(false)
  const [error, setError] = useState(''), [notice, setNotice] = useState(''), [reason, setReason] = useState(''), [actorId, setActorId] = useState('')
  const alive = useRef(true), locked = useRef(false)
  useEffect(() => {
    alive.current = true; const controller = new AbortController()
    setData(null); setDetail(null); setError(''); setLoading(true); setDenied(false)
    const params = new URLSearchParams({ offset: String(offset), limit: '20' })
    if ((section === 'inventory' || section === 'users') && filter) params.set('q', filter)
    if (section === 'purchases' && status) params.set('status', status)
    if (section === 'users' && accessState) params.set('access_state', accessState)
    void (async () => {
      try {
        const user = await getAccount(controller.signal)
        if (user.user.role !== 'admin') throw new ApiError('Tài khoản không có quyền quản trị.', { status: 403 })
        const result = await getAdminPage(section, params, controller.signal)
        if (!controller.signal.aborted) { setActorId(user.user.user_id); setData(result) }
      } catch (failure) { if (!controller.signal.aborted) { setError(failure instanceof Error ? failure.message : 'Chưa tải được trang quản trị.'); setDenied(failure instanceof ApiError && [401, 403].includes(failure.status)) } }
      finally { if (!controller.signal.aborted) setLoading(false) }
    })()
    return () => { alive.current = false; controller.abort() }
  }, [section, offset, generation, filter, status, accessState])
  async function mutate(path: string, body: object) {
    if (locked.current) return
    if (reason.trim().length < 3) { setError('Hãy ghi lý do thay đổi từ 3 đến 200 ký tự.'); return }
    locked.current = true; setBusy(true); setError(''); setNotice('')
    try {
      await adminChange(path, { ...body, reason })
      if (alive.current) { setNotice('Đã xử lý yêu cầu. Bạn có thể kiểm tra lịch sử thao tác.'); setGeneration(value => value + 1) }
    } catch (failure) {
      if (alive.current) {
        setError(failure instanceof Error ? failure.message : 'Chưa lưu được thay đổi.')
        if (failure instanceof ApiError && [401, 403].includes(failure.status)) { setData(null); setDetail(null); setDenied(true) }
      }
    } finally { locked.current = false; if (alive.current) setBusy(false) }
  }
  function switchSection(next: AdminSection) { setShowCatalog(false); setSection(next); setOffset(0); setNotice(''); setReason(''); setFilter(''); setQuery(''); setAccessState('') }
  function stockSubmit(event: FormEvent<HTMLFormElement>, productId: string) {
    event.preventDefault(); const fields = new FormData(event.currentTarget)
    void mutate(`inventory/${productId}`, { quantity: Number(fields.get('quantity')), revision: data?.revision })
  }
  async function openOrder(id: string) {
    if (locked.current) return
    locked.current = true; setBusy(true); setError('')
    try { const result = await getAdminOrder(id); if (alive.current) setDetail(result.order) }
    catch (failure) { if (alive.current) { setError(failure instanceof Error ? failure.message : 'Chưa tải được đơn hàng.'); setDetail(null); if (failure instanceof ApiError && [401, 403].includes(failure.status)) { setData(null); setDenied(true) } } }
    finally { locked.current = false; if (alive.current) setBusy(false) }
  }
  return <div className="page-shell shopping-page admin-page" aria-busy={loading || busy}><header className="page-heading"><h1>Quản trị Cortis.</h1><p>Quản lý tồn kho, xử lý đơn và kiểm soát quyền truy cập.</p></header>
    <nav className="admin-sections" aria-label="Chức năng quản trị"><button className={showCatalog ? 'primary-button' : 'secondary-button'} aria-pressed={showCatalog} disabled={busy} onClick={() => { setShowCatalog(true); setCatalogOpened(true) }}>Sản phẩm</button>{sections.map(item => <button className={!showCatalog && section === item.id ? 'primary-button' : 'secondary-button'} aria-pressed={!showCatalog && section === item.id} disabled={busy} key={item.id} onClick={() => switchSection(item.id)}>{item.label}</button>)}<Link className="secondary-button" to="/admin/returns">Trả hàng</Link></nav>
    {loading && <p role="status">Đang tải dữ liệu quản trị…</p>}{error && <ErrorPanel message={error} onRetry={busy ? undefined : () => { setDetail(null); setGeneration(value => value + 1) }} />}{denied && <Link className="text-link" to="/account">Đăng nhập bằng tài khoản quản trị</Link>}{notice && <p className="account-notice" role="status">{notice}</p>}
    {catalogOpened && !denied && <div hidden={!showCatalog}><AdminCatalogPanel /></div>}
    {data && !loading && !showCatalog && <>
      <div className="admin-toolbar"><p role="status">{data.total} mục</p>{(section === 'inventory' || section === 'users') && <form onSubmit={event => { event.preventDefault(); setFilter(query.trim()); setOffset(0) }}><label htmlFor="admin-search">{section === 'inventory' ? 'Tìm tên hoặc mã sản phẩm' : 'Tìm email tài khoản'}</label><div className="admin-search-row"><input id="admin-search" value={query} disabled={busy} maxLength={120} onChange={event => setQuery(event.target.value)} /><button className="secondary-button" disabled={busy}>Tìm</button></div></form>}
        {section === 'purchases' && <div><label htmlFor="admin-order-status">Trạng thái đơn</label><select id="admin-order-status" value={status} disabled={busy} onChange={event => { setStatus(event.target.value); setOffset(0) }}><option value="">Tất cả</option>{Object.entries(orderStatusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>}
        {section === 'users' && <div><label htmlFor="admin-access-state">Trạng thái tài khoản</label><select id="admin-access-state" value={accessState} disabled={busy} onChange={event => { setAccessState(event.target.value); setOffset(0) }}><option value="">Tất cả</option><option value="active">Đang hoạt động</option><option value="locked">Đã khóa</option></select></div>}
      </div>
      {section !== 'audit' && <label className="admin-reason">Lý do thay đổi<input value={reason} onChange={event => setReason(event.target.value)} maxLength={200} minLength={3} disabled={busy} placeholder="Ví dụ: Kiểm kê kho định kỳ" /></label>}
      {section === 'users' && <p>Khóa tài khoản sẽ kết thúc mọi phiên đăng nhập. Sau khi mở khóa, khách cần đăng nhập lại. Giỏ hàng và lịch sử đơn được giữ nguyên.</p>}
      {data.total === 0 && <div className="empty-state"><h2>Chưa có dữ liệu phù hợp</h2><p>Thay điều kiện lọc hoặc quay lại khi có dữ liệu mới.</p></div>}
      <div className="admin-records">
        {section === 'inventory' && data.items?.map(item => <article className="admin-record" key={`${item.product_id}:${data.revision}`}><div><h2>{item.product?.name ?? item.product_id}</h2><p>{item.product_id} · {item.product?.brand ?? 'Sản phẩm không còn trong danh mục'}</p><p>{item.size ? `Cỡ ${item.size}` : 'Kho gốc / chưa phân cỡ'} · Tồn kho hiện tại: {item.quantity}</p>
          {item.product && !item.size && <details><summary>Phân hàng sang kích cỡ</summary><p>Số lượng được chuyển từ kho gốc. Khi có kích cỡ, khách chỉ mua các size đã phân; kho gốc còn lại chờ phân cỡ. Size là dữ liệu demo.</p><form onSubmit={event => { event.preventDefault(); const fields = new FormData(event.currentTarget); void mutate(`products/${item.product_id}/variants`, { size: fields.get('size'), quantity: Number(fields.get('allocated')), revision: data.revision }) }}><label>Kích cỡ mới {item.product_id}<select aria-label={`Kích cỡ mới ${item.product_id}`} name="size" required disabled={busy}><option value="">Chọn kích cỡ</option>{sizeOptions(item.product.category).map(size => <option key={size} value={size}>{size}</option>)}</select></label><label>Số lượng chuyển {item.product_id}<input name="allocated" type="number" min="0" max={item.quantity} step="1" defaultValue="0" required disabled={busy} /></label><button className="secondary-button" disabled={busy}>Tạo kích cỡ {item.product_id}</button></form></details>}
        </div><form onSubmit={event => stockSubmit(event, item.product_id)}><label>Số lượng mới {item.product_id}<input name="quantity" type="number" min="0" max="1000000" step="1" required defaultValue={item.quantity} disabled={busy || !item.product} /></label><button className="secondary-button" disabled={busy || !item.product}>Lưu tồn kho {item.product_id}</button></form></article>)}
        {section === 'purchases' && data.orders?.map(order => <article className="admin-record" key={`${order.order_id}:${order.version}`}><div><h2>{order.order_id}</h2><p>{formatOrderDate(order.date)} · {orderStatusLabels[order.status]} · {formatMoney(order.total_vnd)}</p><p>COD demo · chưa xác nhận thu tiền</p><button className="text-link" disabled={busy} onClick={() => { void openOrder(order.order_id) }}>Xem thông tin nhận hàng {order.order_id}</button></div><div className="shopping-actions">{order.status === 'processing' && <><button className="primary-button" disabled={busy} onClick={() => { void mutate(`purchases/${order.order_id}/status`, { status: 'shipped', version: order.version }) }}>Chuyển sang giao hàng {order.order_id}</button><button className="secondary-button" disabled={busy} onClick={() => { void mutate(`purchases/${order.order_id}/status`, { status: 'cancelled', version: order.version }) }}>Hủy đơn {order.order_id}</button></>}{order.status === 'shipped' && <button className="primary-button" disabled={busy} onClick={() => { void mutate(`purchases/${order.order_id}/status`, { status: 'delivered', version: order.version }) }}>Xác nhận đã giao {order.order_id}</button>}</div></article>)}
        {section === 'users' && data.users?.map(user => <article className="admin-record" key={`${user.user_id}:${user.version}`}><div><h2>{user.display_name}</h2><p className="admin-email">{user.email}</p><p>{user.role === 'admin' ? 'Quản trị viên' : 'Khách hàng'}{user.user_id === actorId ? ' · Phiên hiện tại' : ''}</p><p>{user.access_state === 'locked' ? 'Đã khóa' : 'Đang hoạt động'}</p></div><form onSubmit={event => { event.preventDefault(); const value = new FormData(event.currentTarget).get('role'); void mutate(`users/${user.user_id}/role`, { role: value, version: user.version }) }}><label htmlFor={`role-${user.user_id}`}>Quyền của {user.email}</label><select id={`role-${user.user_id}`} name="role" defaultValue={user.role} disabled={busy || user.user_id === actorId}><option value="user">Khách hàng</option><option value="admin">Quản trị viên</option></select><button className="secondary-button" disabled={busy || user.user_id === actorId}>Lưu quyền {user.email}</button><button className="secondary-button" type="button" disabled={busy || user.user_id === actorId} onClick={() => { void mutate(`users/${user.user_id}/access`, { access_state: user.access_state === 'locked' ? 'active' : 'locked', version: user.version }) }}>{user.access_state === 'locked' ? 'Mở khóa' : 'Khóa tài khoản'} {user.email}</button></form></article>)}
        {section === 'audit' && data.events?.map(event => <article className="admin-record" key={event.audit_id}><div><h2>{actionLabels[event.action] ?? event.action}</h2><p>{event.subject_id}</p><p>Lý do: {event.reason}</p><p><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString('vi-VN')}</time></p><p className="admin-email">Người thực hiện: {event.actor_id}</p></div><dl><dt>Trước</dt><dd><code>{JSON.stringify(event.before)}</code></dd><dt>Sau</dt><dd><code>{JSON.stringify(event.after)}</code></dd></dl></article>)}
      </div>
      <nav className="browse-pagination" aria-label="Phân trang quản trị"><button className="secondary-button" disabled={busy || offset === 0} onClick={() => setOffset(value => Math.max(0, value - 20))}>Trang trước</button><span>Trang {Math.floor(offset / 20) + 1} / {Math.max(1, Math.ceil(data.total / 20))}</span><button className="secondary-button" disabled={busy || offset + 20 >= data.total} onClick={() => setOffset(value => value + 20)}>Trang sau</button></nav>
    </>}
    {detail && !showCatalog && <section className="account-panel admin-order-detail" aria-label="Chi tiết nhận hàng"><h2>{detail.order_id}</h2><p>{detail.shipping_address?.recipient}<br />{detail.shipping_address?.phone}<br />{detail.shipping_address?.address_line}, {detail.shipping_address?.city}</p><ul>{detail.items.map(item => <li key={item.variant_id ?? item.product_id}>{item.product_name}{item.size ? ` (${item.size})` : ''} × {item.quantity}</li>)}</ul><button className="secondary-button" onClick={() => setDetail(null)}>Đóng thông tin nhận hàng</button></section>}
  </div>
}
