import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Search, SlidersHorizontal, X } from 'lucide-react'
import { getCatalogPage, getSuggestions } from '../lib/api'
import type { BrowseResponse, Category, ProductSummary } from '../lib/types'
import { categoryLabels, ErrorPanel } from '../ui'
import { ProductCard } from './SearchPage'

export function BrowsePage() {
  const [params, setParams] = useSearchParams()
  const key = params.toString()
  const [data, setData] = useState<BrowseResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [query, setQuery] = useState(params.get('q') ?? '')
  const [suggestions, setSuggestions] = useState<ProductSummary[]>([])
  const [selected, setSelected] = useState(-1)
  const [focused, setFocused] = useState(false)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const navigate = useNavigate()
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError(''); setQuery(new URLSearchParams(key).get('q') ?? '')
    getCatalogPage(new URLSearchParams(key), controller.signal).then(result => {
      if (!controller.signal.aborted) setData(result)
    }).catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Chưa tải được sản phẩm.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [key, attempt])
  useEffect(() => {
    const controller = new AbortController()
    setSuggestions([]); setSelected(-1)
    const timer = window.setTimeout(() => {
      if (query.trim().length >= 2) getSuggestions(query, controller.signal).then(result => {
        if (!controller.signal.aborted) setSuggestions(result.products)
      }).catch(() => { /* Suggestions are optional; the search form stays available. */ })
    }, 250)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [query])
  function change(name: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(name, value); else next.delete(name)
    next.delete('offset'); setParams(next); setFocused(false)
  }
  function submit(event: FormEvent) { event.preventDefault(); change('q', query.trim()) }
  const shown = !loading && !error ? data : null
  const activeFilters = ['category', 'brand', 'color', 'min_price', 'max_price', 'in_stock'].filter(name => params.has(name))
  const listOpen = focused && suggestions.length > 0
  const currentPage = shown ? Math.floor(shown.offset / shown.limit) + 1 : 1
  function page(offset: number) { const next = new URLSearchParams(params); next.set('offset', String(offset)); setParams(next) }
  return <div className="page-shell browse-page">
    <header className="page-heading"><h1>Bộ sưu tập Cortis.</h1><p>Chọn theo phong cách, thương hiệu và khoảng giá của bạn.</p><Link className="text-link" to="/">Tìm bằng mô tả, giọng nói hoặc ảnh <ArrowRight size={16} aria-hidden="true" /></Link></header>
    <form className="browse-search" onSubmit={submit} role="search" aria-label="Tìm trong bộ sưu tập">
      <div className="browse-query"><label htmlFor="browse-query">Tên sản phẩm hoặc mã sản phẩm</label>
        <input id="browse-query" role="combobox" autoComplete="off" aria-autocomplete="list" aria-expanded={listOpen} aria-controls="browse-suggestions" aria-activedescendant={listOpen && selected >= 0 ? `suggestion-${selected}` : undefined} maxLength={500} value={query} placeholder="Ví dụ: áo thun, sneaker hoặc P001" onChange={event => { setQuery(event.target.value); setFocused(true) }} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)} onKeyDown={event => {
          if (event.key === 'Escape') { setFocused(false); setSelected(-1) }
          if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && suggestions.length) { event.preventDefault(); setFocused(true); setSelected(value => value < 0 ? event.key === 'ArrowDown' ? 0 : suggestions.length - 1 : (value + (event.key === 'ArrowDown' ? 1 : -1) + suggestions.length) % suggestions.length) }
          if (event.key === 'Enter' && listOpen && selected >= 0) { event.preventDefault(); navigate(`/products/${suggestions[selected].product_id}`) }
        }} />
        {listOpen && <ul className="browse-suggestions" id="browse-suggestions" role="listbox" aria-label="Gợi ý sản phẩm">{suggestions.map((product, index) => <li role="option" id={`suggestion-${index}`} aria-selected={selected === index} key={product.product_id} onMouseDown={event => event.preventDefault()} onClick={() => navigate(`/products/${product.product_id}`)}><span>{product.name}</span><small>{product.product_id}</small></li>)}</ul>}
      </div><button className="primary-button" type="submit"><Search size={17} aria-hidden="true" />Tìm trong bộ sưu tập</button>
    </form>
    <nav className="browse-categories" aria-label="Danh mục sản phẩm"><button type="button" aria-pressed={!params.has('category')} onClick={() => change('category', '')}>Tất cả</button>{Object.entries(categoryLabels).map(([category, label]) => <button key={category} type="button" aria-pressed={params.get('category') === category} onClick={() => change('category', category)}>{label}</button>)}</nav>
    <div className="catalog-layout">
      <aside className={`filter-sidebar ${filtersOpen ? 'is-open' : ''}`} aria-label="Bộ lọc bộ sưu tập">
        <div className="filter-heading"><button type="button" className="text-link" aria-expanded={filtersOpen} aria-controls="browse-filter-content" onClick={() => setFiltersOpen(value => !value)}><SlidersHorizontal size={17} aria-hidden="true" />Bộ lọc</button><button type="button" className="text-link" onClick={() => { const next = new URLSearchParams(params); activeFilters.forEach(name => next.delete(name)); next.delete('offset'); setParams(next) }}>Xóa lọc</button></div>
        <div className="filter-content" id="browse-filter-content">
          {(['category', 'brand', 'color'] as const).map(field => <div className="browse-filter" key={field}><label htmlFor={`browse-${field}`}>{field === 'category' ? 'Loại sản phẩm' : field === 'brand' ? 'Thương hiệu' : 'Màu sắc'}</label><select id={`browse-${field}`} value={params.get(field) ?? ''} onChange={event => change(field, event.target.value)}><option value="">Tất cả</option>{data?.facets[field].map(facet => <option value={facet.value} key={facet.value}>{field === 'category' ? categoryLabels[facet.value as Category] : facet.value} ({facet.count})</option>)}</select></div>)}
          <form className="browse-price" key={key} onSubmit={event => {
            event.preventDefault(); const fields = new FormData(event.currentTarget); const next = new URLSearchParams(params)
            for (const name of ['min_price', 'max_price']) { const value = String(fields.get(name) ?? ''); if (value) next.set(name, value); else next.delete(name) }
            next.delete('offset'); setParams(next)
          }}><fieldset><legend>Khoảng giá (VND)</legend><label htmlFor="browse-min">Thấp nhất</label><input name="min_price" id="browse-min" type="number" min="0" max="1000000000" step="1" defaultValue={params.get('min_price') ?? ''} placeholder="Không giới hạn" /><label htmlFor="browse-max">Cao nhất</label><input name="max_price" id="browse-max" type="number" min="0" max="1000000000" step="1" defaultValue={params.get('max_price') ?? ''} placeholder="Không giới hạn" /></fieldset><button className="secondary-button" type="submit">Áp dụng khoảng giá</button></form>
          <label className="checkbox-label"><input type="checkbox" checked={params.get('in_stock') === 'true'} onChange={event => change('in_stock', event.target.checked ? 'true' : '')} />Chỉ còn hàng</label>
        </div>
      </aside>
      <section className="catalog-content" aria-label="Sản phẩm trong bộ sưu tập" aria-busy={loading}>
        <h2 className="visually-hidden">Sản phẩm trong bộ sưu tập</h2>
        <div className="results-toolbar"><span role="status">{loading ? 'Đang tải sản phẩm…' : shown ? `${shown.total} sản phẩm` : 'Chưa tải được sản phẩm'}</span><div className="browse-sort"><label htmlFor="browse-sort">Sắp xếp</label><select id="browse-sort" value={params.get('sort') ?? 'relevance'} onChange={event => change('sort', event.target.value)}><option value="relevance">Phù hợp nhất</option><option value="price_asc">Giá tăng dần</option><option value="price_desc">Giá giảm dần</option><option value="name">Tên sản phẩm</option></select></div></div>
        {!!activeFilters.length && <div className="browse-active" aria-label="Bộ lọc đang áp dụng">{activeFilters.map(name => <button className="secondary-button" type="button" key={name} onClick={() => change(name, '')}>{name === 'category' ? categoryLabels[params.get(name) as Category] ?? params.get(name) : name === 'in_stock' ? 'Còn hàng' : name === 'min_price' ? `Từ ${params.get(name)} VND` : name === 'max_price' ? `Đến ${params.get(name)} VND` : params.get(name)}<X size={14} aria-hidden="true" /><span className="visually-hidden">Xóa bộ lọc {name}</span></button>)}</div>}
        {!!shown?.corrections.length && <p className="draft-notice">Đã tìm thêm từ gần đúng: {shown.corrections.map(item => `${item.input} → ${item.matched}`).join(', ')}.</p>}
        {error && <ErrorPanel message={error} onRetry={() => setAttempt(value => value + 1)} />}
        {loading && <p className="page-loading" role="status">Đang cập nhật bộ sưu tập…</p>}
        {shown && (shown.products.length ? <div className="product-grid">{shown.products.map(product => <ProductCard key={product.product_id} product={product} onOpen={() => undefined} />)}</div> : <div className="empty-state"><h2>{shown.total > 0 ? 'Trang này không còn sản phẩm' : shown.empty_reason === 'no_matches' ? 'Chưa tìm thấy sản phẩm này' : 'Không có sản phẩm đáp ứng bộ lọc'}</h2><p>Thử từ khóa khác hoặc bỏ bớt điều kiện.</p><button className="secondary-button" onClick={() => setParams({})}>Xem toàn bộ bộ sưu tập</button></div>)}
        {shown && shown.total > 0 && <nav className="browse-pagination" aria-label="Phân trang bộ sưu tập"><button className="secondary-button" disabled={shown.offset === 0} onClick={() => page(Math.max(0, shown.offset - shown.limit))}><ArrowLeft size={16} aria-hidden="true" />Trang trước</button><span>Trang {currentPage} / {Math.ceil(shown.total / shown.limit)}</span><button className="secondary-button" disabled={shown.offset + shown.limit >= shown.total} onClick={() => page(shown.offset + shown.limit)}>Trang sau<ArrowRight size={16} aria-hidden="true" /></button></nav>}
      </section>
    </div>
  </div>
}
