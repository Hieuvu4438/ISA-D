import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'
import { ApiError, getCredits } from '../lib/api'
import type { Credit } from '../lib/types'
import { ErrorPanel, ProductImage } from '../ui'

export function CreditsPage() {
  const [credits, setCredits] = useState<Credit[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    getCredits(controller.signal).then(result => {
      if (!controller.signal.aborted) setCredits(result.credits)
    }).catch(reason => {
      if (!controller.signal.aborted) setError(reason instanceof ApiError ? reason.message : 'Chưa tải được nguồn ảnh. Vui lòng thử lại.')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [attempt])

  return <div className="page-shell">
    <header className="page-heading">
      <h1>Mỗi bức ảnh, một nguồn gốc.</h1>
      <p>Ảnh chụp sản phẩm trong bộ sưu tập, cùng tác giả, nguồn và giấy phép sử dụng.</p>
    </header>
    {loading && <p className="page-loading" role="status">Đang tải nguồn ảnh…</p>}
    {error && <ErrorPanel title="Chưa tải được nguồn ảnh" message={error} onRetry={() => setAttempt(value => value + 1)} />}
    {!loading && !error && credits.length === 0 && <p className="empty-state">Bộ sưu tập chưa có ảnh để ghi nhận nguồn.</p>}
    {!loading && !error && <ul className="credit-list">{credits.map(credit => <li className="credit-item" key={`${credit.asset_id}-${credit.product_id}`}>
      <div className="credit-image">
        <ProductImage src={`/api/v1/media/products/${credit.product_id}`} alt={`Ảnh sản phẩm ${credit.product_id}`} />
      </div>
      <div className="credit-copy">
        <h2><Link to={`/products/${credit.product_id}`}>Sản phẩm {credit.product_id}</Link></h2>
        <p>Tác giả: {credit.author}</p>
        <div className="credit-links">
          <a className="text-link" href={credit.source_page} target="_blank" rel="noopener noreferrer">Nguồn ảnh <ArrowUpRight size={15} aria-hidden="true" /></a>
          <a className="text-link" href={credit.license_url} target="_blank" rel="noopener noreferrer">{credit.license} <ArrowUpRight size={15} aria-hidden="true" /></a>
        </div>
        {credit.transformations.length > 0 && <p>Điều chỉnh: {credit.transformations.join('; ')}.</p>}
      </div>
    </li>)}</ul>}
  </div>
}
