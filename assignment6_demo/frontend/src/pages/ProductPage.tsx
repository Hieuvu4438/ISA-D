import { useEffect, useState } from 'react'
import { Link, useParams, useLocation } from 'react-router-dom'
import { ArrowLeft, ArrowUpRight, ChevronRight } from 'lucide-react'
import { ApiError, getProduct } from '../lib/api'
import type { ProductDetail } from '../lib/types'
import { ProductImage, ErrorPanel, formatMoney, categoryLabels, formatTransformation } from '../ui'
import { ProductShopping } from '../components/ProductShopping'
import { use3DTilt } from '../lib/use3DTilt'

export function ProductPage() {
  const location = useLocation()
  const source = (location.state as { from?: string } | null)?.from
  const returnTo = typeof source === 'string' && (source === '/' || /^\/catalog(?:\?|$)/.test(source)) ? source : '/catalog'
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<{ message: string; missing: boolean } | null>(null)
  const [attempt, setAttempt] = useState(0)
  const imageTilt = use3DTilt<HTMLDivElement>({ maxTilt: 5, scale: 1.015 })

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setProduct(null)
    setError(null)
    getProduct(productId, controller.signal).then(response => {
      if (!controller.signal.aborted) setProduct(response.product)
    }).catch(reason => {
      if (!controller.signal.aborted) setError({
        missing: reason instanceof ApiError && reason.status === 404,
        message: reason instanceof ApiError ? reason.message : 'Chưa tải được sản phẩm. Vui lòng thử lại.',
      })
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [productId, attempt])

  return <div className="page-shell">
    <nav className="breadcrumb" aria-label="Đường dẫn">
      <Link to={returnTo}><ArrowLeft size={16} aria-hidden="true" /> Trở lại bộ sưu tập</Link>
      <ChevronRight size={14} aria-hidden="true" />
      <span aria-current="page">Chi tiết sản phẩm</span>
    </nav>
    {loading && <div className="page-loading" role="status">Đang tải sản phẩm…</div>}
    {error && <ErrorPanel title={error.missing ? 'Không tìm thấy sản phẩm' : 'Chưa tải được sản phẩm'}
      message={error.message} onRetry={() => setAttempt(value => value + 1)} />}
    {!loading && product && <article className="detail-layout">
      <div ref={imageTilt.ref} onMouseMove={imageTilt.onMouseMove} onMouseLeave={imageTilt.onMouseLeave} className="detail-image tilt-card">
        <ProductImage src={product.image_url} alt={product.name} />
        <div className="glare-effect" />
      </div>
      <div className="detail-copy">
        <h1>{product.name}</h1>
        <p className="detail-description">{product.description}</p>
        <p className="detail-price">{formatMoney(product.price_vnd)}</p>
        <p className="stock-status"><span className={`status-label ${product.in_stock ? 'in-stock' : 'out-of-stock'}`}>
          {product.sale_state === 'archived' ? 'Sản phẩm tạm ngừng bán' : product.in_stock ? `Còn hàng · ${product.stock_quantity} sản phẩm` : 'Tạm hết hàng'}
        </span></p>
        <dl className="detail-metadata">
          <div><dt>Thương hiệu</dt><dd>{product.brand}</dd></div>
          <div><dt>Danh mục</dt><dd>{categoryLabels[product.category]}</dd></div>
          <div><dt>Màu sắc</dt><dd>{product.color}</dd></div>
          <div><dt>Mã sản phẩm</dt><dd>{product.product_id}</dd></div>
        </dl>
        <p className="demo-note">Giá và tồn kho là dữ liệu minh họa.</p>
        <ProductShopping key={product.product_id} product={product} />

        <div className="product-atelier-perks" aria-label="Cam kết Cortis Atelier">
          <div className="perk-item">
            <span className="perk-bullet" aria-hidden="true">✦</span>
            <div><strong>Đồng kiểm khi nhận hàng (COD)</strong><p>Mở hộp kiểm tra đúng mẫu mã, màu sắc trước khi thanh toán.</p></div>
          </div>
          <div className="perk-item">
            <span className="perk-bullet" aria-hidden="true">✦</span>
            <div><strong>Đổi kích cỡ trong 7 ngày</strong><p>Hỗ trợ đổi kích cỡ nhanh chóng nếu không vừa vặn.</p></div>
          </div>
          <div className="perk-item">
            <span className="perk-bullet" aria-hidden="true">✦</span>
            <div><strong>Ảnh mẫu vật thực tế 100%</strong><p>Không dùng ảnh render 3D giả lập; nguồn ảnh và giấy phép minh bạch.</p></div>
          </div>
        </div>

        <div className="product-accordion-group">
          <details className="product-accordion-item" open>
            <summary>Đặc điểm thiết kế & kỹ thuật chế tác</summary>
            <div className="accordion-content">
              <p>Sản phẩm đại diện cho ngôn ngữ thiết kế tối giản, tinh xảo của thương hiệu Cortis. Từng đường may và chi tiết kết cấu được tinh chỉnh để tôn vinh vóc dáng người mặc trong môi trường đô thị hiện đại.</p>
            </div>
          </details>
          <details className="product-accordion-item">
            <summary>Chính sách giao nhận & Thanh toán COD</summary>
            <div className="accordion-content">
              <p>Giao hàng toàn quốc từ 2–4 ngày làm việc. Miễn phí vận chuyển cho đơn hàng từ 2.000.000 ₫ (phí tiêu chuẩn 30.000 ₫). Thanh toán tiền mặt khi nhận hàng (COD) an toàn tuyệt đối.</p>
            </div>
          </details>
          <details className="product-accordion-item">
            <summary>Hướng dẫn bảo quản sản phẩm</summary>
            <div className="accordion-content">
              <p>Bảo quản nơi khô ráo, tránh ánh nắng trực tiếp thời gian dài. Giặt nhẹ bằng nước lạnh và phơi trong bóng râm để giữ màu sắc và độ bền sợi vải.</p>
            </div>
          </details>
        </div>
        <section className="credit-block" aria-labelledby="product-credit-title">
          <h2 id="product-credit-title">Về bức ảnh</h2>
          <p>Tác giả: {product.image_credit.author}</p>
          <div className="credit-links">
            <a className="text-link" href={product.image_credit.source_page} target="_blank" rel="noopener noreferrer">
              Xem ảnh gốc <ArrowUpRight size={15} aria-hidden="true" />
            </a>
            <a className="text-link" href={product.image_credit.license_url} target="_blank" rel="noopener noreferrer">
              {product.image_credit.license} <ArrowUpRight size={15} aria-hidden="true" />
            </a>
          </div>
          {product.image_credit.transformations.length > 0 && <p>Điều chỉnh ảnh: {product.image_credit.transformations.map(formatTransformation).join('; ')}</p>}
          <Link className="text-link" to="/credits">Nguồn ảnh của bộ sưu tập</Link>
        </section>
      </div>
    </article>}
  </div>
}
