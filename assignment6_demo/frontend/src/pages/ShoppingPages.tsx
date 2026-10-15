import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Heart, ShoppingBag, Trash2 } from 'lucide-react'
import { ApiError, getCart, getProduct, getWishlist, saveWishlist, setCartQuantity } from '../lib/api'
import type { Cart, WishlistResponse } from '../lib/types'
import { ErrorPanel, ProductImage, formatMoney } from '../ui'

const issues = { VARIANT_REQUIRED: 'Hãy xóa dòng này và mở sản phẩm để chọn kích cỡ.', PRODUCT_UNAVAILABLE: 'Sản phẩm không còn trong danh mục. Hãy xóa khỏi giỏ.', OUT_OF_STOCK: 'Sản phẩm đã hết hàng. Hãy xóa hoặc quay lại sau.', INSUFFICIENT_STOCK: 'Tồn kho hiện tại thấp hơn số lượng đã chọn. Hãy giảm số lượng.' }

export function CartPage() {
  const [cart, setCart] = useState<Cart | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [authRequired, setAuthRequired] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const alive = useRef(true), locked = useRef(false)
  useEffect(() => {
    alive.current = true
    const controller = new AbortController()
    setLoading(true); setError(''); setCart(null); setAuthRequired(false)
    getCart(controller.signal).then(result => { if (!controller.signal.aborted) setCart(result.cart) })
      .catch(reason => { if (!controller.signal.aborted) { setError(reason instanceof Error ? reason.message : 'Chưa tải được giỏ hàng.'); setAuthRequired(reason instanceof ApiError && reason.status === 401) } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => { alive.current = false; controller.abort() }
  }, [attempt])
  async function change(productId: string, quantity: number, variantId?: string) {
    if (!cart || locked.current) return
    locked.current = true; setBusy(true); setError(''); setNotice('')
    try {
      const result = await setCartQuantity(productId, quantity, cart.version, variantId)
      if (alive.current) { setCart(result.cart); setNotice(quantity ? 'Đã cập nhật số lượng.' : 'Đã xóa sản phẩm khỏi giỏ.') }
    } catch (reason) {
      if (alive.current) {
        setError(reason instanceof Error ? reason.message : 'Chưa cập nhật được giỏ hàng.')
        if (reason instanceof ApiError && reason.status === 401) { setCart(null); setAuthRequired(true) }
        if (reason instanceof ApiError && reason.code === 'CART_CHANGED') {
          try { const fresh = await getCart(); if (alive.current) setCart(fresh.cart) } catch { /* Explicit retry remains available. */ }
        }
      }
    } finally { locked.current = false; if (alive.current) setBusy(false) }
  }
  function submit(event: FormEvent<HTMLFormElement>, productId: string, variantId?: string) {
    event.preventDefault(); const quantity = Number(new FormData(event.currentTarget).get('quantity'))
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > 99) { setError('Chọn số lượng nguyên từ 1 đến 99.'); return }
    void change(productId, quantity, variantId)
  }
  return <div className="page-shell shopping-page" aria-busy={busy || loading}><header className="page-heading"><h1>Giỏ hàng của bạn.</h1><p>Kiểm tra món đồ và số lượng trước khi đặt hàng.</p></header>
    {loading && <p role="status">Đang tải giỏ hàng…</p>}
    {error && <ErrorPanel message={error} onRetry={busy ? undefined : () => setAttempt(value => value + 1)} />}
    {authRequired && <Link className="primary-button" to="/account">Đăng nhập để xem giỏ hàng</Link>}
    {notice && <p role="status" className="account-notice">{notice}</p>}
    {!loading && cart && (cart.items.length === 0 ? <section className="empty-state"><ShoppingBag size={32} aria-hidden="true" /><h2>Giỏ hàng đang trống</h2><p>Khám phá bộ sưu tập hoặc chọn từ danh sách yêu thích.</p><Link className="primary-button" to="/catalog">Khám phá bộ sưu tập</Link><Link className="text-link" to="/wishlist">Xem món đã lưu</Link></section> : <div className="shopping-layout">
      <section aria-label="Sản phẩm trong giỏ" className="shopping-list">{cart.items.map(item => <article key={`${item.variant_id ?? item.product_id}:${cart.version}`} className="shopping-row" data-testid="cart-item">
        {item.product && <Link className="shopping-photo" to={`/products/${item.product_id}`}><ProductImage src={item.product.image_url} alt={item.product.name} /></Link>}
        <div className="shopping-copy"><h2>{item.product ? <Link to={`/products/${item.product_id}`}>{item.product.name}</Link> : `Sản phẩm ${item.product_id} không còn khả dụng`}</h2><p>{item.product?.color}{item.size ? ` · ${item.size}` : ''}</p><p>{formatMoney(item.unit_price_vnd)} / sản phẩm</p>{item.issue && <p className="field-error" role="status">{issues[item.issue]}</p>}
          <form className="cart-quantity" onSubmit={event => submit(event, item.product_id, item.variant_id)}><label htmlFor={`quantity-${item.variant_id ?? item.product_id}`}>Số lượng<input id={`quantity-${item.variant_id ?? item.product_id}`} name="quantity" type="number" min="1" max="99" step="1" defaultValue={item.quantity} required disabled={busy || !item.product} /></label><button className="secondary-button" type="submit" disabled={busy || !item.product}>Cập nhật</button><button className="text-link" type="button" disabled={busy} onClick={() => { void change(item.product_id, 0, item.variant_id) }}><Trash2 size={16} aria-hidden="true" />Xóa<span className="visually-hidden"> {item.product?.name ?? item.product_id}</span></button></form>
        </div><strong className="shopping-line-total">{formatMoney(item.line_total_vnd)}</strong>
      </article>)}</section>
      <aside className="shopping-summary"><h2>Tạm tính</h2><p>{cart.item_count} sản phẩm</p><strong>{formatMoney(cart.subtotal_vnd)}</strong><p>Giá và tồn kho là dữ liệu demo. Giỏ hàng chưa giữ hàng; giá và tồn kho được kiểm tra lại khi đặt đơn.</p>{cart.has_issues ? <p>Hãy xử lý các sản phẩm không còn đủ hàng trước khi đặt đơn.</p> : <Link className="primary-button" to="/checkout">Tiếp tục đặt hàng</Link>}<Link className="secondary-button" to="/catalog">Tiếp tục chọn sản phẩm</Link></aside>
    </div>)}
  </div>
}

export function WishlistPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<WishlistResponse | null>(null)
  const [error, setError] = useState(''), [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(false), [authRequired, setAuthRequired] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const alive = useRef(true), locked = useRef(false)
  useEffect(() => {
    alive.current = true; const controller = new AbortController()
    setData(null); setError(''); setLoading(true); setAuthRequired(false)
    getWishlist(controller.signal).then(result => { if (!controller.signal.aborted) setData(result) })
      .catch(reason => { if (!controller.signal.aborted) { setError(reason instanceof Error ? reason.message : 'Chưa tải được danh sách.'); setAuthRequired(reason instanceof ApiError && reason.status === 401) } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => { alive.current = false; controller.abort() }
  }, [attempt])
  async function action(operation: () => Promise<void>) {
    if (locked.current) return
    locked.current = true; setBusy(true); setError(''); setNotice('')
    try { await operation() } catch (reason) { if (alive.current) { setError(reason instanceof Error ? reason.message : 'Chưa hoàn tất thao tác.'); if (reason instanceof ApiError && reason.status === 401) { setData(null); setAuthRequired(true) } } }
    finally { locked.current = false; if (alive.current) setBusy(false) }
  }
  return <div className="page-shell shopping-page" aria-busy={busy || loading}><header className="page-heading"><h1>Món đồ đã lưu.</h1><p>Giữ những món bạn thích để quay lại lựa chọn.</p></header>
    {loading && <p role="status">Đang tải món đã lưu…</p>}{error && <ErrorPanel message={error} onRetry={busy ? undefined : () => setAttempt(value => value + 1)} />}{authRequired && <Link className="primary-button" to="/account">Đăng nhập để xem món đã lưu</Link>}{notice && <p role="status" className="account-notice">{notice} <Link to="/cart">Xem giỏ hàng</Link></p>}
    {!loading && data && (data.total === 0 ? <section className="empty-state"><Heart size={32} aria-hidden="true" /><h2>Bạn chưa lưu món đồ nào</h2><p>Mở chi tiết sản phẩm và bấm lưu để thêm vào danh sách.</p><Link className="primary-button" to="/catalog">Khám phá bộ sưu tập</Link></section> : <section className="shopping-list" aria-label="Danh sách yêu thích">{data.items.map(item => <article className="shopping-row" key={item.product_id} data-testid="wishlist-item">
      {item.product && <Link className="shopping-photo" to={`/products/${item.product_id}`}><ProductImage src={item.product.image_url} alt={item.product.name} /></Link>}
      <div className="shopping-copy"><h2>{item.product ? <Link to={`/products/${item.product_id}`}>{item.product.name}</Link> : `Sản phẩm ${item.product_id} không còn khả dụng`}</h2><p>{item.product?.color}</p>{item.product && <strong>{formatMoney(item.product.price_vnd)}</strong>}
        <div className="shopping-actions"><button className="primary-button" disabled={busy || !item.product?.in_stock} onClick={() => { void action(async () => {
          const detail = await getProduct(item.product_id)
          if (detail.product.variants?.some(v => v.size != null)) { if (alive.current) navigate(`/products/${item.product_id}`); return }
          const current = await getCart(); const old = current.cart.items.find(row => row.product_id === item.product_id)?.quantity ?? 0
          await setCartQuantity(item.product_id, old + 1, current.cart.version)
          if (alive.current) setNotice('Đã thêm một sản phẩm vào giỏ. Món đồ vẫn được giữ trong danh sách yêu thích.')
        }) }}><ShoppingBag size={16} aria-hidden="true" />{item.product?.in_stock ? 'Thêm vào giỏ' : 'Tạm hết hàng'}</button>
        <button className="secondary-button" disabled={busy} onClick={() => { void action(async () => { const result = await saveWishlist(item.product_id, false); if (alive.current) { setData(result); setNotice('Đã bỏ lưu món đồ.') } }) }}>Bỏ lưu<span className="visually-hidden"> {item.product?.name ?? item.product_id}</span></button></div>
      </div>
    </article>)}</section>)}
  </div>
}
