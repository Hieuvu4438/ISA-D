# AI tìm kiếm tiếng Việt và chỉ mục

## Model pair bắt buộc

| Vai trò | Model ID | Commit revision đã tra cứu 08/10/2026 |
| --- | --- | --- |
| Text tiếng Việt | `sentence-transformers/clip-ViT-B-32-multilingual-v1` | `58edf8cada9e398793dca955574a48cbb7f18be2` |
| Ảnh CLIP ViT-B/32 | `sentence-transformers/clip-ViT-B-32` | `327ab6726d33c0e22f920c83f2ff9e4bd38ca37f` |

Multilingual model card liệt kê `vi`, output 512D và hướng dẫn dùng CLIP gốc để encode ảnh. Đây là căn cứ chọn pair; không phải chứng minh mọi truy vấn tiếng Việt tìm đúng. [Model card](https://huggingface.co/sentence-transformers/clip-ViT-B-32-multilingual-v1).

Dùng `SentenceTransformer(..., device="cpu", revision=...)`, `encode(..., convert_to_numpy=True, normalize_embeddings=True)` qua adapter. Tải model trong bước setup, lưu vào `runtime/models`, ghi model/package revisions ở `runtime/models/model_manifest.json`; chạy inference local offline. Không download model trong mỗi request. `trust_remote_code=False` nếu loader có hỗ trợ; dùng adapter chính thức, không import Python tùy ý từ model repo.

M0 smoke test phải xác nhận text/ảnh shape (B,512), norm, dtype, encode tiếng Việt không lỗi và model files thực sự ở workspace. Trước khi lock version, đối chiếu API Sentence Transformers thực cài. Không dùng embedding từ model 384/768D rồi pad/cắt thành512; không dùng text CLIP English thay cho multilingual mà vẫn ghi tiếng Việt verified.

## Tiền xử lý

- Text user: Unicode NFC, trim/gộp whitespace, giữ dấu; 1–500 chars, tokenize không truncation, tổng sequence gồm special tokens ≤128 theo multilingual encoder. Quá giới hạn→422 `TEXT_TOO_LONG`; không cắt âm thầm. Bản gốc normalized hiển thị trong query summary.
- Text product: `"{name}. Thương hiệu: {brand}. Loại: {category_label_vi}. Màu: {color}. {description}"`, version `product_text_v1_vi`; không nhét giá/stock vào embedding. Validate tổng tokens≤128; description phải sửa có chủ đích nếu quá dài.
- Ảnh: validate trước inference theo 06; Pillow EXIF transpose, chuyển RGB; alpha composite nền trắng; dùng image processor đi kèm model cho resize/crop/normalize. Version `image_rgb_exif_white_v1`. Không áp custom histogram hoặc bóp ảnh hình học thay processor.
- Mỗi batch offline tối đa8 khởi điểm, query batch1; torch eval/inference mode, float32 CPU. Không float16 CPU như default. Threads đề xuất min(4, CPU logical count), đo và ghi cấu hình thực.

## Công thức chung

Gọi `unit(x)=x/||x||₂`, chỉ khi x đúng chiều, hữu hạn và norm>1e-12. Mọi vector sau unit phải hữu hạn và norm≈1.

Với sản phẩm p:

```text
T[p] = unit(text_encoder(product_text[p]))
I[p] = unit(image_encoder(product_image[p]))
V[p] = unit(0.5*T[p] + 0.5*I[p])
```

Query text/voice `q=unit(text_encoder(normalized_text))`; image `q=unit(image_encoder(decoded_image))`; multimodal:

```text
qt = unit(text_encoder(text))
qi = unit(image_encoder(image))
q  = unit(lambda*qt + (1-lambda)*qi)
lambda = text_weight, default 0.5, strict finite number in [0.1, 0.9]
score[p] = dot(q, V[p])
```

Product fusion weight .5 cố định baseline, query weight khác product weight. Cả hai là quyết định demo chưa chứng minh tối ưu. Khi q trước unit gần zero trả `INVALID_VECTOR`, không chia zero. Float accumulation ưu tiên float32/64 nhất quán rồi output JSON finite number. Cho phép clip giá trị lệch [-1,1] trong tolerance1e-5; lệch lớn báo lỗi, không che invalid vector.

Components để giải thích: `text=dot(qt,V[p])` nếu có text, `image=dot(qi,V[p])` nếu có ảnh; signal vắng là null. Với text/voice hoặc image đơn, score bằng component tương ứng. Với multimodal score **không** đơn giản là .5*text+.5*image do normalization q; quan hệ đúng:

```text
score = (lambda*component_text + (1-lambda)*component_image)
        / norm(lambda*qt + (1-lambda)*qi)
```

Không softmax hoặc `logit_scale` để biến score thành xác suất/độ chính xác. UI hiện “Độ tương đồng cosine”, giá trị 3 chữ số thập phân; backend rank dùng full precision, không rank bằng score đã làm tròn.

## Retrieval, filter, ranking

```text
validate request and readiness
query = QueryService.build_*(input, options)
snapshot = immutable catalog + index with same fingerprint
candidates = all rows of snapshot.V @ query.vector
assert all candidate ids exist in snapshot catalog
eligible = hard_filter(candidates, metadata, options.filters)
if result_policy == relevant:
    policy = require matching calibrated policy(mode, text_weight, fingerprint)
    eligible = [c for c in eligible if c.score >= policy.threshold]
sort by (-full_precision_score, product_id ascending)
selected = eligible[:top_k]
hydrate only selected product metadata and credits
return results + trace + effective options + policy metadata
```

Filter price inclusive `min_price ≤ price_vnd ≤ max_price`; category/brand bằng equality trên allowlist; stock>0 nếu in_stock=true. Không có filter thì tất cả candidate eligible. Filter giá strict integer, min>max là422. `top_k≤20`, N<k trả tối đa N. Không clamp k sai sang default hoặc thêm sản phẩm khác để đủ k.

O(Nd) cho exact scan, full sort O(N log N), catalog nhỏ≤100 baseline. Không lấy top candidates từng modality trước fusion. “Candidate union” trong prototype cũ được thay bởi exact all-catalog scoring để tránh mất ứng viên. Khi mở rộng ANN phải chứng minh recall trước đổi.

## Empty và ngưỡng liên quan

- `nearest`: threshold=null, trả gần nhất sau filters; nếu catalog/filter rỗng trả results=[] với empty_reason phù hợp. UI ghi rõ chưa lọc mức liên quan.
- `relevant`: threshold từ calibration hợp lệ, lọc trước Top-k; tất cả bị loại→200 empty_reason=threshold.
- Thiếu policy hay weight chưa được calibration→503 `RELEVANCE_POLICY_UNAVAILABLE`, frontend gợi ý chọn nearest. Đây là trạng thái setup thiếu, không phải đã đạt luồng semantic empty.
- Voice transcript dùng policy text; STT accuracy đo riêng. Text/image/multimodal default .5 có ngưỡng riêng, không lấy một threshold chung. Custom lambda ở relevant chỉ mở khi có policy đúng weight; baseline UI dùng nearest khi chỉnh slider và yêu cầu user tìm lại.

## Calibration có thể tái lập

Chuẩn bị `evaluation/queries.json`: ít nhất60 cases, mỗi split calibration/test có5 positive+5 OOD cho từng mode text/image/multimodal(.5). Fields: query_id, family_id, split, mode, text|null, image_path|null, text_weight|null, filters, expected_product_ids[], is_ood. Text tiếng Việt; OOD phải thực sự không có đối tượng tương ứng trong catalog. Bổ sung mẫu âm thanh thật5 cases riêng theo 10.

Split theo family_id/nguồn ảnh/góc chụp và cụm diễn đạt để không dùng cùng câu hoặc byte ảnh cho calibration và test. Image queries thật từ nguồn mạng có credit riêng, ưu tiên góc khác catalog. Same-image self-match chỉ kiểm tra mechanics; không tính như independent quality result. Danh sách expected IDs được người review gán từ nhu cầu và ảnh trước khi chạy model, không sinh từ current top result.

1. Freeze/hash các splits. Thu full candidate scores sau filters với model/index hiện tại trên calibration.
2. Thử threshold [-1,1] tại các score quan sát và các midpoint phân biệt, thêm boundaries; apply predicate `>=` đúng như runtime.
3. Tính positive Hit@3 (số positive có ít nhất một expected ID trong top3 sau threshold / số positive), OOD rejection (số OOD empty / số OOD).
4. Policies khả thi phải positive Hit@3≥.80 và OOD rejection≥.60 trên calibration. Chọn policy Hit@3 lớn nhất; nếu hòa chọn threshold nhỏ nhất trong các policy khả thi. Ghi cả confusion/false rejection, không chỉ successes.
5. Không có policy khả thi→đánh dấu chưa calibration thành công; kiểm tra chất lượng metadata/ảnh/encoder, ghi quyết định và tiếp tục cải thiện. Không đặt .90 từ ví dụ toán trong CONTEXT.
6. Publish policy fingerprint; chạy test split độc lập theo cùng thuật toán; report từng mode. Thất bại test là gate fail, không đổi nhãn/xóa case khó để đạt.

## Cache fingerprint và publish

Fingerprint SHA256 canonical JSON UTF-8 sort keys + product IDs sorted, bao gồm mọi record metadata, SHA256 byte ảnh theo ID, model IDs+commit revisions, các package versions encoder, dimension/dtype, preprocess/template/scoring/schema versions, product fusion weight. Fingerprint luôn có 64 ký tự hex thường, không prefix `sha256:`, thống nhất filenames/API theo04. Không hash mtime đơn thuần. Query weight không đổi catalog index nhưng là khóa calibration policy.

Builder offline tạo temporary NPZ/JSON, validate all rows/IDs/norms/checksums, flush và publish atomic. Một process giữ builder lock có timeout, process thứ hai không ghi đè tạm; lock chỉ là cơ chế loại trừ, phải xác minh PID/liveness để xử lý lock cũ. Xuất NPZ trước rồi sidecar hoàn chỉnh, loader không nhận cặp thiếu/hash sai. Một lần build thất bại giữ cache cũ; cache cũ chỉ dùng nếu fingerprint vẫn khớp, không vì “còn file”.

Startup tải snapshot chỉ khi đủ validate. Missing/stale/corrupt→search unavailable, hướng dẫn `build_index.py`; catalog/order vẫn sử dụng được nếu dataset hợp lệ. Nếu phát hiện index chứa ID không tồn tại→503 `INDEX_OUT_OF_SYNC`, không bỏ qua rồi gắn score vào product khác. Không hot-reload dữ liệu trong process; build và restart theo runbook.

Evidence benchmark/relevance phải lưu fingerprint, package locks, CPU/OS, thời gian và per-query results. Điểm số mẫu toán 2D không được trình bày như kết quả CLIP thật.
