import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { Link } from 'react-router-dom';
import { ArrowDown, ArrowRight, ArrowUpRight, AudioLines, Camera, Check, ChevronDown, Clock3, ImagePlus, LoaderCircle, Mic, SlidersHorizontal, Square, Type, Upload, X } from 'lucide-react';
import { useCatalog } from '../catalog';
import { useSearchState, initialOptions, type Draft } from '../state';
import { ApiError, searchText, searchImage, searchMultimodal, transcribe } from '../lib/api';
import { MicrophoneRecorder } from '../lib/voice';
import type { Category, ProductSummary, QueryMode, SearchOptions, SearchResponse, SearchResult } from '../lib/types';
import { categoryLabels, ErrorPanel, formatMoney, ProductImage } from '../ui';

const modes = [
  { id: 'text' as const, label: 'Mô tả', icon: Type },
  { id: 'voice' as const, label: 'Giọng nói', icon: AudioLines },
  { id: 'image' as const, label: 'Hình ảnh', icon: Camera },
  { id: 'multimodal' as const, label: 'Mô tả + ảnh', icon: ImagePlus },
];
const stepLabels: Record<string, string> = { validation: 'Kiểm tra đầu vào', encoding: 'Hiểu mô tả / hình ảnh', retrieval: 'So sánh sản phẩm', filtering: 'Áp dụng bộ lọc', threshold: 'Lọc mức liên quan', ranking: 'Xếp hạng kết quả', hydration: 'Hiển thị sản phẩm' };
const ignoreAbort = (error: unknown) => error instanceof DOMException && error.name === 'AbortError';
function useObjectUrl(file: File | null) {
  const [url, setUrl] = useState('');
  useEffect(() => { if (!file) { setUrl(''); return; } const next = URL.createObjectURL(file); setUrl(next); return () => URL.revokeObjectURL(next); }, [file]);
  return url;
}
function signature(draft: Draft, mode: QueryMode) {
  return JSON.stringify({ text: mode === 'image' ? null : draft.text.normalize('NFC').trim().replace(/\s+/g, ' '), image: draft.image ? [draft.image.name, draft.image.size, draft.image.lastModified] : null,
    options: draft.options, weight: mode === 'multimodal' ? draft.weight : null, source: mode === 'voice' ? draft.voiceSource : null });
}
function ProductCard({ product, result, onOpen }: { product: ProductSummary; result?: SearchResult; onOpen: () => void }) {
  return <article className="product-card" data-testid={result ? 'result-card' : 'product-card'}>
    <Link to={`/products/${product.product_id}`} className="product-card-link" onClick={onOpen}>
      <div className="product-card-media"><ProductImage src={product.image_url} alt={product.name} retry={false} />
        {result && <span className="rank-label">{String(result.rank).padStart(2, '0')}</span>}
        {!product.in_stock && <span className="stock-tag">Hết hàng</span>}
        <span className="product-open" aria-hidden="true"><ArrowUpRight size={20} /></span>
      </div>
      <div className="product-card-copy"><div className="product-brand">{product.brand}<span>{categoryLabels[product.category]}</span></div><h3>{product.name}</h3><p className="product-color">{product.color}</p>
        <div className="product-price-row"><strong>{formatMoney(product.price_vnd)}</strong>{result && <span className="cosine-score">Cosine {result.score.toFixed(3)}</span>}</div>
        <span className="card-stock">{product.in_stock ? 'Còn hàng' : 'Tạm hết hàng'}</span>
      </div>
    </Link>
  </article>;
}

export function SearchPage() {
  const catalog = useCatalog();
  const state = useSearchState();
  const { mode, drafts, responses } = state;
  const draft = drafts[mode];
  const response = responses[mode];
  const [pending, setPending] = useState<'search' | 'speech' | null>(null);
  const [error, setError] = useState('');
  const [field, setField] = useState('');
  const [notice, setNotice] = useState('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [micPhase, setMicPhase] = useState<'idle' | 'permission' | 'recording'>('idle');
  const [duration, setDuration] = useState(0);
  const [cooldownUntil, setCooldownUntil] = useState(0);
  const [cooldown, setCooldown] = useState(0);
  const sequence = useRef(0);
  const micSequence = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const recorder = useRef<MicrophoneRecorder | null>(null);
  const textRef = useRef<HTMLTextAreaElement>(null);
  const imageRef = useRef<HTMLInputElement>(null);
  const modeRef = useRef(mode);
  const savedScroll = useRef(state.scroll);
  modeRef.current = mode;
  const imageUrl = useObjectUrl(draft.image);
  const audioUrl = useObjectUrl(draft.audio);
  const speechAvailable = catalog.meta?.speech.configuration_state === 'configured_unverified';
  const relevantAvailable = !!catalog.meta?.capabilities.relevant.modes.includes(mode) &&
    (mode !== 'multimodal' || !!catalog.meta.capabilities.relevant.multimodal_weights.includes(draft.weight));
  const featured = catalog.products.find(product => product.product_id === 'P006') ?? catalog.products[0];
  const dirty = !!response && (state.signatures[mode]
    ? state.signatures[mode] !== signature(draft, mode)
    : response.query.text !== (mode === 'image' ? null : draft.text.normalize('NFC').trim().replace(/\s+/g, ' ')) || JSON.stringify(response.query.options) !== JSON.stringify(draft.options));

  useEffect(() => {
    const tick = () => setCooldown(Math.max(0, Math.ceil((cooldownUntil - Date.now()) / 1000)));
    tick(); const timer = window.setInterval(tick, 500); return () => window.clearInterval(timer);
  }, [cooldownUntil]);
  useEffect(() => {
    const frame = requestAnimationFrame(() => window.scrollTo(0, savedScroll.current));
    return () => { cancelAnimationFrame(frame); sequence.current++; micSequence.current++; controller.current?.abort(); void recorder.current?.cancel(); state.setScroll(window.scrollY); };
  }, []);
  useEffect(() => {
    if (draft.options.result_policy === 'relevant' && catalog.meta && !relevantAvailable) {
      state.updateDraft(mode, { options: { ...draft.options, result_policy: 'nearest' } });
      setNotice('Mức liên quan chưa sẵn sàng cho cách tìm này. Lượt tìm tiếp theo dùng sản phẩm gần nhất.');
    }
  }, [mode, draft.weight, catalog.meta, relevantAvailable]);

  function update(update: Partial<Draft>) { state.updateDraft(mode, update); }
  function updateOptions(updateValue: Partial<SearchOptions>) { update({ options: { ...draft.options, ...updateValue } }); }
  function updateFilters(updateValue: Partial<SearchOptions['filters']>) { updateOptions({ filters: { ...draft.options.filters, ...updateValue } }); }
  function cancel() {
    sequence.current++; micSequence.current++; controller.current?.abort(); controller.current = null;
    void recorder.current?.cancel(); recorder.current = null; setPending(null); setMicPhase('idle'); setDuration(0);
  }
  function switchMode(next: QueryMode) { cancel(); state.setMode(next); setError(''); setField(''); setNotice(''); }
  function tabKey(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault(); const next = event.key === 'Home' ? 0 : event.key === 'End' ? 3 : (index + (event.key === 'ArrowRight' ? 1 : -1) + 4) % 4;
    switchMode(modes[next].id); document.getElementById(`tab-${modes[next].id}`)?.focus();
  }
  function showError(reason: unknown) {
    if (ignoreAbort(reason)) return;
    const message = reason instanceof Error ? reason.message : 'Không thể hoàn tất. Vui lòng thử lại.';
    setError(message);
    if (reason instanceof ApiError) {
      setField(reason.field_errors[0]?.field ?? '');
      if (reason.retryAfter) setCooldownUntil(Date.now() + reason.retryAfter * 1000);
      if (reason.field_errors.some(item => item.field === 'text')) textRef.current?.focus();
    }
  }
  function chooseImage(file?: File) {
    if (!file) return;
    if (!file.size || file.size > 5 * 1024 * 1024) { setError('Ảnh cần có dữ liệu và nhỏ hơn hoặc bằng 5 MiB.'); setField('image'); return; }
    if (!['image/jpeg', 'image/png', 'image/webp', 'application/octet-stream', ''].includes(file.type)) { setError('Hãy chọn ảnh JPEG, PNG hoặc WebP.'); setField('image'); return; }
    update({ image: file }); setError(''); setField('');
  }
  function chooseAudio(file?: File) {
    if (!file) return;
    if (!file.size || file.size > 1024 * 1024) { setError('Tệp WAV cần nhỏ hơn hoặc bằng 1 MiB.'); return; }
    update({ audio: file }); setError('');
  }
  async function submit(event?: FormEvent) {
    event?.preventDefault(); if (pending || cooldown) return;
    setError(''); setField('');
    const text = draft.text.normalize('NFC').trim().replace(/\s+/g, ' ');
    if (mode !== 'image' && (!text || Array.from(text).length > 500)) { setError('Vui lòng nhập mô tả từ 1 đến 500 ký tự.'); setField('text'); textRef.current?.focus(); return; }
    if ((mode === 'image' || mode === 'multimodal') && !draft.image) { setError('Hãy chọn một hình ảnh để tìm sản phẩm.'); setField('image'); imageRef.current?.focus(); return; }
    const { min_price, max_price } = draft.options.filters;
    if ((min_price != null && (!Number.isInteger(min_price) || min_price < 0 || min_price > 1e9)) || (max_price != null && (!Number.isInteger(max_price) || max_price < 0 || max_price > 1e9)) || (min_price != null && max_price != null && min_price > max_price)) {
      setError('Giá phải là số nguyên từ 0 đến 1 tỷ; giá thấp nhất không vượt giá cao nhất.'); setField('price'); setFiltersOpen(true); document.getElementById('min-price')?.focus(); return;
    }
    const token = ++sequence.current; controller.current?.abort(); const abort = new AbortController(); controller.current = abort;
    const activeMode = mode; const snapshot = signature(draft, mode); setPending('search');
    try {
      const result = activeMode === 'image' ? await searchImage(draft.image!, draft.options, abort.signal)
        : activeMode === 'multimodal' ? await searchMultimodal(text, draft.image!, draft.weight, draft.options, abort.signal)
        : await searchText(activeMode === 'voice' ? { mode: 'voice', text, voice_source: draft.voiceSource, options: draft.options } : { mode: 'text', text, options: draft.options }, abort.signal);
      if (token !== sequence.current || abort.signal.aborted || modeRef.current !== activeMode) return;
      state.setSignature(activeMode, snapshot); state.setResponse(activeMode, result); setNotice('');
    } catch (reason) { if (token === sequence.current) showError(reason); }
    finally { if (token === sequence.current) setPending(null); }
  }
  async function recognize() {
    if (!draft.audio || pending || !speechAvailable || cooldown) return;
    const token = ++sequence.current; const abort = new AbortController(); controller.current?.abort(); controller.current = abort;
    setPending('speech'); setError('');
    try {
      const result = await transcribe(draft.audio, abort.signal);
      if (token !== sequence.current || abort.signal.aborted || modeRef.current !== 'voice') return;
      state.updateDraft('voice', { text: result.transcript, voiceSource: 'azure', transcriptModified: false });
      textRef.current?.focus(); setNotice('Đã nhận dạng. Bạn có thể sửa lời nói trước khi tìm sản phẩm.');
    } catch (reason) { if (token === sequence.current) showError(reason); }
    finally { if (token === sequence.current) setPending(null); }
  }
  async function startRecording() {
    if (micPhase !== 'idle' || pending) return;
    const token = ++micSequence.current; setError(''); setDuration(0); setMicPhase('permission');
    const instance = new MicrophoneRecorder({ onDuration: value => { if (token === micSequence.current) setDuration(value); },
      onAutoStop: file => { if (token === micSequence.current) { state.updateDraft('voice', { audio: file }); setMicPhase('idle'); setNotice('Đã dừng ở 15 giây. Bấm nhận dạng khi bạn sẵn sàng.'); } },
      onError: reason => { if (token === micSequence.current) { showError(reason); setMicPhase('idle'); } } });
    recorder.current = instance;
    try { await instance.start(); if (token === micSequence.current && modeRef.current === 'voice') setMicPhase('recording'); else await instance.cancel(); }
    catch (reason) { if (token === micSequence.current) { setMicPhase('idle'); if (!ignoreAbort(reason)) setError('Chưa truy cập được microphone. Kiểm tra quyền hoặc tải tệp WAV để tiếp tục.'); } }
  }
  async function stopRecording() {
    const token = micSequence.current;
    try { const file = await recorder.current?.stop(); if (file && token === micSequence.current) state.updateDraft('voice', { audio: file }); }
    catch (reason) { if (token === micSequence.current) showError(reason); }
    finally { if (token === micSequence.current) setMicPhase('idle'); }
  }
  const visibleCatalog = catalog.products.filter(product => {
    const filters = draft.options.filters;
    return (!filters.category || product.category === filters.category) && (!filters.brand || product.brand === filters.brand)
      && (filters.min_price == null || product.price_vnd >= filters.min_price) && (filters.max_price == null || product.price_vnd <= filters.max_price)
      && (!filters.in_stock || product.in_stock);
  });
  const activeFilters = Object.values(draft.options.filters).filter(value => value != null && value !== false).length;
  const effective = response?.query.options.filters;

  return <div className="search-page">
    <section className="showroom-hero" aria-labelledby="hero-title"><div className="hero-copy">
      <h1 id="hero-title">Tìm món đồ<br /><span>đúng với bạn.</span></h1>
      <p>Từ một ý tưởng, một lời nói hay một hình ảnh.<br className="desktop-break" /> Khám phá thời trang theo cách của riêng bạn.</p>
      <form className="search-desk" onSubmit={submit} aria-label="Tìm sản phẩm">
        <div className="mode-tabs" role="tablist" aria-label="Cách tìm sản phẩm">{modes.map((item, index) => <button key={item.id} id={`tab-${item.id}`} type="button" role="tab" aria-selected={mode === item.id} aria-controls={`panel-${item.id}`} tabIndex={mode === item.id ? 0 : -1} onClick={() => switchMode(item.id)} onKeyDown={event => tabKey(event, index)}><item.icon size={17} aria-hidden="true" />{item.label}</button>)}</div>
        <div id={`panel-${mode}`} role="tabpanel" aria-labelledby={`tab-${mode}`} className="search-input-panel">
          {mode === 'voice' && <div className="voice-workspace"><p className="voice-intro">Nói một câu tiếng Việt, tối đa 15 giây. Âm thanh chỉ được gửi đến Azure khi bạn bấm nhận dạng.</p>
            <div className="record-row">{micPhase === 'recording' ? <button className="secondary-button recording-button" type="button" onClick={() => void stopRecording()}><Square size={15} fill="currentColor" aria-hidden="true" />Dừng ghi âm</button>
              : <button className="secondary-button" type="button" disabled={micPhase === 'permission' || !!pending} onClick={() => void startRecording()}><Mic size={17} aria-hidden="true" />{micPhase === 'permission' ? 'Đang xin quyền…' : 'Bắt đầu ghi âm'}</button>}
              <span className="record-timer">{duration.toFixed(1)} / 15 giây</span>
              {micPhase !== 'idle' && <button className="icon-button" aria-label="Hủy ghi âm" type="button" onClick={cancel}><X size={18} /></button>}
            </div>
            <label className="audio-upload"><Upload size={16} aria-hidden="true" /> Hoặc tải WAV PCM16, mono 16 kHz<input type="file" accept=".wav,audio/wav" data-testid="voice-audio-input" onChange={event => chooseAudio(event.target.files?.[0])} /></label>
            {draft.audio && audioUrl && <div className="audio-preview"><audio src={audioUrl} controls aria-label="Nghe bản ghi âm" /><button type="button" className="icon-button" aria-label="Xóa âm thanh" onClick={() => update({ audio: null })}><X size={17} /></button></div>}
            <button type="button" className="secondary-button recognize-button" disabled={!draft.audio || !speechAvailable || !!pending || micPhase !== 'idle' || cooldown > 0} onClick={() => void recognize()}>{pending === 'speech' ? <LoaderCircle className="spin" size={16} aria-hidden="true" /> : <AudioLines size={17} aria-hidden="true" />}Nhận dạng lời nói</button>
            {!speechAvailable && <p className="voice-unavailable">Nhận dạng Azure chưa sẵn sàng. Bạn vẫn có thể nhập lời nói bên dưới để thử tìm kiếm.</p>}
            <div className="transcript-origin"><span>{draft.voiceSource === 'azure' ? 'Azure Speech · tiếng Việt' : 'Transcript nhập tay · mô phỏng'}</span>{draft.transcriptModified && draft.voiceSource === 'azure' && <span>Đã chỉnh sửa transcript</span>}
              {draft.voiceSource === 'azure' && <button type="button" className="text-link" onClick={() => update({ voiceSource: 'manual_transcript', transcriptModified: false })}>Chuyển sang nhập tay</button>}</div>
          </div>}
          {mode !== 'image' && <div className="text-input-group"><label htmlFor="search-text">{mode === 'voice' ? 'Lời nói của bạn' : 'Bạn đang tìm điều gì?'}</label>
            <textarea ref={textRef} id="search-text" data-testid={mode === 'voice' ? 'voice-transcript' : 'search-text'} value={draft.text} aria-invalid={field === 'text'} aria-describedby={field === 'text' ? 'search-error' : 'text-count'} placeholder={mode === 'voice' ? 'Nhập hoặc chỉnh sửa lời nói trước khi tìm…' : 'Ví dụ: giày Converse màu đỏ, cổ cao…'} rows={2} onChange={event => update({ text: event.target.value, transcriptModified: draft.voiceSource === 'azure' })} />
            <span id="text-count" className={`text-counter ${Array.from(draft.text).length > 500 ? 'invalid' : ''}`}>{Array.from(draft.text).length}/500 ký tự</span>
          </div>}
          {(mode === 'image' || mode === 'multimodal') && <div className={`image-drop ${draft.image ? 'has-image' : ''}`} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); chooseImage(event.dataTransfer.files[0]); }}>
            {draft.image ? <>{imageUrl && <img className="query-preview" src={imageUrl} alt="Hình ảnh bạn dùng để tìm sản phẩm" />}<div><strong>{draft.image.name}</strong><p>{(draft.image.size / 1024).toFixed(0)} KB · chỉ dùng cho lượt tìm</p><button className="text-link" type="button" onClick={() => imageRef.current?.click()}>Thay ảnh</button><button className="text-link" type="button" onClick={() => update({ image: null })}>Xóa ảnh</button></div></>
              : <><Camera size={27} strokeWidth={1.5} aria-hidden="true" /><label htmlFor="image-input"><strong>Thả một ảnh vào đây</strong><span>hoặc chọn ảnh từ thiết bị</span></label><p>JPEG, PNG, WebP · tối đa 5 MiB</p></>}
            <input ref={imageRef} type="file" id="image-input" data-testid="image-input" accept="image/jpeg,image/png,image/webp" aria-label="Chọn ảnh sản phẩm" onChange={event => { chooseImage(event.target.files?.[0]); event.target.value = ''; }} />
          </div>}
          {mode === 'multimodal' && <div className="weight-control"><label htmlFor="text-weight">Ưu tiên mô tả <strong>{Math.round(draft.weight * 100)}%</strong></label><input id="text-weight" data-testid="text-weight" type="range" min="0.1" max="0.9" step="0.1" value={draft.weight} onChange={event => update({ weight: Number(event.target.value) })} /><span>Ảnh {Math.round((1 - draft.weight) * 100)}%</span></div>}
          {(mode === 'text' || mode === 'multimodal') && <div className="suggestions"><span>Thử tìm</span>{['Giày Converse màu đỏ', 'Túi da màu nâu', 'Giày chạy bộ màu đen'].map(text => <button key={text} type="button" onClick={() => { update({ text }); textRef.current?.focus(); }}>{text}<ArrowUpRight size={12} aria-hidden="true" /></button>)}</div>}
          {error && <div id="search-error" data-testid="search-error"><ErrorPanel message={error} title="Vui lòng kiểm tra lại" /></div>}
          {notice && <p className="notice" role="status">{notice}</p>}
          <div className="search-action-row"><span><Check size={14} aria-hidden="true" />Tìm trong danh mục thật</span><button type="submit" className="primary-button" data-testid="search-submit" disabled={!!pending || micPhase !== 'idle' || cooldown > 0 || !catalog.meta?.capabilities.search.available}>{pending === 'search' ? <><LoaderCircle size={18} className="spin" aria-hidden="true" />Đang tìm…</> : <>{cooldown ? `Thử lại sau ${cooldown}s` : mode === 'voice' ? 'Tìm theo lời nói' : mode === 'image' ? 'Tìm bằng ảnh' : mode === 'multimodal' ? 'Tìm kết hợp' : 'Tìm sản phẩm'}<ArrowRight size={18} aria-hidden="true" /></>}</button></div>
          {pending && <button type="button" className="text-link cancel-search" onClick={cancel}>Hủy yêu cầu</button>}
          {catalog.meta && !catalog.meta.capabilities.search.available && <p className="voice-unavailable">Tìm kiếm AI chưa sẵn sàng. Bạn vẫn có thể xem danh mục và đơn hàng.</p>}
          {catalog.metaError && <ErrorPanel message={catalog.metaError} title="Chưa kết nối được tìm kiếm" onRetry={catalog.reload} />}
        </div>
      </form>
    </div>
    <div className="hero-display">{featured && <Link className="hero-sample" to={`/products/${featured.product_id}`} onClick={() => state.setScroll(window.scrollY)}><ProductImage src={featured.image_url} alt={featured.name} className="hero-photograph" retry={false} eager /><div className="hero-sample-caption"><span><strong>{featured.brand}</strong><span>{featured.color}</span></span><ArrowUpRight size={23} aria-hidden="true" /></div></Link>}
      <div className="hero-display-note"><span>Nhìn thấy điều mình thích.<br />Tìm lại bằng một tấm ảnh.</span><button type="button" onClick={() => { switchMode('image'); requestAnimationFrame(() => imageRef.current?.focus()); }} aria-label="Chuyển sang tìm bằng ảnh"><Camera size={21} aria-hidden="true" /><ArrowUpRight size={17} aria-hidden="true" /></button></div>
    </div></section>
    <section className="catalog-section" aria-labelledby="catalog-title"><div className="catalog-heading"><div><h2 id="catalog-title">{response ? 'Những món đồ phù hợp' : 'Bộ sưu tập Cortis'}</h2><p>{response ? response.query.text ? `“${response.query.text}”` : 'Tìm từ hình ảnh của bạn' : 'Giày, túi, quần áo và phụ kiện — từ dáng quen đến nét riêng.'}</p></div>
      <a className="catalog-jump" href="#catalog-title"><ArrowDown size={15} aria-hidden="true" />Khám phá sản phẩm</a></div>
      <div className="catalog-layout"><aside className={`filter-sidebar ${filtersOpen ? 'is-open' : ''}`} aria-label="Bộ lọc sản phẩm"><button type="button" className="filter-toggle" onClick={() => setFiltersOpen(value => !value)} aria-expanded={filtersOpen}><SlidersHorizontal size={18} aria-hidden="true" />Bộ lọc{activeFilters ? ` (${activeFilters})` : ''}<ChevronDown size={16} aria-hidden="true" /></button>
        <div className="filter-content"><div className="filter-title"><h3>Bộ lọc</h3><button type="button" className="text-link" onClick={() => { update({ options: initialOptions() }); setError(''); }}>Đặt lại</button></div>
          <p className="filter-help">Giới hạn giá và thương hiệu bằng bộ lọc. Thay đổi sẽ áp dụng khi bạn tìm lại.</p>
          <label htmlFor="filter-category">Loại sản phẩm</label><select id="filter-category" data-testid="filter-category" value={draft.options.filters.category ?? ''} onChange={event => updateFilters({ category: event.target.value as Category || null })}><option value="">Tất cả sản phẩm</option>{(catalog.meta?.filters.categories ?? Object.keys(categoryLabels) as Category[]).map(category => <option key={category} value={category}>{categoryLabels[category]}</option>)}</select>
          <label htmlFor="filter-brand">Thương hiệu</label><select id="filter-brand" data-testid="filter-brand" value={draft.options.filters.brand ?? ''} onChange={event => updateFilters({ brand: event.target.value || null })}><option value="">Tất cả thương hiệu</option>{catalog.meta?.filters.brands.map(brand => <option key={brand}>{brand}</option>)}</select>
          <fieldset className="price-filter"><legend>Khoảng giá (VND)</legend><label htmlFor="min-price">Thấp nhất</label><input id="min-price" data-testid="min-price" type="number" min="0" max="1000000000" step="1" placeholder="Không giới hạn" value={draft.options.filters.min_price ?? ''} aria-invalid={field === 'price'} onChange={event => updateFilters({ min_price: event.target.value === '' ? null : Number(event.target.value) })} /><label htmlFor="max-price">Cao nhất</label><input id="max-price" data-testid="max-price" type="number" min="0" max="1000000000" step="1" placeholder="Không giới hạn" value={draft.options.filters.max_price ?? ''} onChange={event => updateFilters({ max_price: event.target.value === '' ? null : Number(event.target.value) })} /></fieldset>
          <label className="checkbox-label"><input type="checkbox" checked={!!draft.options.filters.in_stock} onChange={event => updateFilters({ in_stock: event.target.checked })} />Chỉ còn hàng</label>
          <div className="advanced-options"><label htmlFor="top-k">Số kết quả</label><select id="top-k" data-testid="top-k" value={draft.options.top_k} onChange={event => updateOptions({ top_k: Number(event.target.value) })}>{[1, 3, 5, 10, 20].map(value => <option key={value} value={value}>{value} sản phẩm</option>)}</select>
            <label htmlFor="result-policy">Cách hiển thị</label><select id="result-policy" data-testid="result-policy" value={draft.options.result_policy} onChange={event => updateOptions({ result_policy: event.target.value as SearchOptions['result_policy'] })}><option value="nearest">Sản phẩm gần nhất</option><option value="relevant" disabled={!relevantAvailable}>Chỉ sản phẩm liên quan</option></select><p>{relevantAvailable ? 'Liên quan: chỉ giữ sản phẩm đạt ngưỡng đã hiệu chỉnh.' : 'Chưa có ngưỡng liên quan cho lựa chọn này.'}</p>
          </div><button className="secondary-button filter-apply" type="button" disabled={!!pending} onClick={() => void submit()}>Áp dụng và tìm lại<ArrowRight size={15} aria-hidden="true" /></button>
        </div>
      </aside>
      <div className="catalog-content" data-testid="search-results" aria-busy={pending === 'search'}><div className="results-toolbar"><span role="status" aria-live="polite">{pending === 'search' ? 'Đang tìm sản phẩm…' : `${response ? response.results.length : visibleCatalog.length} sản phẩm`}</span><span>{response ? <><Clock3 size={14} aria-hidden="true" />{(response.meta.timing_ms.total / 1000).toFixed(2)} giây</> : 'Ảnh chụp thực tế'}</span></div>
        {response && <div className="submitted-context"><span>{modes.find(item => item.id === response.query.mode)?.label} · {response.meta.result_policy === 'nearest' ? 'Các sản phẩm gần nhất · chưa lọc mức liên quan' : 'Chỉ giữ kết quả đạt ngưỡng đã hiệu chỉnh'}</span>
          <div className="effective-filters">{effective?.category && <span>{categoryLabels[effective.category]}</span>}{effective?.brand && <span>{effective.brand}</span>}{effective?.min_price != null && <span>Từ {formatMoney(effective.min_price)}</span>}{effective?.max_price != null && <span>Đến {formatMoney(effective.max_price)}</span>}{effective?.in_stock && <span>Chỉ còn hàng</span>}{response.query.text_weight != null && <span>Mô tả {Math.round(response.query.text_weight * 100)}% / ảnh {Math.round((1 - response.query.text_weight) * 100)}%</span>}</div>
          {dirty && <p className="draft-notice" role="status">Đã đổi điều kiện, hãy tìm lại. Kết quả bên dưới vẫn thuộc lượt tìm trước.</p>}
          <button type="button" className="text-link" onClick={() => { state.setResponse(mode, null); setError(''); }}>Về danh mục sản phẩm</button>
        </div>}
        {catalog.loading && !response ? <div className="product-grid skeleton-grid" aria-label="Đang tải danh mục">{Array.from({ length: 6 }, (_, index) => <div key={index} className="product-skeleton"><div /><span /><span /></div>)}</div>
          : catalog.error && !response ? <ErrorPanel title="Chưa tải được danh mục" message={catalog.error} onRetry={catalog.reload} />
          : (response ? response.results.length : visibleCatalog.length) === 0 ? <div className="empty-state"><Camera size={32} strokeWidth={1.4} aria-hidden="true" /><h3>{response?.meta.empty_reason === 'threshold' ? 'Chưa có sản phẩm đạt ngưỡng liên quan' : catalog.products.length === 0 ? 'Danh mục chưa có sản phẩm' : 'Không có sản phẩm đáp ứng bộ lọc'}</h3><p>Thử mô tả khác, thay ảnh hoặc điều chỉnh bộ lọc để tiếp tục khám phá.</p><button type="button" className="secondary-button" onClick={() => { update({ options: initialOptions() }); state.setResponse(mode, null); }}>Xóa bộ lọc và xem danh mục<ArrowRight size={16} aria-hidden="true" /></button></div>
          : <div className="product-grid">{response ? response.results.map(result => <ProductCard key={result.product.product_id} product={result.product} result={result} onOpen={() => state.setScroll(window.scrollY)} />) : visibleCatalog.map(product => <ProductCard key={product.product_id} product={product} onOpen={() => state.setScroll(window.scrollY)} />)}</div>}
        {response && <details className="processing-panel" data-testid="processing-panel"><summary>Xem cách hệ thống xử lý<ChevronDown size={17} aria-hidden="true" /></summary><div className="processing-content"><p>Điểm cosine biểu thị độ tương đồng, không phải xác suất chính xác.</p><ol>{response.meta.trace.map(step => <li key={step.step}><span>{stepLabels[step.step] ?? step.step}</span><span>{step.status === 'skipped' ? 'Không áp dụng' : `${step.output_count} đầu ra`} · {(response.meta.timing_ms[step.step as keyof SearchResponse['meta']['timing_ms']] ?? 0).toFixed(1)} ms</span></li>)}</ol>
          {response.query.mode === 'multimodal' && <table><caption>Điểm thành phần theo sản phẩm</caption><thead><tr><th scope="col">Sản phẩm</th><th scope="col">Mô tả</th><th scope="col">Ảnh</th><th scope="col">Kết hợp</th></tr></thead><tbody>{response.results.map(result => <tr key={result.product.product_id}><th scope="row">{result.product.name}</th><td>{result.component_scores.text?.toFixed(3)}</td><td>{result.component_scores.image?.toFixed(3)}</td><td>{result.score.toFixed(3)}</td></tr>)}</tbody></table>}
          <dl className="request-info"><dt>Mã lượt tìm</dt><dd>{response.request_id}</dd><dt>Model</dt><dd>{response.meta.model_fingerprint.slice(0, 12)}</dd><dt>Chỉ mục</dt><dd>{response.meta.index_fingerprint.slice(0, 12)}</dd></dl></div></details>}
      </div></div>
    </section>
  </div>;
}
