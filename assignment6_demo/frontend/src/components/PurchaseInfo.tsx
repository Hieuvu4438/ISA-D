import { useEffect, useRef, useState } from 'react'
import type { OrderDetail } from '../lib/types'
import { cancelPurchase } from '../lib/api'
import { ErrorPanel } from '../ui'

export function PurchaseInfo({ order, onChange }: { order: OrderDetail; onChange: (order: OrderDetail) => void }) {
  const [confirm, setConfirm] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const alive = useRef(true), locked = useRef(false)
  useEffect(() => { alive.current = true; return () => { alive.current = false } }, [])
  async function cancel() {
    if (locked.current || order.version == null) return
    locked.current = true; setBusy(true); setError('')
    try { const result = await cancelPurchase(order.order_id, order.version); if (alive.current) { onChange(result.order); setConfirm(false) } }
    catch (reason) { if (alive.current) setError(reason instanceof Error ? reason.message : 'Chưa hủy được đơn hàng.') }
    finally { locked.current = false; if (alive.current) setBusy(false) }
  }
  return <section className="account-panel purchase-info"><h2>Nhận hàng và thanh toán</h2><p>COD · {order.status === 'cancelled' ? 'Đơn đã hủy; không thu tiền.' : 'Chưa thanh toán. Đây là đơn hàng demo.'}</p>{order.shipping_address && <p>{order.shipping_address.recipient}<br />{order.shipping_address.phone}<br />{order.shipping_address.address_line}, {order.shipping_address.city}</p>}
    {order.status === 'processing' && (confirm ? <div><p>Xác nhận hủy đơn? Số lượng sản phẩm sẽ được hoàn lại tồn kho.</p><div className="shopping-actions"><button className="primary-button" disabled={busy} onClick={() => { void cancel() }}>{busy ? 'Đang hủy…' : 'Xác nhận hủy đơn'}</button><button className="secondary-button" disabled={busy} onClick={() => setConfirm(false)}>Giữ đơn hàng</button></div></div> : <button className="secondary-button" onClick={() => setConfirm(true)}>Hủy đơn hàng</button>)}
    {order.status === 'cancelled' && <p role="status">Đã hủy đơn và hoàn lại tồn kho.</p>}{error && <ErrorPanel message={error} />}
  </section>
}
