import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ChevronRight } from 'lucide-react'
import { ApiError, getOrder } from '../lib/api'
import type { OrderDetail } from '../lib/types'
import { ErrorPanel, formatMoney } from '../ui'
import { formatOrderDate, orderStatusLabels } from './OrdersPage'

export function OrderPage() {
  const { orderId = '' } = useParams()
  const [order, setOrder] = useState<OrderDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setOrder(null)
    setError(null)
    setLoading(true)
    getOrder(orderId, controller.signal).then(result => {
      if (!controller.signal.aborted) setOrder(result.order)
    }).catch(reason => {
      if (!controller.signal.aborted) setError(
        reason instanceof ApiError && reason.status === 404 ? 'Không tìm thấy đơn hàng.' :
        reason instanceof ApiError ? reason.message : 'Chưa tải được đơn hàng. Vui lòng thử lại.',
      )
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [orderId, attempt])

  return <div className="page-shell">
    <nav className="breadcrumb" aria-label="Đường dẫn">
      <Link to="/orders"><ArrowLeft size={16} aria-hidden="true" /> Tra cứu đơn hàng</Link>
      <ChevronRight size={14} aria-hidden="true" /><span aria-current="page">Chi tiết đơn hàng</span>
    </nav>
    {loading && <p className="page-loading" role="status">Đang tải đơn hàng…</p>}
    {error && <ErrorPanel title="Chưa tìm được đơn hàng" message={error} onRetry={() => setAttempt(value => value + 1)} />}
    {!loading && order && <article>
      <header className="page-heading order-detail-heading">
        <div><h1>Đơn hàng {order.order_id}.</h1>
          <p>Ngày đặt: <time dateTime={order.date}>{formatOrderDate(order.date)}</time></p>
        </div>
        <span className="status-label order-status">{orderStatusLabels[order.status]}</span>
      </header>
      <div className="order-table-wrap">
        <table className="order-table">
          <caption className="visually-hidden">Sản phẩm trong đơn hàng {order.order_id}</caption>
          <thead><tr><th scope="col">Sản phẩm</th><th scope="col">Số lượng</th><th scope="col">Đơn giá</th><th scope="col">Thành tiền</th></tr></thead>
          <tbody>{order.items.map((item, index) => <tr key={`${item.product_id}-${index}`}>
            <th scope="row"><Link className="text-link" to={`/products/${item.product_id}`}>{item.product_name}</Link>
              <span className="order-reference">{item.product_id}</span></th>
            <td>{item.quantity}</td><td>{formatMoney(item.unit_price_vnd)}</td><td>{formatMoney(item.line_total_vnd)}</td>
          </tr>)}</tbody>
          <tfoot><tr><th scope="row" colSpan={3}>Tổng giá trị đơn hàng</th><td className="order-total">{formatMoney(order.total_vnd)}</td></tr></tfoot>
        </table>
      </div>
      <p className="demo-note">Tên sản phẩm và giá được ghi nhận tại thời điểm đặt đơn. Đây là đơn hàng minh họa.</p>
    </article>}
  </div>
}
