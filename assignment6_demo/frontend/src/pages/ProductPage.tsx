import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowUpRight, ChevronRight } from 'lucide-react'
import { ApiError, getProduct } from '../lib/api'
import type { ProductDetail } from '../lib/types'
import { ProductImage, ErrorPanel, formatMoney, categoryLabels } from '../ui'

export function ProductPage() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<{ message: string; missing: boolean } | null>(null)
  const [attempt, setAttempt] = useState(0)

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
      <Link to="/"><ArrowLeft size={16} aria-hidden="true" /> Trở lại bộ sưu tập</Link>
      <ChevronRight size={14} aria-hidden="true" />
      <span aria-current="page">Chi tiết sản phẩm</span>
    </nav>
    {loading && <div className="page-loading" role="status">Đang tải sản phẩm…</div>}
    {error && <ErrorPanel title={error.missing ? 'Không tìm thấy sản phẩm' : 'Chưa tải được sản phẩm'}
      message={error.message} onRetry={() => setAttempt(value => value + 1)} />}
    {!loading && product && <article className="detail-layout">
      <div className="detail-image"><ProductImage src={product.image_url} alt={product.name} /></div>
      <div className="detail-copy">
        <h1>{product.name}</h1>
        <p className="detail-description">{product.description}</p>
        <p className="detail-price">{formatMoney(product.price_vnd)}</p>
        <p className="stock-status"><span className={`status-label ${product.in_stock ? 'in-stock' : 'out-of-stock'}`}>
          {product.in_stock ? `Còn hàng · ${product.stock_quantity} sản phẩm` : 'Tạm hết hàng'}
        </span></p>
        <dl className="detail-metadata">
          <div><dt>Thương hiệu</dt><dd>{product.brand}</dd></div>
          <div><dt>Danh mục</dt><dd>{categoryLabels[product.category]}</dd></div>
          <div><dt>Màu sắc</dt><dd>{product.color}</dd></div>
          <div><dt>Mã sản phẩm</dt><dd>{product.product_id}</dd></div>
        </dl>
        <p className="demo-note">Giá và tồn kho là dữ liệu minh họa.</p>
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
          {product.image_credit.transformations.length > 0 && <p>Điều chỉnh ảnh: {product.image_credit.transformations.join('; ')}.</p>}
          <Link className="text-link" to="/credits">Nguồn ảnh của bộ sưu tập</Link>
        </section>
      </div>
    </article>}
  </div>
}
