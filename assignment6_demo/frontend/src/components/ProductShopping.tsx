import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Heart, ShoppingBag } from 'lucide-react'
import { ApiError, getCart, getWishlist, saveWishlist, setCartQuantity } from '../lib/api'
import type { ProductDetail } from '../lib/types'
import { ErrorPanel } from '../ui'

export function ProductShopping({ product }: { product: ProductDetail }) {
  const [quantity, setQuantity] = useState(1), [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [notice, setNotice] = useState(''), [auth, setAuth] = useState(false)
  const alive = useRef(true), locked = useRef(false)
  const generation = useRef(0)
  useEffect(() => {
    alive.current = true; const controller = new AbortController()
    const token = ++generation.current
    getWishlist(controller.signal).then(result => { if (!controller.signal.aborted && generation.current === token) setSaved(result.items.some(row => row.product_id === product.product_id)) }).catch(() => { /* Login recovery is shown when a shopper acts. */ })
    return () => { alive.current = false; controller.abort() }
  }, [product.product_id])
  async function action(operation: () => Promise<void>) {
    if (locked.current) return
    generation.current++
    locked.current = true; setBusy(true); setError(''); setNotice(''); setAuth(false)
    try { await operation() } catch (reason) { if (alive.current) { setError(reason instanceof Error ? reason.message : 'Chưa hoàn tất thao tác.'); setAuth(reason instanceof ApiError && reason.status === 401) } }
    finally { locked.current = false; if (alive.current) setBusy(false) }
  }
  return <section className="product-shopping" aria-label="Chọn và lưu sản phẩm">
    <label htmlFor="purchase-quantity">Số lượng<input id="purchase-quantity" type="number" min="1" max={Math.min(99, product.stock_quantity) || 1} step="1" value={quantity} disabled={busy || !product.in_stock} onChange={event => setQuantity(Number(event.target.value))} /></label>
    <div className="shopping-actions"><button className="primary-button" disabled={busy || !product.in_stock} onClick={() => {
      if (!Number.isInteger(quantity) || quantity < 1 || quantity > 99) { setError('Chọn số lượng nguyên từ 1 đến 99.'); return }
      void action(async () => { const current = await getCart(); const old = current.cart.items.find(row => row.product_id === product.product_id)?.quantity ?? 0; await setCartQuantity(product.product_id, old + quantity, current.cart.version); if (alive.current) setNotice('Đã thêm sản phẩm vào giỏ hàng.') })
    }}><ShoppingBag size={17} aria-hidden="true" />{busy ? 'Đang cập nhật…' : product.in_stock ? 'Thêm vào giỏ' : 'Tạm hết hàng'}</button>
      <button className="secondary-button" aria-pressed={saved} disabled={busy} onClick={() => { void action(async () => { const result = await saveWishlist(product.product_id, !saved); if (alive.current) { setSaved(result.items.some(row => row.product_id === product.product_id)); setNotice(saved ? 'Đã bỏ lưu món đồ.' : 'Đã lưu món đồ yêu thích.') } }) }}><Heart size={17} aria-hidden="true" />{saved ? 'Bỏ lưu' : 'Lưu yêu thích'}</button></div>
    {error && <ErrorPanel message={error} />}{auth && <Link className="text-link" to="/account">Đăng nhập để lưu hoặc thêm sản phẩm</Link>}
    {notice && <p role="status" className="account-notice">{notice} <Link className="text-link" to="/cart">Xem giỏ hàng</Link> · <Link className="text-link" to="/wishlist">Xem món đã lưu</Link></p>}
  </section>
}
