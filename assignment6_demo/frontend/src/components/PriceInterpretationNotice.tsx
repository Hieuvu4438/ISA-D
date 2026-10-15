import type { PriceInterpretation } from '../lib/types'
import { formatMoney } from '../ui'

export function PriceInterpretationNotice({ plan, showBounds = true }: { plan?: PriceInterpretation; showBounds?: boolean }) {
  if (!plan?.applied) return null
  return <div className="submitted-context" role="status" aria-label="Điều kiện giá đã hiểu"><p>Đã áp dụng giá từ mô tả: {plan.clauses.map(clause => `“${clause.text}”`).join('; ')}.</p>{showBounds && <div className="effective-filters">{plan.effective_filters.min_price != null && <span>Từ {formatMoney(plan.effective_filters.min_price)}</span>}{plan.effective_filters.max_price != null && <span>Đến {formatMoney(plan.effective_filters.max_price)}</span>}</div>}<p>Giới hạn này kết hợp với bộ lọc bạn chọn. Có thể sửa mô tả hoặc tắt tự hiểu giá rồi tìm lại.</p></div>
}
