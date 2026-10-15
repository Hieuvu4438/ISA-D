# Soạn sản phẩm và ảnh cho admin

Ưu tiên người dùng mới: thanh toán giữ COD/demo; không mở rộng cổng thanh toán, hoàn tiền thực hoặc các edge cases thương mại nâng cao. Tập trung hoàn thiện tìm kiếm và quản lý sản phẩm để sớm bàn giao. Các yêu cầu mới này ưu tiên trên ma trận mở rộng cũ ở15.

Mốc authoring bổ sung bản nháp riêng cho metadata/ảnh. **Chưa xuất bản catalog/index**, chưa phải hoàn tất module quản lý sản phẩm. Luồng xuất bản đồng bộ là bước tiếp theo; không dùng nút lưu bản nháp để giả đã cập nhật cửa hàng.

Thiết kế tham khảo [Shopify product status](https://help.shopify.com/en/manual/products/add-update-products) và [media management](https://shopify.dev/docs/apps/build/product-merchandising/products-and-collections/manage-media): tách soạn nội dung khỏi dữ liệu phục vụ khách, giữ nguồn ảnh. Cortis không dùng Shopify runtime.

## Dữ liệu và API

SQLite `catalog_drafts(product_id,version,base_fingerprint,payload,asset,validation,updated_at)` cùng commerce DB đã ignore. Metadata chỉ name/brand/category/color/price_vnd/description. Giá strict integer VND0–1e9, text NFC/whitespace normalized, reject control chars/extra fields. Version tăng sau save/image/preflight/discard; tombstone giữ version sau discard để chống stale write sau xóa/tạo lại. Base fingerprint phải khớp catalog hiện tại. Mọi mutation kiểm admin/active/auth_epoch trong write transaction, CAS và audit commit cùng nhau.

| Method | Route sau `/api/v1/admin` | Contract |
|---|---|---|
| GET | `/products?q=&status=draft|live&offset=0&limit=20` | List metadata tối thiểu; count trước phân trang; q≤120; max100/page; unknown/duplicate query422 |
| GET | `/products/Pnnn/draft` | Có mã live trả metadata gốc/version0 nếu chưa soạn; mã mới trả template rỗng. Không tạo DB record khi đọc. |
| POST | `/products/Pnnn/draft` | `{version,base_catalog_fingerprint,product}`; save chỉ nháp; trả draft/version mới |
| POST | `/products/Pnnn/draft/image` | Multipart image/version/provenance JSON; intent admin. Ảnh≤5MiB, JPEG/PNG/WebP single-frame,≤16M pixels/dimension8192, decode/signature/MIME thật. |
| GET | `/products/Pnnn/draft/image?v=version` | Admin-only, checksum/size/allowlist path; stale v409; không public mount |
| POST | `/products/Pnnn/draft/preflight` | `{version}`; bounded CPU runner kiểm text token/ảnh/unit vectors512D/fusion; kết quả chỉ commit nếu vẫn đúng version/epoch. Timeout không commit muộn. |
| POST | `/products/Pnnn/draft/discard` | `{version}`; xóa nội dung nháp, giữ version và catalog live |

Ảnh provenance bắt buộc source_page/original_url/download_url HTTPS không credentials, author/license/license_url, retrieved_at YYYY-MM-DD không tương lai, transformations và real_photo_review=passed. Đây là xác nhận bằng mắt của admin, không phải bộ phát hiện ảnh synthetic. Backend không fetch URL do client gửi; file bytes nguyên gốc lưu content-addressed SHA256 dưới runtime/catalog/assets. Không dùng tên file upload làm đường dẫn. Hash/size/decode được kiểm trước preview/preflight. Ảnh trùng SKU catalog khác hoặc nháp khác bị từ chối để không nhân số sản phẩm bằng ảnh cũ. File orphan sau rollback/discard được giữ private; chưa có GC/quota toàn bộ kho, cần bổ sung trước triển khai public.

Public DTO không trả local_path, reviewed_by hay request body audit. Draft credit link được render dưới dạng link HTTPS, React không render raw HTML. Lưu mới/sửa ảnh làm mất validation cũ. Preflight là encoding property, **không đánh giá relevance, không build index và không publish**; MODEL_UNAVAILABLE phải báo lỗi thật. Không gọi STT/provider.

Ảnh authoring mới P181 ở `data/authoring/` là ảnh thật Auckland Museum tải từ Commons, source/checksum/review riêng. Chưa đưa vào products.json/image_sources catalog, không thay catalog180 hoặc vector hiện tại. Brand Nike theo mô tả museum; không suy từ ảnh nghiêng. Giá890000 là demo. Attribution CC BY4.0 và URL ảnh thu nhỏ/gốc ở P181-source.json; giữ nguyên byte tải.

## UI và UML

Trang `/admin`, mục Sản phẩm: tìm/lọc/phân trang, mở mã, sửa metadata, lưu, tải ảnh/nguồn/xác nhận ảnh thật, kiểm tra encoder, xem preview và xóa bản nháp có xác nhận. Đổi sản phẩm khi dirty có cảnh báo giữ/bỏ; chuyển tab admin giữ editor mounted, reload có beforeunload cho metadata chưa lưu. Input nguồn ảnh dạng uncontrolled được reset theo draft version, chưa có autosave/persist cho form ảnh chưa gửi. Lỗi CAS/network giữ metadata, có nút tải server rõ việc bỏ thay đổi. Anonymous/user bị từ chối API, cả ảnh nháp.

```mermaid
sequenceDiagram
  actor A as Admin
  participant UI as AdminCatalogPanel
  participant API as Catalog draft routes
  participant S as CatalogDraftService
  participant DB as CatalogDraftRepository
  participant E as CPU encoder
  A->>UI: Edit metadata and image provenance
  UI->>API: Save with version/base fingerprint/intent
  API->>S: Validate DTO
  S->>DB: Lock, admin/epoch/CAS, save and audit
  DB-->>UI: Draft version; live catalog unchanged
  A->>UI: Explicit preflight
  UI->>API: Version
  API->>E: Bounded text/image encoding, pure computation
  E-->>S: Valid512D vectors or typed failure
  S->>DB: Recheck version/epoch and record result
  DB-->>UI: Encoder checked, still unpublished
```

Code: domain/catalog_draft.py DTO; data/catalog_draft_repository.py transactions; data/draft_image_storage.py bytes/path/checksum; application/catalog_draft_service.py workflow/inference; presentation/catalog_drafts.py routes; main.py DI. Source Mermaid ne thay `.vpp`; publication/archival/color variants và full-system acceptance vẫn pending.

Evidence xem `artifacts/backend/CATALOG_DRAFTS_REPORT.md`; test doubles, encoder thật và browser phải ghi riêng.
