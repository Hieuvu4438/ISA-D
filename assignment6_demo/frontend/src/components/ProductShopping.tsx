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
  const sized = product.variants?.some(v => v.size != null) ?? false
  const [sku, setSku] = useState(sized ? '' : product.product_id)
  const selected = product.variants?.find(v => v.variant_id === sku)
  const available = selected?.stock_quantity ?? (sized ? 0 : product.stock_quantity)
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
    {sized && <><label htmlFor="purchase-size">Kích cỡ<select id="purchase-size" aria-label="Kích cỡ" value={sku} disabled={busy} onChange={event => { setSku(event.target.value); setQuantity(1); setNotice(''); setError('') }}><option value="">Chọn kích cỡ</option>{product.variants?.map(v => <option value={v.variant_id} key={v.variant_id} disabled={!v.in_stock}>{v.size} · {v.in_stock ? `còn ${v.stock_quantity}` : 'hết hàng'}</option>)}</select></label><p className="demo-note">Kích cỡ và tồn kho minh họa, chưa có số đo để tư vấn độ vừa vặn.</p></>}
    <label htmlFor="purchase-quantity">Số lượng<input id="purchase-quantity" type="number" min="1" max={Math.min(99, available) || 1} step="1" value={quantity} disabled={busy || !available} onChange={event => setQuantity(Number(event.target.value))} /></label>
    <div className="shopping-actions"><button className="primary-button" disabled={busy || !product.in_stock || (sized && !sku)} onClick={() => {
      if (!Number.isInteger(quantity) || quantity < 1 || quantity > 99) { setError('Chọn số lượng nguyên từ 1 đến 99.'); return }
      void action(async () => { const current = await getCart(); const old = current.cart.items.find(row => (row.variant_id ?? row.product_id) === sku)?.quantity ?? 0; await setCartQuantity(product.product_id, old + quantity, current.cart.version, sku); if (alive.current) setNotice('Đã thêm sản phẩm vào giỏ hàng.') })
    }}><ShoppingBag size={17} aria-hidden="true" />{busy ? 'Đang cập nhật…' : product.in_stock ? 'Thêm vào giỏ' : 'Tạm hết hàng'}</button>
      <button className="secondary-button" aria-pressed={saved} disabled={busy} onClick={() => { void action(async () => { const result = await saveWishlist(product.product_id, !saved); if (alive.current) { setSaved(result.items.some(row => row.product_id === product.product_id)); setNotice(saved ? 'Đã bỏ lưu món đồ.' : 'Đã lưu món đồ yêu thích.') } }) }}><Heart size={17} aria-hidden="true" />{saved ? 'Bỏ lưu' : 'Lưu yêu thích'}</button></div>
    {error && <ErrorPanel message={error} />}{auth && <Link className="text-link" to="/account">Đăng nhập để lưu hoặc thêm sản phẩm</Link>}
    {notice && <p role="status" className="account-notice">{notice} <Link className="text-link" to="/cart">Xem giỏ hàng</Link> · <Link className="text-link" to="/wishlist">Xem món đã lưu</Link></p>}
  </section>
}
