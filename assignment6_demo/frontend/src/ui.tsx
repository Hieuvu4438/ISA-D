import { useEffect, useState } from 'react';
import { AlertCircle, ImageOff, RotateCcw } from 'lucide-react';
import type { Category } from './lib/types';

export const formatMoney = (value: number) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value);
export const categoryLabels: Record<Category, string> = {
  running_shoes: 'Giày chạy bộ', trail_shoes: 'Giày địa hình', casual_shoes: 'Giày thường ngày',
  boots: 'Giày boots', sandals: 'Dép và sandal', bag: 'Túi xách', backpack: 'Balo', tote_bag: 'Túi tote',
  t_shirt: 'Áo thun', jacket: 'Áo khoác', watch: 'Đồng hồ', sunglasses: 'Kính mát',
};
export function ProductImage({ src, alt, className = '', retry = true, eager = false }: {
  src: string; alt: string; className?: string; retry?: boolean; eager?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => { setFailed(false); setAttempt(0); }, [src]);
  return <div className={`product-image ${className}`}>
    {failed ? <div className="image-fallback"><ImageOff aria-hidden="true" size={28} /><span>Ảnh chưa tải được</span>
      {retry && <button type="button" className="text-link" onClick={() => { setFailed(false); setAttempt(value => value + 1); }}><RotateCcw size={14} aria-hidden="true" />Thử lại ảnh</button>}
    </div> : <img key={`${src}:${attempt}`} src={src} alt={alt} loading={eager ? 'eager' : 'lazy'} decoding="async" onError={() => setFailed(true)} />}
  </div>;
}
export function ErrorPanel({ message, title = 'Chưa thể hoàn tất', onRetry }: { message: string; title?: string; onRetry?: () => void }) {
  return <div className="error-panel" role="alert"><AlertCircle size={22} aria-hidden="true" /><div><strong>{title}</strong><p>{message}</p>
    {onRetry && <button type="button" className="text-link" onClick={onRetry}><RotateCcw size={15} aria-hidden="true" />Thử lại</button>}
  </div></div>;
}
