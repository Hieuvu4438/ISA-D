import type { Category, ExclusionInterpretation } from '../lib/types'
import { categoryLabels } from '../ui'

export function ExclusionInterpretationNotice({ plan }: { plan?: ExclusionInterpretation }) {
  if (!plan?.applied) return null
  const labels = { category: 'Loại sản phẩm', brand: 'Thương hiệu', color: 'Màu' }
  return <div className="submitted-context" role="status" aria-label="Điều kiện loại trừ đã hiểu"><p>Đã loại trừ theo mô tả:</p><div className="effective-filters">{plan.clauses.map(clause => <span key={`${clause.field}:${clause.value}`}>{labels[clause.field]}: {clause.field === 'category' ? categoryLabels[clause.value as Category] : clause.value}</span>)}</div><p>{[...new Set(plan.clauses.map(clause => `“${clause.text}”`))].join('; ')}. Điều kiện này kết hợp với bộ lọc bạn chọn. Có thể sửa mô tả hoặc tắt tự hiểu loại trừ rồi tìm lại.</p></div>
}
