# Dữ liệu, ảnh thật và schema

## Nguồn dữ liệu

Catalog demo ít nhất 12 sản phẩm P001–P012. Giá/tồn kho/đơn hàng là dữ liệu giả định; tên, brand, màu và mô tả ảnh phải phù hợp với ảnh thật. Không dùng stock image của túi cho một sản phẩm giày hoặc cùng ảnh cho nhiều SKU để tăng số sản phẩm.

Đợt đặc tả chuẩn bị `data/images/`, `data/image_sources.json`, `data/products.json`, `data/orders.json` để người dùng review. Backend sau này validate và đọc chúng qua repository. Query fixtures/evaluation/index sẽ được xây trong đợt implement; không coi việc có seed là search đã chạy được.

## Product nội bộ

`products.json`: JSON array, mỗi record có đúng các trường sau; extra fields là lỗi dataset.

```json
{
  "product_id": "P001",
  "name": "Giày chạy bộ On Cloud màu đen",
  "brand": "On",
  "category": "running_shoes",
  "color": "đen",
  "price_vnd": 1800000,
  "stock_quantity": 10,
  "description": "Giày chạy bộ màu đen, thân vải lưới và đế có các khoang rỗng.",
  "image_path": "data/images/P001.jpg",
  "image_asset_id": "P001"
}
```

| Trường | Ràng buộc |
| --- | --- |
| product_id | String `^P[0-9]{3}$`, duy nhất; sort lexicographic tăng |
| name / description | NFC, không rỗng; name ≤120, description ≤500 ký tự; combined embedding text không vượt 128 tokens |
| brand | String có căn cứ trong ảnh/source; không rõ dùng `Không xác định`, không gán Nike từ ảnh giày bất kỳ |
| category | `running_shoes`, `trail_shoes`, `casual_shoes`, `bag`; nhãn UI tiếng Việt riêng |
| color | Mô tả tiếng Việt từ ảnh, có thể nhiều màu; không suy vật liệu/hiệu năng chưa được source xác nhận |
| price_vnd | Strict integer 0–1,000,000,000, reject boolean; giá demo, không float hoặc tự đổi USD |
| stock_quantity | Strict integer 0–1,000,000; `in_stock = stock_quantity > 0` |
| image_path | Relative dưới `data/images`; resolve trong root, file tồn tại, decode được, không symlink ra ngoài |
| image_asset_id | Một asset manifest tồn tại, local_path đúng image_path; mỗi ảnh chính gắn đúng SKU |

Catalog không phục vụ trực tiếp raw `image_path`. API tạo `/api/v1/media/products/P001`. ProductSummary/Detail và wire names được định nghĩa đầy đủ trong [06_API_CONTRACT.md](06_API_CONTRACT.md). Internal model dùng stock_quantity, external summary dùng in_stock để tránh khác tên.

## Order nội bộ và quyền truy cập

`orders.json`: JSON array với các trường `order_id`, `customer_id`, `date`, `status`, `items`, `total_vnd`. Có ít nhất O001/O003 của C001 và O002 của C002; một đơn có nhiều item để kiểm tra tổng tiền.

```json
{
  "order_id": "O001",
  "customer_id": "C001",
  "date": "2026-10-01T08:30:00Z",
  "status": "shipped",
  "items": [{
    "product_id": "P001",
    "product_name": "Giày chạy bộ On Cloud màu đen",
    "quantity": 1,
    "unit_price_vnd": 1800000,
    "line_total_vnd": 1800000
  }],
  "total_vnd": 1800000
}
```

Order ID `^O[0-9]{3}$`, customer ID `^C[0-9]{3}$`; date ISO-8601 UTC; status `processing|shipped|delivered|cancelled`; items không rỗng, quantity strict integer 1–100, các giá cùng VND không âm. `line_total_vnd = quantity × unit_price_vnd`; `total_vnd = sum(line_total_vnd)`. Không shipping fee/tax ngầm. Snapshot name và giá của item được giữ nguyên khi giá catalog đổi; current product_id phải tồn tại trong catalog demo. Không sửa stock khi chỉ xem/tìm đơn hàng.

Lookup thực hiện đồng thời `(customer_id server, order_id)`; missing và foreign đều 404 cùng message. Không dùng CLIP/RankingService cho order. External detail không trả customer_id, địa chỉ, số điện thoại hay thông tin thật. C001 là bối cảnh demo cố định, không phải auth production.

## Manifest ảnh thật

```json
{
  "schema_version": 1,
  "assets": [{
    "asset_id": "P001",
    "product_id": "P001",
    "local_path": "data/images/P001.jpg",
    "source_page": "https://commons.wikimedia.org/wiki/File:On_Clouds_running_shoes.jpg",
    "download_url": "https://upload.wikimedia.org/…",
    "original_url": "https://upload.wikimedia.org/…",
    "author": "Tên tác giả từ source",
    "license": "CC BY-SA 4.0",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "retrieved_at": "2026-10-08",
    "sha256": "64 ký tự hex của file lưu thật",
    "bytes": 123456,
    "transformations": "Wikimedia thumbnail; không chỉnh sửa local",
    "real_photo_review": "passed"
  }]
}
```

Ví dụ trên mô tả schema, các giá trị hash/bytes/author phải lấy từ manifest thật, không dùng nguyên placeholder. Manifest thực tế có thêm description nguồn, width/height/format và review_evidence/review_notes sau kiểm tra; validator cho phép đúng các trường bổ sung này. `transformations` nội bộ là narrative string; API chuyển thành array một phần tử theo 06. author và license_url bắt buộc có giá trị trong bộ demo.

Khi thêm query assets, dùng ID `Q...`, `product_id=null`, local_path dưới `data/queries`; giữ toàn bộ provenance/checksum/visual-review contract. Product assets vẫn bắt buộc product_id tồn tại; không ép query OOD vào một SKU có sẵn. Query manifest records không được trả như credit sản phẩm bởi `/api/v1/credits`; ảnh dùng để demo query cần ghi nguồn ở evidence riêng.

Quy trình bổ sung ảnh:

1. Tìm ảnh chụp đối tượng rõ, ưu tiên nguồn có quyền dùng minh bạch như Wikimedia Commons. Mở trang file và đọc tác giả/license từng ảnh, không suy license từ domain.
2. Tải binary vào folder này, không hotlink runtime. Không bypass login/paywall, không dùng ảnh AI/synthetic/render hoặc ảnh không rõ nguồn.
3. Kiểm tra file signature, decode, kích thước; tính SHA256; kiểm tra bằng mắt đúng là ảnh chụp thật và phù hợp metadata. Metadata/EXIF là hỗ trợ, không tự chứng minh mọi ảnh là thật.
4. Ghi source page, original/download URL, author, license link, ngày và biến đổi; nếu thumbnail từ host thì ghi rõ. Giữ nghĩa vụ share-alike cho chính asset được chia sẻ nếu áp dụng.
5. Credit ở product detail và trang `/credits`; nguồn/source/license là external links, không dùng để backend fetch theo request khách hàng.
6. Thay byte ảnh hoặc mô tả→rebuild index và calibration. Ảnh được tải, kiểm tra từ mạng mới được vào catalog; không sinh ảnh bù khi download fail.

[Bảng xem nhanh ảnh](assets/asset-contact-sheet.jpg) chỉ là contact sheet ghép các ảnh đã tải để review, không phải ảnh sản phẩm synthetic. Ảnh chủ thể trong `data/images` được giữ nguyên byte đã tải. Khi implement làm bảng credit theo manifest để đáp ứng điều kiện mỗi file.

## Query và Candidate trong bộ nhớ

Query có `mode:text|voice|image|multimodal`, `vector:float32[512]`, `text_vector|null`, `image_vector|null`, `input_summary`, `options`, `text_weight|null`, `voice_source|null`. Query không phải entity persisted và vector không trả browser. Candidate có product_id, score, component_scores. SearchResult ghép đúng Product với Candidate; không composition làm xóa Product khi xóa result.

`options` wire schema ở 06: top_k, result_policy, filters. Thay options không được sửa catalog. Tiền, tồn kho được lọc bằng metadata; chỉ có text/image signals trong cosine, không thêm business score ngầm.

## Chỉ mục NPZ và metadata

`runtime/index/vectors_<fingerprint>.npz` có `ids: unicode[N]`, `text_vectors:float32[N,512]`, `image_vectors:float32[N,512]`, `product_vectors:float32[N,512]`. Load `allow_pickle=False`, reject object dtype, shape sai, duplicate IDs, NaN/Inf, norm zero. Unit norm tolerance 1e-5. N bằng catalog, ids tăng dần và đủ tập IDs. Empty catalog test có N=0, matrix shape `(0,512)` hợp lệ, không gọi encode batch rỗng; gate dataset demo vẫn yêu cầu ≥12 sản phẩm.

Trước `numpy.load`, inspect ZIP directory: đúng bốn `.npy` entries, không duplicate/path traversal, file NPZ≤16MiB, tổng declared uncompressed bytes≤32MiB và header lengths bị giới hạn; reject trước allocation nếu vượt. Đây là cap prototype12–100, không tự nâng cap bằng metadata từ file hỏng. Sidecar checksum và shape expected từ snapshot được kiểm tra cả trước/sau load để chặn truncated/ZIP-bomb cache.

Sidecar `vectors_<fingerprint>.json` có schema_version, fingerprint, dataset_sha256, model IDs + commit revisions, package versions, preprocess_version, text_template_version, product_text_weight=.5, dimension=512, dtype=float32, sorted_ids, image_sha256_by_id, npz_sha256, created_at. Không credentials hoặc đường dẫn ngoài workspace. Fingerprint chi tiết ở 05.

`runtime/policies/relevance_<fingerprint>.json` chứa policy cho text/image/multimodal(.5), threshold hữu hạn [-1,1], scoring_version, calibration split hash, model/index fingerprint, weights, metrics và ngày. NPZ hoặc policy không khớp snapshot phải bị từ chối; không reuse ngưỡng khi đổi model/ảnh/template.

Mọi fingerprint/hash trong sidecar, filenames và API dùng **64 ký tự hex thường** (`^[a-f0-9]{64}$`), không prefix `sha256:`. Chỉ tên thuật toán trong schema mô tả SHA256; giá trị định danh không có `:` để dùng hợp lệ trong filename Windows.
