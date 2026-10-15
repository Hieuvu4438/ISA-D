# Tìm theo kích cỡ và tồn kho đúng SKU — 15/10/2026

`áo thun size M`, `giày cỡ 42`, `kích cỡ XL` nay lọc theo kích cỡ đã khai báo trong SQLite, trước ranking/top-k. Không suy size từ ảnh, tên sản phẩm, kho gốc hoặc độ tương đồng AI. Hành vi áp dụng đồng nhất cho catalog, suggestions, semantic/hybrid, manual transcript và multimodal có text.

## Quy tắc

- Nhận marker `size`, `cỡ`, `kích cỡ`; hỗ trợ không dấu `co M`, `kich co XL`, không phân biệt hoa/thường, NFC/NFD. Nhận dạng viết liền `sizeM`, `size40`, `size3XL` với cỡ được hỗ trợ.
- Cỡ canonical theo hợp đồng SKU26: XS/S/M/L/XL/XXL/3XL, 34–48 và ONE. Admin tiếp tục giới hạn cỡ theo category. Cỡ hợp lệ nhưng không được sản phẩm khai báo trả rỗng; sản phẩm chưa phân cỡ không tự trở thành ONE hoặc M.
- `size M hoặc L`, `cỡ 40 hoặc 42`: OR trong cùng trường; giao với category/hãng/màu/giá/manual filters. `size M` + filter L trả 422 `SCOPE_FILTER_CONFLICT`, `field_errors[].field=filters.size` hoặc `options.filters.size`. OR M/L kết hợp filter L chỉ giữ L.
- Mặc định có thể xem sản phẩm đã khai báo cỡ M dù cỡ đó hết hàng. Bật `in_stock=true` yêu cầu **chính cỡ M** còn hàng, kể cả tổng kho sản phẩm vẫn dương nhờ cỡ L. OR nhiều cỡ yêu cầu ít nhất một cỡ được chọn còn hàng; manual size vẫn áp dụng riêng.
- Cỡ lạ/thiếu, nhánh OR thiếu, AND/dấu phẩy không rõ, `M/L`, `40-42`, `40.5`, `40,5`, so sánh `>=40`, OR chéo trường hoặc phủ định size chưa được xử lý: giữ query, bỏ automatic scope và hiển thị warning để sửa/chọn filter. Không làm tròn, quy đổi EU/US/UK hoặc thay cỡ gần nhất.
- `42` đứng riêng không phải size. Phân biệt từ tiếng Việt `có` với `cỡ`; `áo có màu trắng` không bị hiểu là một kích cỡ. `co` không dấu chỉ là marker ngắn khi theo sau bằng cỡ canonical; trường hợp không rõ vẫn có bộ lọc thủ công.

Tính size dựa trên cùng snapshot definition/quantity/revision/archive. Autocomplete đã được sửa để hydrate stock/variants trước khi lọc, không dùng seed quantity cũ. AI search tạo bản sao metadata cho mỗi request, tránh ghi snapshot stock/variants vào repository dùng chung.

## API và UI

Giữ `interpret_scope=true` như docs30/33. `clauses[].field` thêm `size`; `value` là cỡ canonical, `text` giữ span cỡ gốc. Parser version `brand_category_color_size_scope_v3`; lexical fingerprint chứa version mới. Model/catalog/index/cosine không đổi, không rebuild embedding vì thêm parser. Số lượng, giá và schema đặt hàng không đổi.

```json
{"enabled":true,"parser_version":"brand_category_color_size_scope_v3","applied":true,"clauses":[{"text":"áo thun","field":"category","value":"t_shirt"},{"text":"m","field":"size","value":"M"}],"lexical_text":"","warnings":[]}
```

Checkbox đổi thành “Tự hiểu hãng, loại, màu và kích cỡ”. Notice ghi “Cỡ M” và hướng dẫn bật “Chỉ còn hàng”. Card tìm kiếm và catalog ghi tồn của cỡ đã tìm, ví dụ `Cỡ M: hết hàng`, có nhãn `Hết cỡ đã tìm` dù L còn hàng. Với OR, chỉ liệt kê các cỡ mục tiêu mà sản phẩm có. Điều kiện size thủ công được ưu tiên khi hiển thị. Card dùng điều kiện của response đã nhận, không dùng draft mới chưa submit. ProductSummary vẫn giữ tổng stock/in_stock và available_sizes đúng hợp đồng26, không đổi nghĩa các trường để phục vụ riêng query.

False bỏ scope size cùng hãng/category/color và warning, không bỏ manual filters/price/exclusions. Catalog URL/Back/reload giữ opt-out như trước. Không tự chọn cỡ hoặc thêm vào giỏ thay khách; detail tiếp tục yêu cầu chọn SKU rõ ràng.

```mermaid
sequenceDiagram
  actor U as Người mua
  participant API as Search / Catalog / Suggestions
  participant P as Price → Exclusions → Scope
  participant DB as SQLite inventory snapshot
  participant R as Retrieval và ranking
  U->>API: Câu có size + bộ lọc
  API->>P: Nhận marker, cỡ canonical, OR và conflict
  alt Scope mâu thuẫn bộ lọc
    P-->>U: 422 và field_errors, giữ query
  else Scope hợp lệ hoặc warning
    API->>DB: Đọc variants + stock + revision + archive
    DB-->>R: Snapshot đồng nhất
    P-->>R: Scope size hoặc query giữ nguyên và warning
    R->>R: Lọc size tồn tại; nếu in_stock thì đúng size còn hàng
    R->>R: Ranking và top-k trên tập hợp lệ
    R-->>U: ProductSummary + scope notice + trạng thái từng cỡ
  end
```

Mapping: ScopeInterpreter/ScopePlan, CatalogSearch, SearchService, shared domain size constants/AdminService, ScopeInterpretationNotice và ProductCard. Mermaid không thay Visual Paradigm editable còn pending.

## Evidence và giới hạn

[SIZE_SCOPE_REPORT](../artifacts/backend/SIZE_SCOPE_REPORT.md) tách doubles, fresh SQLite lifecycle, browser và actual CPU. Browser dùng fixture P041-M/L đã có từ luồng phân size26, tạm đặt M=0, giữ L>0 và khôi phục toàn bộ product sau test; không giả dữ liệu model. Clean checkout cần admin khai báo cỡ theo26 trước khi demo tìm theo size có kết quả; unit HTTP test tự tạo cỡ trong DB sạch và kiểm tra sau restart ứng dụng.

Tham khảo chính thức [Shopify variant-option filtering](https://shopify.dev/docs/storefronts/headless/building-with-the-storefront-api/products-collections/filter-products) về lọc theo lựa chọn biến thể và availability. Đây là nguồn thiết kế, không phải dữ liệu hoặc bằng chứng test Cortis. Các cỡ/tồn kho trong dự án là demo, không phải bảng size thương hiệu thực.

Không gọi STT hay dịch vụ trả phí. Manual voice không phải bằng chứng Groq/Azure hoạt động. Half-size, size guide có số đo, quy đổi hệ size, color/price variants, các nhóm ảnh còn lỗi, independent relevance/OOD và full acceptance còn pending. Thanh toán tiếp tục COD/demo theo ưu tiên người dùng.
