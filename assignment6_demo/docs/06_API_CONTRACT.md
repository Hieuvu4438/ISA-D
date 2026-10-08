# Hợp đồng HTTP API

Revision 1. Tài liệu này là chuẩn giao tiếp giữa React và FastAPI. Implementation phải sinh OpenAPI tương ứng, bổ sung example cho cả success/error và kiểm tra contract ở integration tests. Tên Python nội bộ có thể khác; tên JSON, enum, HTTP status và đơn vị dưới đây phải giữ nguyên.

## Quy ước chung

- Routes nghiệp vụ có prefix `/api/v1`. Health ở `/health/live`, `/health/ready`, ngoài prefix. Các route trong bảng dưới đây là URL đầy đủ của backend, không phải route React.
- JSON UTF-8, tiền VND số nguyên, thời gian ISO 8601 UTC kết thúc `Z`. Cosine là độ tương đồng, không phải xác suất. Không trả embedding, đường dẫn máy chủ, biến môi trường, key hoặc payload lỗi Azure.
- Mọi JSON response có `request_id` do server tạo UUID; header `X-Request-ID` cùng giá trị. Error đặt ID trong `error.request_id`. Không dùng request ID client làm định danh quyền hoặc ghi trực tiếp chuỗi client vào log.
- Body JSON bắt buộc `Content-Type: application/json`; multipart để browser tự sinh boundary. Sai media type 415. JSON sai cú pháp, key trùng, NaN/Infinity là 400 `INVALID_JSON`; đúng JSON nhưng sai schema là 422. Form key lặp/không được khai báo là 422.
- Mọi object input dùng `extra="forbid"`; query params không có trong route contract cũng 422. `null` chỉ được chấp nhận tại các trường được ghi nullable. Object `options`, `filters` có thể bỏ qua để dùng default nhưng không được là `null`.
- Số nguyên JSON phải là integer thực sự, không nhận `true`, `1.0` hay `"1"`. Trường số thực nhận number hữu hạn, loại boolean/string. Dùng strict validation; không dựa vào coercion mặc định.
- Mọi response JSON search/transcription/order và meta dùng `Cache-Control: no-store`. Response image có cache theo mục media; browser không cache upload trên server.
- Client không được cung cấp `customer_id` trong body/query, hoặc các header `customer_id`, `Customer-Id`, `X-Customer-ID`, `X-Demo-Customer-ID` bất kể hoa thường. Trả 422 `CLIENT_CUSTOMER_CONTEXT_FORBIDDEN`. Backend xác định Customer từ `DEMO_CUSTOMER_ID=C001`.
- POST không tự retry. `retryable=true` chỉ gợi ý UI hiển thị thao tác thử lại do người dùng chủ động; không đồng nghĩa request đã được hủy ở provider. Timeout/abort không cho response cũ ghi đè UI mới; xem 07 và 08.

## Danh mục endpoint

| Method | URL | Input | Success | Dependency chính |
| --- | --- | --- | --- | --- |
| GET | `/api/v1/meta` | Không có query | 200 `MetaResponse` | Trạng thái an toàn, catalog nếu hợp lệ |
| GET | `/api/v1/products` | `offset`, `limit` | 200 `ProductListResponse` | Catalog |
| GET | `/api/v1/products/{product_id}` | ID `P` + 3 chữ số | 200 `ProductDetailResponse` | Catalog |
| GET | `/api/v1/credits` | Không có query | 200 `CreditsResponse` | Catalog + image manifest |
| GET | `/api/v1/media/products/{product_id}` | ID như trên | 200 bytes ảnh | Catalog + stored image allowlist |
| POST | `/api/v1/search` | JSON text/voice | 200 `SearchResponse` | Model + catalog/index snapshot |
| POST | `/api/v1/search/image` | Multipart | 200 `SearchResponse` | Như trên + decoder ảnh |
| POST | `/api/v1/search/multimodal` | Multipart | 200 `SearchResponse` | Như trên |
| POST | `/api/v1/speech/transcriptions` | Multipart WAV | 200 `TranscriptionResponse` | Azure Speech cấu hình thật |
| GET | `/api/v1/orders` | `order_id` bắt buộc | 200 `OrderSummaryResponse` | Order repository + server scope |
| GET | `/api/v1/orders/{order_id}` | ID `O` + 3 chữ số | 200 `OrderDetailResponse` | Như trên |
| GET | `/health/live` | Không có query | 200 `LiveResponse` | Process/event loop |
| GET | `/health/ready` | Không có query | 200 hoặc 503 `ReadyResponse` | Semantic search readiness |

Catalog, media và order phải hoạt động khi model/index/Azure unavailable nếu dependency riêng của route còn hợp lệ. Không dùng một middleware readiness toàn cục chặn tất cả route.

## SearchOptions dùng chung

```json
{
  "top_k": 5,
  "result_policy": "nearest",
  "filters": {
    "category": null,
    "brand": null,
    "min_price": null,
    "max_price": null,
    "in_stock": false
  }
}
```

| Field | Kiểu/default | Validation và nghĩa |
| --- | --- | --- |
| `top_k` | integer, default 5 | 1–20 inclusive |
| `result_policy` | string, default `nearest` | Chỉ `nearest` hoặc `relevant` |
| `filters.category` | string hoặc null, default null | `running_shoes|trail_shoes|casual_shoes|boots|sandals|bag|backpack|tote_bag|t_shirt|jacket|watch|sunglasses` trong `/meta.filters.categories`; `null` là không lọc |
| `filters.brand` | string hoặc null, default null | Giá trị chính xác trong `/meta.filters.brands`; NFC+trim, không đoán thương hiệu |
| `filters.min_price` | integer hoặc null, default null | 0–1,000,000,000 VND, bao gồm cận; JSON key giữ tên `min_price` |
| `filters.max_price` | integer hoặc null, default null | 0–1,000,000,000 VND, bao gồm cận; nếu cả hai có giá trị thì min ≤ max |
| `filters.in_stock` | boolean, default false | `true` chỉ giữ stock_quantity >0; `false` giữ cả còn/hết hàng |

`""`, category/brand lạ, giá âm, min lớn hơn max đều 422; không biến filter sai thành một truy vấn rộng hơn. Bỏ options tương đương `{}`. Response luôn trả options với đầy đủ default và nullable fields như ví dụ. `/products` không nhận SearchOptions và không xếp hạng semantic.

## POST /api/v1/search — text và transcript voice

```json
{
  "mode": "text",
  "text": "giày chạy bộ màu đen",
  "options": { "top_k": 5, "result_policy": "nearest" }
}
```

```json
{
  "mode": "voice",
  "text": "Tôi cần giày chạy bộ màu đen.",
  "voice_source": "azure",
  "options": { "top_k": 3 }
}
```

- `mode` bắt buộc, chỉ `text|voice`; `text` bắt buộc string. Với text mode, không được gửi `voice_source`, kể cả null. Với voice mode, `voice_source` bắt buộc và chỉ `azure|local|manual_transcript`.
- Chuẩn hóa `text`: Unicode NFC, trim, gộp các whitespace thành một dấu cách; giữ dấu/chữ hoa chữ thường để hiển thị. Sau chuẩn hóa phải 1–500 Unicode code points và tối đa **128 tokenizer tokens kể cả special tokens**, dùng tokenizer của multilingual model với `truncation=False`. Frontend đếm ký tự bằng code points, không dùng UTF-16 `.length` để kết luận hợp lệ. Backend có quyền quyết định cuối.
- Quá ký tự/token trả 422 `TEXT_TOO_LONG`, field `text`, trước inference. Không silent truncate. Tokenizer unavailable là 503 `MODEL_UNAVAILABLE`, không bỏ qua giới hạn token.
- Voice text đi cùng pipeline encoder text. `voice_source` là thông tin workflow do client khai báo, có thể sửa transcript; **không phải chứng thực** rằng Azure đã nhận dạng và không ảnh hưởng quyền truy cập. UI chỉ gắn nhãn Azure khi chính phiên đó nhận transcript thật. Không có receipt/token Azure trong SearchRequest.
- Nhập transcript thủ công vẫn gọi mode voice với `manual_transcript`; nhãn UI “Transcript nhập tay · mô phỏng”. Không dùng để nghiệm thu Azure STT.

## POST /api/v1/search/image và /multimodal

Multipart image:

| Part | Bắt buộc | Dữ liệu |
| --- | --- | --- |
| `image` | Có | Một file bytes JPEG/PNG/WebP |
| `options` | Không | String JSON object `SearchOptions`; thiếu tương đương `{}` |

Multipart multimodal:

| Part | Bắt buộc | Dữ liệu |
| --- | --- | --- |
| `image` | Có | Như image mode |
| `text` | Có | String, normalize/500 ký tự/128 tokens như `/search` |
| `text_weight` | Không | Form string biểu diễn JSON number hữu hạn trong [0.1,0.9], default `0.5`; không nhận boolean |
| `options` | Không | String JSON object `SearchOptions` |

`options` không phải các form field `top_k`, `filters[brand]` hay một JSON body riêng. Backend parse JSON object rồi strict validate, loại key trùng/NaN/unknown field. Options sai cú pháp là 400 `INVALID_JSON` field `options`; sai schema là 422 field như `options.top_k`. `text_weight="0.5"` trong form hợp lệ; `text_weight="\"0.5\""`/`true`/rỗng không hợp lệ. Không gửi `mode` trong multipart: route xác định mode. Không nhận URL hoặc path thay bytes.

Giới hạn ảnh thực thi cả trước/sau decode:

- File tối đa **5 MiB = 5,242,880 bytes**, không rỗng; vượt bytes 413 `IMAGE_TOO_LARGE`.
- Chỉ JPEG, PNG, WebP. Sniff/decode bytes thực tế; không tin extension/filename hoặc MIME của client. SVG/GIF/HEIC/animated image/multi-frame bị từ chối. Declared image MIME phải tương thích decoded format; `application/octet-stream` được sniff như file upload không khai báo MIME. Unsupported type 415 `IMAGE_TYPE_UNSUPPORTED`.
- Dimensions trước decode đầy đủ phải >0, mỗi cạnh ≤8192; width × height ≤**16,000,000 pixels**. Giới hạn được áp trên ảnh gốc trước resize; vượt 413 `IMAGE_DIMENSIONS_EXCEEDED`. Decompression-bomb warning/error phải được xử lý thành lỗi hữu hạn.
- Decode thất bại/truncated bytes/mismatch MIME 422 `IMAGE_INVALID`; orientation, alpha và preprocess theo 05. Không truyền tên file client vào filesystem hay shell.
- JSON body `/search` ≤16 KiB. Text parts/options tổng ≤16 KiB; tổng multipart ảnh ≤6 MiB, audio ≤2 MiB. Enforce streaming cap trước model/provider và giới hạn số parts; không chỉ tin `Content-Length`. Oversize envelope 413 `REQUEST_TOO_LARGE`.

## SearchResponse

Ví dụ minh họa shape; số score/timing là dữ liệu ví dụ, không phải kết quả model đã chạy:

```json
{
  "request_id": "9caee945-8634-43d0-bbd9-05b2b603ee98",
  "query": {
    "mode": "text",
    "text": "giày chạy bộ màu đen",
    "voice_source": null,
    "image_summary": null,
    "text_weight": null,
    "options": {
      "top_k": 1,
      "result_policy": "nearest",
      "filters": {
        "category": null, "brand": null,
        "min_price": null, "max_price": null, "in_stock": false
      }
    }
  },
  "results": [
    {
      "rank": 1,
      "product": {
        "product_id": "P001", "name": "Giày chạy bộ đen",
        "category": "running_shoes", "brand": "Thương hiệu từ catalog",
        "color": "đen", "price_vnd": 1500000, "in_stock": true,
        "image_url": "/api/v1/media/products/P001"
      },
      "score": 0.731234,
      "component_scores": { "text": 0.731234, "image": null }
    }
  ],
  "meta": {
    "model_fingerprint": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "index_fingerprint": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "catalog_fingerprint": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "result_policy": "nearest",
    "threshold": null,
    "policy_fingerprint": null,
    "empty_reason": null,
    "timing_ms": {
      "validation": 1.0, "encoding": 45.0, "retrieval": 1.0,
      "filtering": 0.1, "threshold": 0.0, "ranking": 0.1, "hydration": 0.2, "total": 48.5
    },
    "trace": [
      { "step": "validation", "status": "ok", "input_count": 1, "output_count": 1 },
      { "step": "encoding", "status": "ok", "input_count": 1, "output_count": 1 },
      { "step": "retrieval", "status": "ok", "input_count": 1, "output_count": 12 },
      { "step": "filtering", "status": "ok", "input_count": 12, "output_count": 12 },
      { "step": "threshold", "status": "skipped", "input_count": 12, "output_count": 12 },
      { "step": "ranking", "status": "ok", "input_count": 12, "output_count": 1 },
      { "step": "hydration", "status": "ok", "input_count": 1, "output_count": 1 }
    ]
  }
}
```

Count trace hydration phải bằng đúng `results.length`; count minh họa chỉ hợp lệ nếu runtime thực sự có snapshot 12 sản phẩm và options tương ứng.

Quy tắc fields:

| Field | Contract |
| --- | --- |
| `query.mode` | `text|voice|image|multimodal` |
| `query.text` | Normalized string cho text/voice/multimodal; null cho image |
| `query.voice_source` | `azure|local|manual_transcript` ở voice; null ở các mode khác |
| `query.image_summary` | `{format:"JPEG"|"PNG"|"WEBP",width:integer,height:integer,byte_size:integer}` cho image/multimodal; null cho text/voice; dimensions gốc đã validate |
| `query.text_weight` | Number [0.1,0.9] ở multimodal; null ở mode khác |
| `results` | Array, có thể `[]`; không null. Rank liên tiếp từ 1, product_id không trùng |
| `score` | Cosine hữu hạn [-1,1], precision đủ cho xếp hạng, không làm tròn trước sort; serialize tối thiểu 6 chữ số thập phân khi có precision |
| `component_scores` | Luôn object `{text:number|null,image:number|null}`; null tương ứng input không có |
| fingerprints | Đúng 64 ký tự hex thường `^[a-f0-9]{64}$`, không prefix; SHA256 của snapshot thực sự dùng. Các chuỗi a/b/c trong example chỉ minh họa schema; runtime không có placeholder hoặc fingerprint null cho search success |
| `threshold` | Null trong nearest; number [-1,1] trong relevant có policy hợp lệ |
| `policy_fingerprint` | Null trong nearest; fingerprint policy đã calibration trong relevant |
| `empty_reason` | Null khi results có phần tử; `catalog_empty|filters|threshold` khi results rỗng |
| `timing_ms` | Các fields cố định trong example, number hữu hạn ≥0, monotonic clock; total bao gồm chờ slot, validation và xử lý đến DTO; không gồm ghi mic/upload/network browser |
| `trace` | Bảy steps cố định theo đúng thứ tự example, status `ok|skipped`, counts integer ≥0; nearest threshold `skipped`/count giữ nguyên/timing0; relevant threshold `ok`; là bước thật đã chạy, không stack trace/raw input |

Score chính dùng cùng product vector `V=unit(0.5*T+0.5*I)` theo 05. Text/voice: `q_text·V`; image: `q_image·V`; multimodal: `unit(w*q_text+(1-w)*q_image)·V`. Components lần lượt `q_text·V` và `q_image·V` khi có input. Score fusion **không phải** trung bình có trọng số trực tiếp của component scores vì query được chuẩn hóa lại.

Filter toàn bộ catalog trước threshold và Top-k, stable tie theo product_id. `nearest` có threshold/policy null và UI nhãn “Sản phẩm gần nhất”. `relevant` không có policy tương thích fingerprint/mode/weight trả 503 `RELEVANCE_POLICY_UNAVAILABLE`, không tự chuyển nearest. Voice chia sẻ text policy; multimodal weight `.5` phải calibration cho bản demo hoàn chỉnh, weight khác chỉ relevant khi có policy tương ứng. Empty 200 chỉ khi pipeline hợp lệ: ưu tiên `catalog_empty` nếu catalog rỗng, `filters` nếu sau hard filter không có candidate, `threshold` nếu relevant loại tất cả. Không dùng empty che model/index lỗi.

Search deadline backend 10s từ nhận đủ body qua validation/queue/inference/DTO, browser 15s. Timeout→504 `SEARCH_TIMEOUT`, retryable=true; không auto retry. Timeout khi còn queue phải loại request trước encoder; inference active giữ slot tới native completion và response muộn bị bỏ theo03/07. Voice transcription có deadline riêng bên dưới.

## POST /api/v1/speech/transcriptions

| Part | Bắt buộc/default | Validation |
| --- | --- | --- |
| `audio` | Bắt buộc file | WAV RIFF PCM signed 16-bit little-endian, mono, 16,000 Hz, 1–15 giây inclusive, ≤1 MiB =1,048,576 bytes |
| `language` | Không; default `vi-VN` | Baseline chỉ cho phép `vi-VN`; language khác 422 |

Không nhận WebM/Opus/MP3, không tự transcode server, không nhận path/URL. Browser mic tạo WAV theo 08. File WAV đúng signature nhưng wrong codec/rate/channels/bit depth/length/header/data size trả 422 `AUDIO_INVALID`; format khác 415 `AUDIO_TYPE_UNSUPPORTED`; vượt bytes 413 `AUDIO_TOO_LARGE`. Duration tính từ actual valid frames/16,000, không tin metadata của client. Validation phải xong trước Azure.

```json
{
  "request_id": "89707e66-772c-40ce-b8b6-fbe16f1bce48",
  "transcript": "Tôi cần giày chạy bộ màu đen.",
  "language": "vi-VN",
  "provider": "azure",
  "audio_duration_ms": 4200,
  "timing_ms": { "validation": 1.0, "provider": 1840.0, "total": 1842.0 }
}
```

Success có transcript NFC+trim không rỗng; không thêm trường confidence bịa đặt. Transcript được trả để người dùng sửa, **chưa gọi search**. Nếu transcript dài hơn giới hạn search, UI yêu cầu rút ngắn trước submit; không tự cắt. Azure NoMatch/recognized text rỗng 422 `SPEECH_NO_MATCH`; deadline 25s sau upload 504; browser chờ tối đa 30s. Chi tiết sanitized mapping và resource lifecycle ở 08.

## Product/catalog/media contracts

`ProductSummary` fields chính xác như SearchResponse: `product_id`, `name`, `category`, `brand`, `color`, `price_vnd`, `in_stock`, `image_url`; tất cả bắt buộc và không null. `color` là nhãn tiếng Việt; category là slug; brand/name lấy catalog đúng ảnh thật, không suy từ vector. Stock/price là dữ liệu demo, UI ghi rõ. Category examples `running_shoes|casual_shoes|trail_shoes|bag`; giá trị thực lấy `/meta`.

GET `/products?offset=12&limit=12`: offset default 0 integer ≥0; limit default 12 integer 1–100. Query HTTP string được parse theo decimal digits, không boolean/float/key lặp. Thứ tự product_id tăng ổn định; không nhận text/top_k/filters. Ví dụ với catalog 12 sản phẩm:

```json
{
  "request_id": "c1b27a8a-fd07-4fb2-b011-b6b6dbb0aebc",
  "products": [], "total": 12, "offset": 12, "limit": 12
}
```

Array rỗng hợp lệ nếu offset ≥ total. `total` là tổng catalog đã validate, không phải số kết quả semantic.

GET `/products/P001`: response `{request_id,product:ProductDetail}`. Detail bao gồm toàn bộ Summary và:

```json
{
  "description": "Mô tả tiếng Việt đúng đối tượng trong ảnh.",
  "stock_quantity": 8,
  "image_credit": {
    "source_page": "https://commons.wikimedia.org/wiki/File:EXAMPLE.jpg",
    "author": "Tác giả đã kiểm tra ở trang nguồn",
    "license": "Giấy phép đã kiểm tra",
    "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "transformations": ["resize"]
  }
}
```

Object minh họa credit không dùng làm nguồn thực. Credit phải hydrate từ manifest đã xác minh theo [04_DATA_CONTRACTS.md](04_DATA_CONTRACTS.md) và [IMAGE_CREDITS.md](IMAGE_CREDITS.md); `source_page`, `author`, `license`, `license_url` đều bắt buộc string không rỗng/không null, URLs hợp lệ HTTPS, không dùng URL ví dụ. `transformations` array string có thể rỗng; nếu manifest seed lưu một narrative string, adapter trả array một phần tử chứa nguyên string đó. Không trả internal `image_path`, `image_asset_id`, hash filesystem. `in_stock=(stock_quantity>0)`; price_vnd integer0–1,000,000,000, stock_quantity integer0–1,000,000.

GET `/api/v1/credits`: response `{request_id,credits:CreditEntry[]}`; mỗi entry gồm `asset_id`, `product_id` và toàn bộ fields của `image_credit`. `asset_id` là định danh public từ manifest, không phải filesystem path. Sort theo product_id; một entry cho mỗi ảnh chính sản phẩm trong catalog; credit không có generated asset. Catalog/manifest rỗng hợp lệ trả `[]`; hỏng dependency trả503 `CATALOG_UNAVAILABLE`. Route dùng cho trang `/credits`, không cần fetch từng product detail hoặc load model. Không trả download_url/original_url/local_path/checksum private qua endpoint này.

GET `/media/products/P001` chỉ resolve ID→stored image đã được ingest/checksum/allowlist. Không có query path/url/filename, không mount toàn bộ data directory. Dùng content type decoded ảnh, `X-Content-Type-Options: nosniff`, ETag từ image checksum; conditional request hợp lệ có thể 304. Unknown product 404 `PRODUCT_NOT_FOUND`; ảnh known product bị thiếu/corrupt 503 `PRODUCT_IMAGE_UNAVAILABLE`; không trả ảnh gen hoặc ảnh thay thế như ảnh sản phẩm. UI dùng placeholder trung tính với alt khi file ảnh lỗi.

## Order contracts và demo Customer

GET `/orders?order_id=O001`: `order_id` bắt buộc string, normalize trim + ASCII uppercase rồi validate `^O[0-9]{3}$`; key lặp/rỗng/sai shape 422. Response `{request_id,order:OrderSummary}`.

```json
{
  "request_id": "a4b4496c-2dff-438a-a453-d684c9557f82",
  "order": {
    "order_id": "O001", "date": "2026-09-20T03:00:00Z",
    "status": "delivered", "total_vnd": 3000000
  }
}
```

GET `/orders/O001`: path ID canonical uppercase; response `{request_id,order:OrderDetail}`. Detail có toàn bộ summary và `items` array không rỗng:

```json
{
  "items": [
    {
      "product_id": "P001", "product_name": "Giày chạy bộ đen",
      "quantity": 2, "unit_price_vnd": 1500000, "line_total_vnd": 3000000
    }
  ]
}
```

`date` ISO UTC, status chỉ `processing|shipped|delivered|cancelled`; quantity integer1–100, tiền integer ≥0. Giá/tên item là snapshot lúc tạo seed order, không tính lại từ catalog hiện tại. `line_total_vnd=quantity*unit_price_vnd`; total là tổng lines. Không trả địa chỉ, số điện thoại hoặc dữ liệu khách thật. Không có pagination/fuzzy/semantic order search, POST order, thanh toán hay cập nhật trạng thái.

Repository lookup kết hợp `customer_context` server và ID; cả O002 thuộc C002 và O999 thiếu đều 404 với cùng code/message `ORDER_NOT_FOUND`/“Không tìm thấy đơn hàng.” Không trả `exists`, owner, khác status code hoặc đếm đơn khách khác. Catalog endpoint không nhận customer context. Đây là demo một khách, chưa thay cho auth production.

## GET /meta và health

`MetaResponse` luôn 200 nếu process hoạt động; không gọi Azure/model download để probe. Các field cố định:

| Field | Type/meaning |
| --- | --- |
| `request_id`, `api_version` | UUID; string `v1` |
| `capabilities.catalog`, `.orders`, `.search` | Object `{available:boolean,reason_code:string|null}`; available false phải có reason an toàn |
| `capabilities.manual_transcript` | Object `{available:true,reason_code:null}`: nhập tay không cần Azure; gọi search vẫn cần search readiness |
| `capabilities.relevant` | Object `{available:boolean,modes:string[],multimodal_weights:number[],reason_code:string|null}` theo policy hiện tại; modes chỉ text/voice/image/multimodal có policy |
| `speech` | `{provider:"azure"|"local",configuration_state:"unconfigured"|"configured_unverified",language:"vi-VN",region:"southeastasia"|null,accepted_formats:["wav_pcm16_mono_16000"],max_duration_seconds:15,max_bytes:1048576}` |
| `model` | `{text_model_id:string,image_model_id:string,text_revision:string|null,image_revision:string|null,dimension:512,model_fingerprint:string|null}`; revisions/fingerprint null khi chưa có artifact hợp lệ |
| `index` | `{available:boolean,index_fingerprint:string|null,catalog_fingerprint:string|null,product_count:integer}` |
| `filters` | `{available:boolean,categories:string[],brands:string[],min_price:integer|null,max_price:integer|null}`; arrays sort ổn định, min/max từ catalog hoặc null khi rỗng/unavailable |
| `limits` | `{text_max_characters:500,text_max_tokens:128,top_k_max:20,image_max_bytes:5242880,image_max_pixels:16000000,image_max_dimension:8192,text_weight_min:0.1,text_weight_max:0.9}` |

Model IDs cố định trong 05. Không trả local cache paths, key suffix, Azure endpoint/token, auth status giả hoặc `azure_connected=true` từ việc env có giá trị. Configuration thiếu/sai→unconfigured; cấu hình cú pháp hợp lệ→configured_unverified. Region trong meta là cấu hình dự kiến, chưa chứng minh key thực thuộc region. Meta an toàn phải vẫn trả trạng thái degrade nếu catalog/index hỏng; `product_count=0` ở unavailable không đồng nghĩa catalog thực sự rỗng. Relevant available chỉ khi có ít nhất một policy hợp lệ; UI kiểm tra mode/weight riêng.

`LiveResponse`: `{request_id,status:"live"}` HTTP 200 khi event loop hoạt động. Không hứa model/search/Azure sẵn sàng.

`ReadyResponse`: `{request_id,status:"ready"|"not_ready",search_available:boolean,reason_codes:string[]}`. HTTP 200 nếu catalog+model+index snapshot tương thích và search inference worker hoạt động; 503 nếu không. Worker đang phục vụ một lượt nhưng còn healthy không tự làm readinessfalse. Đây là exception health body có schema status riêng, không dùng error envelope. reason codes allowlist `CATALOG_UNAVAILABLE|MODEL_UNAVAILABLE|INDEX_MISSING|INDEX_STALE|INDEX_CORRUPT|INDEX_OUT_OF_SYNC|SEARCH_WORKER_UNAVAILABLE`; không chứa exception text. Policy/Azure availability phản ánh riêng ở meta; readiness search không chứng minh nghiệm thu toàn demo.

## Error envelope và mapping

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Vui lòng kiểm tra dữ liệu nhập.",
    "field_errors": [{ "field": "options.top_k", "message": "Top-k phải từ 1 đến 20." }],
    "retryable": false,
    "request_id": "c83a43ee-7f27-4bd7-9a90-881fa80aa7c8"
  }
}
```

Tất cả fields bắt buộc; `field_errors=[]` nếu không gắn field. Field là dotted path (`text`, `audio`, `image`, `options.filters.min_price`), không trả input bị lỗi. Route/HTTPException/Pydantic/unhandled exception phải đi qua handler chung; không lộ mặc định `detail`, traceback, input hoặc SDK error_details. Những lỗi health readiness dùng schema riêng đã nêu. Message tiếng Việt ổn định; UI switch theo code, không parse message.

| HTTP | Code | Retryable | Trường hợp |
| --- | --- | --- | --- |
| 400 | `INVALID_JSON` | false | JSON/options syntax, duplicate key, nonfinite literal |
| 413 | `REQUEST_TOO_LARGE`, `IMAGE_TOO_LARGE`, `IMAGE_DIMENSIONS_EXCEEDED`, `AUDIO_TOO_LARGE` | false | Limit thực tế vượt |
| 415 | `MEDIA_TYPE_UNSUPPORTED`, `IMAGE_TYPE_UNSUPPORTED`, `AUDIO_TYPE_UNSUPPORTED` | false | Content/file type ngoài contract |
| 422 | `VALIDATION_ERROR`, `TEXT_TOO_LONG`, `IMAGE_INVALID`, `AUDIO_INVALID`, `CLIENT_CUSTOMER_CONTEXT_FORBIDDEN` | false | Schema/domain input sai |
| 422 | `SPEECH_NO_MATCH` | false | Không nhận dạng được; người dùng có thể ghi lại |
| 404 | `PRODUCT_NOT_FOUND`, `ORDER_NOT_FOUND`, `ROUTE_NOT_FOUND` | false | Không tìm thấy trong phạm vi cho phép |
| 405 | `METHOD_NOT_ALLOWED` | false | Method sai; header Allow đúng route |
| 429 | `SEARCH_BUSY` | true | Search queue đầy; `Retry-After: 2` |
| 429 | `SPEECH_BUSY`, `SPEECH_RATE_LIMITED` | true | Voice worker/quota giới hạn; `Retry-After: 5` hoặc số giây provider đã validate |
| 502 | `SPEECH_AUTH_FAILED` | false | Upstream auth/forbidden; cần sửa server config, không expose provider message |
| 502 | `SPEECH_UPSTREAM_FAILED` | true | Provider connection/service/runtime failure sau mapping sanitized |
| 503 | `CATALOG_UNAVAILABLE`, `ORDERS_UNAVAILABLE`, `MODEL_UNAVAILABLE`, `INDEX_MISSING`, `INDEX_STALE`, `INDEX_CORRUPT`, `INDEX_OUT_OF_SYNC`, `SEARCH_WORKER_UNAVAILABLE`, `PRODUCT_IMAGE_UNAVAILABLE` | false | Artifact/server dependency cần sửa; không response fake |
| 503 | `RELEVANCE_POLICY_UNAVAILABLE`, `SPEECH_UNAVAILABLE` | false | Policy hoặc speech config/SDK unavailable |
| 504 | `SPEECH_TIMEOUT` | true | SDK/provider deadline; UI thử lại chủ động |
| 504 | `SEARCH_TIMEOUT` | true | Search deadline 10s kể cả queue; UI thử lại chủ động, native slot giữ đến completion |
| 500 | `INVALID_VECTOR`, `INTERNAL_ERROR` | false | Encoder/fusion tạo vector không hợp lệ hoặc lỗi không dự kiến; log sanitized theo request_id |

## Checklist implement/test contract

- Generate TS DTO/client từ OpenAPI hoặc kiểm tra typed DTO tương đương; strict validation hai phía, server quyết định cuối. Multipart model cần OpenAPI examples rõ thay vì chỉ mô tả generic body.
- Test mỗi route success + validation, missing/null/default/unknown/duplicate/boolean-number boundary; token boundary dùng tokenizer thật và over-limit không gọi encode. Image/audio fixture đúng format và malformed phải đi tới decoder thật; không chỉ mock file extension.
- Test `/search` không nhận image mode, text không nhận voice_source, voice phải có provenance; options form JSON và weight parsing phải phù hợp examples.
- Test search count/rank/score/component/meta/fingerprint/empty_reason nhất quán với 05; relevant policy missing và unsupported weight đều 503.
- Test products/credits/order không cần model; credits khớp toàn catalog/manifest; foreign/missing order cùng envelope; forbidden context ở body/query/header không đổi scope.
- Test health degrade và meta không gọi Azure tại startup/readiness; no secrets/vectors/path/raw provider payload trong response/log.
- Giữ tests xử lý NoMatch/timeout/rate/auth bằng adapter stub được ghi nhãn test. Live Azure smoke riêng là evidence bắt buộc trước nghiệm thu FR-03, không chạy mặc định CI.

## Mở rộng STT local theo yêu cầu 08/10/2026

`POST /speech/transcriptions` giữ WAV/language/timing/error contract; response `provider` là `azure|local`. `/meta.speech.provider` phản ánh adapter đã chọn, local có `region=null`; trạng thái `configured_unverified` chỉ xác nhận model đã nạp/cấu hình, không bảo đảm độ chính xác. Client timeout speech95s, backend local tối đa90s; không auto retry, native slot giữ đến khi inference kết thúc. Search voice nhận và trả `voice_source=local`. Settings chọn một adapter rõ ràng, local không gọi Azure/budget; xem [LOCAL_SPEECH](LOCAL_SPEECH.md).
