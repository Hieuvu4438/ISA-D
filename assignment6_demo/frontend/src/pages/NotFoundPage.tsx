import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

export function NotFoundPage() {
  return <div className="page-shell empty-state">
    <h1>Trang này không có trong bộ sưu tập.</h1>
    <p>Đường dẫn có thể đã thay đổi. Bạn có thể trở lại tìm sản phẩm hoặc tra cứu đơn hàng.</p>
    <div className="credit-links">
      <Link className="primary-button" to="/"><ArrowLeft size={18} aria-hidden="true" /> Trở lại tìm sản phẩm</Link>
      <Link className="secondary-button" to="/orders">Tra cứu đơn hàng</Link>
    </div>
  </div>
}
