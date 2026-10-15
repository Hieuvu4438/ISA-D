import type { Category, ScopeInterpretation } from '../lib/types'
import { categoryLabels } from '../ui'

export function ScopeInterpretationNotice({ plan }: { plan?: ScopeInterpretation }) {
  if (!plan?.applied && !plan?.warnings.length) return null
  return <div className="submitted-context" role="status" aria-label="Phạm vi tìm kiếm đã hiểu">{plan.applied && <><p>Đang tìm trong phạm vi từ mô tả:</p><div className="effective-filters">{plan.clauses.map(clause => <span key={`${clause.field}:${clause.value}`}>{clause.field === 'category' ? categoryLabels[clause.value as Category] : clause.field === 'color' ? `Màu ${clause.value}` : clause.field === 'size' ? `Cỡ ${clause.value}` : clause.value}</span>)}</div><p>Các lựa chọn cùng hãng, loại, màu hoặc kích cỡ được nối bằng “hoặc”. Bộ lọc bạn chọn vẫn áp dụng. Có thể tắt tự hiểu phạm vi rồi tìm lại để mở rộng.</p>{plan.clauses.some(c => c.field === 'size') && <p>Bật “Chỉ còn hàng” để chỉ xem sản phẩm còn đúng cỡ đã tìm.</p>}</>}{plan.warnings.map(warning => <p key={warning}>{warning}</p>)}</div>
}
