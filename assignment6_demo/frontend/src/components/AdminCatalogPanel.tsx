import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError, changeProductSaleState, discardProductDraft, getAdminProducts, getProductDraft, preflightProductDraft, publishProductDraft, saveProductDraft, uploadDraftPhoto } from '../lib/api'
import type { AdminProductList, Category, DraftMetadata, PhotoProvenance, ProductDraft } from '../lib/types'
import { categoryLabels, ErrorPanel, formatMoney, ProductImage } from '../ui'

const emptyProduct = (): DraftMetadata => ({ name: '', brand: 'Không xác định', category: 't_shirt', color: '', price_vnd: 0, description: '' })

export function AdminCatalogPanel() {
  const [list, setList] = useState<AdminProductList | null>(null), [offset, setOffset] = useState(0), [generation, setGeneration] = useState(0)
  const [query, setQuery] = useState(''), [filter, setFilter] = useState(''), [status, setStatus] = useState(''), [newId, setNewId] = useState('')
  const [draft, setDraft] = useState<ProductDraft | null>(null), [product, setProduct] = useState<DraftMetadata>(emptyProduct)
  const [loading, setLoading] = useState(true), [opening, setOpening] = useState(false), [busy, setBusy] = useState(false), [dirty, setDirty] = useState(false)
  const [error, setError] = useState(''), [notice, setNotice] = useState(''), [conflict, setConflict] = useState(false), [pendingId, setPendingId] = useState(''), [confirmDiscard, setConfirmDiscard] = useState(false), [confirmPublish, setConfirmPublish] = useState(false)
  const alive = useRef(true), locked = useRef(false), readSequence = useRef(0), detailAbort = useRef<AbortController | null>(null)
  const editor = useRef<HTMLElement | null>(null)
  const [confirmSaleState, setConfirmSaleState] = useState(false), [saleReason, setSaleReason] = useState('')
  useEffect(() => {
    alive.current = true
    return () => { alive.current = false; detailAbort.current?.abort() }
  }, [])
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setList(null); setError('')
    const params = new URLSearchParams({ offset: String(offset), limit: '20' })
    if (filter) params.set('q', filter); if (status) params.set('status', status)
    getAdminProducts(params, controller.signal).then(result => { if (!controller.signal.aborted) setList(result) })
      .catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Chưa tải được sản phẩm.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [offset, filter, status, generation])
  useEffect(() => {
    if (!dirty) return
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])
  async function open(id: string, abandon = false) {
    if (locked.current) return
    if (dirty && !abandon) { setPendingId(id); return }
    detailAbort.current?.abort(); const controller = new AbortController(); detailAbort.current = controller
    const token = ++readSequence.current; setOpening(true); setError(''); setNotice(''); setConflict(false); setConfirmDiscard(false); setPendingId('')
    try {
      const result = await getProductDraft(id, controller.signal)
      if (!controller.signal.aborted && token === readSequence.current) {
        setDraft(result.draft); setProduct(result.draft.product ?? emptyProduct()); setDirty(false); setConfirmPublish(false); setConfirmSaleState(false); setSaleReason('')
        editor.current?.scrollIntoView({ block: 'start' })
      }
    } catch (reason) { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Chưa mở được bản nháp.') }
    finally { if (!controller.signal.aborted && token === readSequence.current) setOpening(false) }
  }
  function change<K extends keyof DraftMetadata>(key: K, value: DraftMetadata[K]) { setProduct(current => ({ ...current, [key]: value })); setDirty(true); setNotice(''); setConfirmDiscard(false) }
  async function action(operation: () => Promise<{ draft: ProductDraft }>, success: string) {
    if (locked.current) return
    locked.current = true; setBusy(true); setError(''); setNotice(''); setConflict(false)
    try {
      const result = await operation()
      if (alive.current) { setDraft(result.draft); setProduct(result.draft.product ?? emptyProduct()); setDirty(false); setConfirmDiscard(false); setConfirmPublish(false); setConfirmSaleState(false); setSaleReason(''); setNotice(success); setGeneration(value => value + 1) }
    } catch (reason) {
      if (alive.current) {
        setError(reason instanceof Error ? reason.message : 'Chưa xác nhận được thao tác. Hãy tải lại bản nháp để kiểm tra trước khi gửi tiếp.')
        setConflict(reason instanceof ApiError && (reason.status === 409 || reason.status === 0 || reason.status >= 500))
        if (reason instanceof ApiError && [401, 403].includes(reason.status)) { setDraft(null); setList(null); setDirty(false) }
      }
    } finally { locked.current = false; if (alive.current) setBusy(false) }
  }
  function save(event: FormEvent) {
    event.preventDefault(); if (!draft) return
    if (!Number.isInteger(product.price_vnd) || product.price_vnd < 0 || product.price_vnd > 1_000_000_000) { setError('Giá VND cần số nguyên từ 0 đến 1.000.000.000.'); return }
    void action(() => saveProductDraft(draft.product_id, draft.version, draft.base_catalog_fingerprint, product), 'Đã lưu bản nháp. Cửa hàng chưa thay đổi.')
  }
  function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!draft || dirty) return
    const fields = new FormData(event.currentTarget), file = fields.get('image')
    if (!(file instanceof File) || file.size === 0 || file.size > 5 * 1024 * 1024) { setError('Chọn ảnh JPEG, PNG hoặc WebP tối đa 5 MiB.'); return }
    const provenance: PhotoProvenance = { source_page: String(fields.get('source_page')), original_url: String(fields.get('original_url')), download_url: String(fields.get('download_url')), transformations: String(fields.get('transformations')), author: String(fields.get('author')), license: String(fields.get('license')), license_url: String(fields.get('license_url')), retrieved_at: String(fields.get('retrieved_at')), real_photo_review: 'passed' }
    void action(() => uploadDraftPhoto(draft.product_id, draft.version, file, provenance), 'Đã lưu ảnh và nguồn cho bản nháp. Ảnh cửa hàng chưa thay đổi.')
  }
  return <section className="admin-catalog" aria-label="Soạn thảo sản phẩm" aria-busy={loading || opening || busy}>
    <h2>Sản phẩm và bản nháp.</h2><p className="catalog-authoring-note">Soạn nội dung và ảnh trong bản nháp. Chọn xuất bản khi đã kiểm tra để cập nhật đồng thời cửa hàng và tìm kiếm.</p>
    <div className="admin-toolbar"><form onSubmit={event => { event.preventDefault(); setFilter(query.trim()); setOffset(0) }}><label htmlFor="catalog-admin-query">Tìm mã, tên hoặc thương hiệu</label><div className="admin-search-row"><input id="catalog-admin-query" value={query} maxLength={120} onChange={event => setQuery(event.target.value)} /><button className="secondary-button" disabled={busy}>Tìm sản phẩm</button></div></form><div><label htmlFor="catalog-admin-status">Phạm vi danh sách</label><select id="catalog-admin-status" value={status} disabled={busy} onChange={event => { setStatus(event.target.value); setOffset(0) }}><option value="">Tất cả</option><option value="draft">Có bản nháp</option><option value="active">Đang mở bán</option><option value="archived">Đang ngừng bán</option><option value="live">Có trên cửa hàng</option></select></div></div>
    <form className="admin-create-product" onSubmit={event => { event.preventDefault(); if (/^P[0-9]{3}$/.test(newId)) void open(newId); else setError('Mã sản phẩm có dạng P181.') }}><label htmlFor="catalog-new-id">Mã sản phẩm cần tạo hoặc mở</label><div className="admin-search-row"><input id="catalog-new-id" value={newId} maxLength={4} pattern="P[0-9]{3}" required placeholder="Ví dụ: P181" onChange={event => setNewId(event.target.value.toUpperCase())} disabled={busy} /><button className="secondary-button" disabled={busy || opening}>Mở mã sản phẩm</button></div></form>
    {loading && <p role="status">Đang tải danh sách sản phẩm…</p>}
    {list && !loading && <><p role="status">{list.total} sản phẩm</p>{list.items.length ? <div className="admin-records">{list.items.map(item => <article className="admin-record" key={item.product_id}><div><h3>{item.name}</h3><p>{item.product_id} · {categoryLabels[item.category]} · {formatMoney(item.price_vnd)}</p><p>{item.has_draft ? 'Có bản nháp' : 'Chưa có bản nháp'} · {item.is_new ? 'Sản phẩm mới, chưa có trên cửa hàng' : item.sale_state === 'archived' ? 'Đang tạm ngừng bán' : 'Đã có trên cửa hàng'}</p></div><button className="secondary-button" disabled={busy || opening} onClick={() => { void open(item.product_id) }}>Soạn {item.product_id}</button></article>)}</div> : <p>Chưa có sản phẩm trong trang này. Thay bộ lọc hoặc về trang đầu.</p>}<nav className="browse-pagination" aria-label="Phân trang sản phẩm quản trị"><button className="secondary-button" disabled={busy || offset === 0} onClick={() => setOffset(value => Math.max(0, value - 20))}>Trang trước</button><span>Trang {Math.floor(offset / 20) + 1} / {Math.max(1, Math.ceil(list.total / 20))}</span><button className="secondary-button" disabled={busy || offset + 20 >= list.total} onClick={() => setOffset(value => value + 20)}>Trang sau</button></nav></>}
    {error && <ErrorPanel message={error} />}{notice && <p role="status" className="account-notice">{notice}</p>}
    {pendingId && <div className="draft-navigation-warning" role="alert"><p>Nội dung đang sửa chưa được lưu. Mở {pendingId} sẽ bỏ thay đổi chưa lưu.</p><div className="shopping-actions"><button className="secondary-button" onClick={() => setPendingId('')}>Tiếp tục chỉnh sửa</button><button className="secondary-button" onClick={() => { void open(pendingId, true) }}>Bỏ thay đổi và mở {pendingId}</button></div></div>}
    {conflict && draft && <button className="secondary-button" disabled={busy} onClick={() => { void open(draft.product_id, true) }}>Tải lại bản trên server, bỏ nội dung đang sửa</button>}
    {opening && <p role="status">Đang mở sản phẩm…</p>}
    <section ref={editor} className="catalog-draft-editor" aria-label="Nội dung bản nháp">{draft && !opening && <>
      <h2>Soạn {draft.product_id}.</h2><p>{draft.has_draft ? `Bản nháp đã lưu · phiên bản ${draft.version}` : draft.is_new ? 'Sản phẩm mới · chưa lưu bản nháp' : 'Nội dung đã xuất bản · chưa có bản nháp'}{dirty ? ' · Có thay đổi chưa lưu' : ''}</p>
      {!draft.is_new && <section className="catalog-preflight" aria-label="Trạng thái bán"><h3>Trạng thái bán</h3><p>{draft.sale_state === 'archived' ? 'Đang tạm ngừng bán. Sản phẩm được ẩn khỏi tìm kiếm và không thể đặt mua.' : 'Đang mở bán trên cửa hàng.'} Tồn kho, ảnh và lịch sử đơn hàng được giữ lại.</p><button className="secondary-button" disabled={busy || dirty || draft.inventory_revision == null} onClick={() => setConfirmSaleState(true)}>{draft.sale_state === 'archived' ? 'Mở bán lại sản phẩm' : 'Tạm ngừng bán sản phẩm'}</button>{dirty && <p>Lưu hoặc bỏ thay đổi nội dung trước khi đổi trạng thái bán.</p>}{confirmSaleState && <form className="draft-navigation-warning" onSubmit={event => { event.preventDefault(); if (draft.inventory_revision == null || dirty) return; const target = draft.sale_state === 'archived' ? 'active' : 'archived'; void action(async () => { await changeProductSaleState(draft.product_id, target, draft.inventory_revision!, saleReason); return getProductDraft(draft.product_id) }, target === 'archived' ? 'Đã tạm ngừng bán. Tải lại cửa hàng để cập nhật trạng thái.' : 'Đã mở bán lại. Sản phẩm có thể mua khi còn hàng.') }}><label htmlFor="product-sale-reason">Lý do đổi trạng thái bán</label><input id="product-sale-reason" value={saleReason} required minLength={3} maxLength={200} disabled={busy} onChange={event => setSaleReason(event.target.value)} /><p>{draft.sale_state === 'archived' ? 'Mở bán lại với tồn kho hiện tại?' : 'Tạm ngừng bán ngay cả khi sản phẩm còn hàng?'}</p><div className="shopping-actions"><button className="primary-button" disabled={busy || dirty}>{draft.sale_state === 'archived' ? 'Xác nhận mở bán lại' : 'Xác nhận ngừng bán'}</button><button type="button" className="secondary-button" disabled={busy} onClick={() => setConfirmSaleState(false)}>Giữ trạng thái hiện tại</button></div></form>}</section>}
      <div className="catalog-draft-layout"><form className="catalog-metadata-form" onSubmit={save}><fieldset disabled={busy}><legend>Thông tin sản phẩm</legend>
        <label htmlFor="draft-name">Tên sản phẩm</label><input id="draft-name" value={product.name} required maxLength={120} onChange={event => change('name', event.target.value)} />
        <div className="catalog-field-pair"><div><label htmlFor="draft-brand">Thương hiệu</label><input id="draft-brand" value={product.brand} required maxLength={120} onChange={event => change('brand', event.target.value)} /></div><div><label htmlFor="draft-category">Danh mục</label><select id="draft-category" value={product.category} onChange={event => change('category', event.target.value as Category)}>{Object.entries(categoryLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></div></div>
        <div className="catalog-field-pair"><div><label htmlFor="draft-color">Màu sắc theo ảnh</label><input id="draft-color" value={product.color} required maxLength={120} onChange={event => change('color', event.target.value)} /></div><div><label htmlFor="draft-price">Giá minh họa (VND)</label><input id="draft-price" type="number" value={product.price_vnd} min="0" max="1000000000" step="1" required onChange={event => change('price_vnd', Number(event.target.value))} /></div></div>
        <label htmlFor="draft-description">Mô tả theo ảnh và nguồn</label><textarea id="draft-description" value={product.description} required maxLength={500} onChange={event => change('description', event.target.value)} />
        <p>Không suy đoán thương hiệu, chất liệu hoặc tính năng chưa có căn cứ. Quản lý tồn kho và kích cỡ tại mục Tồn kho.</p><div className="shopping-actions"><button className="primary-button" disabled={busy || (!dirty && draft.has_draft)}>Lưu bản nháp</button>{dirty && <button type="button" className="secondary-button" onClick={() => { setProduct(draft.product ?? emptyProduct()); setDirty(false) }}>Bỏ thay đổi chưa lưu</button>}</div>
      </fieldset></form><div className="catalog-photo-preview"><h3>Ảnh của bản nháp</h3>{draft.image_url ? <ProductImage src={draft.image_url} alt={product.name || `Ảnh bản nháp ${draft.product_id}`} eager /> : <p>Chưa có ảnh. Lưu nội dung trước rồi tải ảnh chụp thật kèm nguồn.</p>}{draft.image && <p>{draft.image.author} · <a className="text-link" href={draft.image.source_page} target="_blank" rel="noopener noreferrer">Nguồn ảnh</a> · <a className="text-link" href={draft.image.license_url} target="_blank" rel="noopener noreferrer">{draft.image.license}</a></p>}</div></div>
      <details className="catalog-photo-form"><summary>Thay ảnh và ghi nguồn</summary><p>Chỉ dùng ảnh chụp thật từ mạng, có quyền sử dụng. Kiểm tra ảnh khớp sản phẩm; mỗi mã mới cần ảnh riêng. Tệp tải lên không tự thay ảnh cửa hàng.</p><form key={`${draft.product_id}:${draft.version}`} onSubmit={upload}><fieldset disabled={busy || !draft.has_draft || dirty}><legend>Ảnh và thông tin nguồn</legend><label htmlFor="draft-image">Ảnh JPEG, PNG hoặc WebP · tối đa 5 MiB</label><input id="draft-image" name="image" type="file" accept="image/jpeg,image/png,image/webp" required />
        <label htmlFor="photo-source">Trang nguồn</label><input id="photo-source" name="source_page" type="url" required maxLength={2000} defaultValue={draft.image?.source_page ?? ''} placeholder="https://…" />
        <label htmlFor="photo-original">URL ảnh gốc</label><input id="photo-original" name="original_url" type="url" required maxLength={2000} defaultValue={draft.image?.original_url ?? ''} placeholder="https://…" />
        <label htmlFor="photo-download">URL đã tải ảnh</label><input id="photo-download" name="download_url" type="url" required maxLength={2000} defaultValue={draft.image?.download_url ?? ''} placeholder="https://…" />
        <label htmlFor="photo-transformations">Thay đổi so với ảnh gốc</label><input id="photo-transformations" name="transformations" required maxLength={500} defaultValue={draft.image?.transformations ?? ''} placeholder="Ví dụ: Ảnh thu nhỏ từ nguồn, không chỉnh sửa tại máy" />
        <div className="catalog-field-pair"><div><label htmlFor="photo-author">Tác giả ảnh</label><input id="photo-author" name="author" required maxLength={200} defaultValue={draft.image?.author ?? ''} /></div><div><label htmlFor="photo-license">Giấy phép</label><input id="photo-license" name="license" required maxLength={120} defaultValue={draft.image?.license ?? ''} /></div></div>
        <label htmlFor="photo-license-url">Trang giấy phép</label><input id="photo-license-url" name="license_url" type="url" required maxLength={2000} defaultValue={draft.image?.license_url ?? ''} />
        <label htmlFor="photo-retrieved">Ngày lấy ảnh</label><input id="photo-retrieved" name="retrieved_at" type="date" required defaultValue={draft.image?.retrieved_at ?? ''} />
        <label className="checkbox-label"><input type="checkbox" required />Tôi đã xem ảnh, xác nhận là ảnh chụp thật, khớp sản phẩm và đã kiểm tra quyền sử dụng.</label><button className="secondary-button">Lưu ảnh cho bản nháp</button></fieldset></form>{(!draft.has_draft || dirty) && <p>Lưu nội dung sản phẩm trước khi tải ảnh.</p>}</details>
      <section className="catalog-preflight" aria-label="Kiểm tra bản nháp"><h3>Kiểm tra trước khi xuất bản</h3><p>Kiểm tra ảnh và khả năng mã hóa dữ liệu bằng model CPU. Sản phẩm mới được xuất bản với tồn kho 0; điều chỉnh số lượng tại Tồn kho sau đó.</p>{draft.validation && !dirty && <p role="status">Đã kiểm tra encoder CPU lúc {new Date(draft.validation.checked_at).toLocaleString('vi-VN')} · chưa xuất bản.</p>}<div className="shopping-actions"><button className="secondary-button" disabled={busy || dirty || !draft.has_draft || !draft.image} onClick={() => { void action(() => preflightProductDraft(draft.product_id, draft.version), 'Kiểm tra hoàn tất. Bản nháp chưa được xuất bản.') }}>Kiểm tra dữ liệu và ảnh</button><button className="primary-button" disabled={busy || dirty || !draft.has_draft || !draft.image} onClick={() => setConfirmPublish(true)}>Xuất bản sản phẩm</button><button className="text-link" disabled={busy || !draft.has_draft} onClick={() => setConfirmDiscard(true)}>Xóa bản nháp đã lưu</button></div>
        {confirmPublish && <div className="draft-navigation-warning"><p>Xuất bản {draft.product_id} lên cửa hàng local? Tên, giá, ảnh và tìm kiếm sẽ đổi cùng nhau. Ngưỡng lọc mức liên quan cần hiệu chỉnh lại sau khi đổi catalog; tìm gần nhất vẫn hoạt động.</p><div className="shopping-actions"><button className="primary-button" disabled={busy || dirty} onClick={() => { void action(() => publishProductDraft(draft.product_id, draft.version), 'Đã xuất bản sản phẩm và chỉ mục tìm kiếm. Hãy tải lại trang cửa hàng để xem dữ liệu mới.') }}>{busy ? 'Đang chuẩn bị chỉ mục…' : 'Xác nhận xuất bản'}</button><button className="secondary-button" disabled={busy} onClick={() => setConfirmPublish(false)}>Tiếp tục soạn</button></div></div>}
        {confirmDiscard && <div className="draft-navigation-warning"><p>Xóa bản nháp {draft.product_id}? Nội dung trên cửa hàng được giữ nguyên.</p><div className="shopping-actions"><button className="secondary-button" disabled={busy} onClick={() => { void action(() => discardProductDraft(draft.product_id, draft.version), 'Đã xóa bản nháp. Cửa hàng được giữ nguyên.') }}>Xác nhận xóa bản nháp</button><button className="secondary-button" disabled={busy} onClick={() => setConfirmDiscard(false)}>Giữ bản nháp</button></div></div>}
      </section>
    </>}</section>
  </section>
}
