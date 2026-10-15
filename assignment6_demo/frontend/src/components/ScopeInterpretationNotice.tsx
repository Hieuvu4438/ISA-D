import type { Category, ScopeInterpretation } from '../lib/types'
import { categoryLabels } from '../ui'

export function ScopeInterpretationNotice({ plan }: { plan?: ScopeInterpretation }) {
  if (!plan?.applied && !plan?.warnings.length) return null
  return <div className="submitted-context" role="status" aria-label="Phạm vi tìm kiếm đã hiểu">{plan.applied && <><p>Đang tìm trong phạm vi từ mô tả:</p><div className="effective-filters">{plan.clauses.map(clause => <span key={`${clause.field}:${clause.value}`}>{clause.field === 'category' ? categoryLabels[clause.value as Category] : clause.value}</span>)}</div><p>Các lựa chọn cùng hãng hoặc loại được nối bằng “hoặc”. Bộ lọc bạn chọn vẫn áp dụng. Có thể tắt tự hiểu hãng và loại rồi tìm lại để mở rộng.</p></>}{plan.warnings.map(warning => <p key={warning}>{warning}</p>)}</div>
}
