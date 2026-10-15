# Xuất bản sản phẩm, ảnh và index đồng bộ

Mốc tiếp theo authoring27, base141b825. Admin có thể **tạo/sửa sản phẩm và ảnh rồi xuất bản lên cửa hàng local**, không cần sửa JSON/restart thủ công. Không triển khai public. Thanh toán giữ COD/demo theo ưu tiên mới của người dùng; payment/refund integrations được hoãn.

## Luồng thực thi

1. Admin lưu metadata và ảnh có provenance như27. Nút “Xuất bản sản phẩm” mở xác nhận inline, không tự gọi lúc startup/CI. Preflight riêng vẫn có thể dùng nhưng publication tự kiểm dữ liệu/model/index nên không tin nhãn preflight cũ.
2. POST `/api/v1/admin/products/Pnnn/draft/publish` với JSON `{version}`, intent admin, session/Origin checks. Dùng CPU runner chung với tìm kiếm, một native task active; giới hạn30s server/40s client. Khi quá thời gian chỉ còn computation/file staging, **không activation muộn**. Lỗi không auto retry. Nếu HTTP mất sau commit, tải lại draft/product/meta để đối chiếu; không tự gửi publication lần nữa.
3. Application tạo immutable release dưới `runtime/catalog/releases/<uuid32>/data/`: products/manifest/ảnh byte copies riêng. Không sửa seed hoặc release cũ; không dùng URL do browser gửi để fetch. ProductRepository validate lại toàn bộ metadata/provenance/hash/decode trước index build. Uploaded PNG/WebP có thể dùng tên nội bộ `.jpg` nhưng MIME luôn lấy từ nội dung decode; không ép chuyển byte ảnh.
4. Build index trên encoder CPU hiện tại. Reuse text/image vectors **chỉ** khi model/catalog cũ khớp và record product cùng SHA ảnh không đổi; SKU thay đổi được encode lại thật, không random/keyword vectors. Giữ công thức fusion512D. Validate NPZ/sidecar/fingerprint/full ID set trước khi tạo SearchService/CatalogSearch mới. Không reuse ngưỡng relevance của index cũ.
5. Sau staging, gate async ngắn ngăn HTTP readers mới và đợi requests hiện tại kết thúc; các search native đã timeout giữ reference SearchService cũ, không trộn index mới vào request cũ. Trong gate, DB transaction recheck admin/epoch/draft version/base; ghi pointer `catalog_publication`, revision, audit và tombstone draft cùng transaction. Source category đã có size không được đổi để tránh sai hệ size.
6. Sau durable commit, không await trước khi thay references products/index/search/catalog_search và Shopping/Purchase/Admin/Draft services. Gate nhả, HTTP mới dùng cùng snapshot. Stock ledger không reset. Product mới inventory0, admin nhập tồn tại Tồn kho. Quote cũ kiểm metadata/giá và từ chối khi có thay đổi; đơn/return đã tạo giữ snapshot.

SQLite pointer `catalog_publication(singleton=1,release_path,catalog_fingerprint,index_fingerprint,revision)` là nguồn quyết định. Restart đọc pointer trong chính account DB đang dùng, validate path UUID dưới workspace, catalog checksum và index fingerprint. Không fallback âm thầm sang seed nếu release hỏng. Khi load_models=false, catalog vẫn đọc release nhưng semantic search unavailable như trước. Một worker bắt buộc; chưa có shared activation giữa nhiều process.

Các nháp sản phẩm khác được rebase sang catalog mới, xóa validation và tăng version vì chính product của chúng chưa thay đổi. Tab đang mở phải reload trước khi lưu; nội dung nháp giữ nguyên. Không tự rebase khi source file bị sửa ngoài ứng dụng; runbook cấm sửa seed trong lúc serve.

## API và giao diện

Response200 `{request_id,publication:{published:true,product_id,revision,catalog_fingerprint,index_fingerprint,relevant_available},draft}`. `draft.has_draft=false` sau activation; published=false trong draft DTO vẫn chỉ có nghĩa không còn nội dung nháp đã xuất bản riêng, xem publication object để xác nhận activation. New products xuất hiện trong `/products`, `/catalog`, `/suggestions`, `/credits`, media và cả4 search modes; wishlist/cart hydrate metadata mới.

Lỗi chính:401/403 identity/role/CSRF;409 DRAFT_CHANGED/CATALOG_CHANGED/DRAFT_IMAGE_REQUIRED/CATEGORY_HAS_VARIANTS;503 MODEL_UNAVAILABLE/CATALOG_RELEASE_UNAVAILABLE/INDEX_OUT_OF_SYNC;422 text/token/provenance;504 bounded task timeout. Giữ draft khi staging/validation/audit thất bại; runtime staged files không tự xóa để tránh xóa file native task đang dùng. Chưa có GC/quota/version rollback UI; cần trước production quy mô lớn. Không hard delete product/order/asset lịch sử.

Giao diện báo rõ cửa hàng local, xác nhận xuất bản, tiến trình chuẩn bị index, giữ nội dung khi lỗi và yêu cầu reload cửa hàng sau success. Mức liên quan (`relevant`) cần calibration lại cho index mới; `nearest`/hybrid vẫn hoạt động với bộ lọc cứng và score thật. Không tự gán threshold mới để che dependency.

## UML/code mapping

```mermaid
sequenceDiagram
  actor A as Admin
  participant API as Draft publication route
  participant P as CatalogPublication
  participant E as CPU encoder/index builder
  participant G as HTTP catalog gate
  participant DB as CatalogDraftRepository SQLite
  participant S as Application services
  A->>API: Explicit publish with draft version
  API->>P: Bounded prepare
  P->>P: Immutable release and full ProductRepository validation
  P->>E: Reuse unchanged vectors; encode changed products
  E-->>P: Validated index + fingerprint
  P-->>API: Prepared services, no live mutation
  API->>G: Drain readers and acquire writer
  API->>DB: Recheck role/epoch/version/base; commit pointer + audit
  alt Transaction failed
    DB-->>A: Typed failure, current snapshot retained
  else Committed
    API->>S: Replace catalog/search/commerce references without await
    API->>G: Release readers
    S-->>A: Publication fingerprints and fresh draft state
  end
```

Code: application/catalog_publication.py orchestration, application/index_builder.py incremental vector reuse, data/catalog_draft_repository.py durable activation, catalog_gate.py drain, main.py DI/startup/reference wiring. Data không gọi encoder. Source UML không thay `.vpp`.

## Demo và evidence

P181 ảnh Auckland Museum đã visual-review/provenance ở data/authoring được đưa vào runtime bằng browser admin thật. Sau publication catalog local181 products, P181 stock0; catalog seed checkout vẫn180 cho tới khi admin publish. Không commit runtime DB/index/release. Clean checkout: setup model/index seed như README rồi admin tạo/mở draft, upload fixture ảnh/nguồn, publish và nhập stock. Model không tải hoặc gọi provider lúc publish.

Evidence [CATALOG_PUBLICATION_REPORT](../artifacts/backend/CATALOG_PUBLICATION_REPORT.md) tách doubles, browser, encoderCPU và restart thật. Image self-match chỉ là property smoke; voice manual transcript không phải STT. Chưa claim full search relevance hoặc toàn ecommerce complete. Product archive/restore, color/price variants, dữ liệu còn lỗi và independent query evaluation là việc còn lại; không mở rộng payment provider trong mốc ưu tiên.
