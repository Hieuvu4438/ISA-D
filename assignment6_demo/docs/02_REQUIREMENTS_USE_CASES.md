# Yêu cầu và use case website

Revision 1. Các từ **phải** là điều kiện bắt buộc để nghiệm thu website; **đề xuất** là giả định có thể điều chỉnh bằng evidence và cập nhật đặc tả.

## Scope và actor

Actor chính Customer, được trình diễn với C001. Azure Speech là dịch vụ ngoài hệ thống ở sơ đồ triển khai/sequence, không thay thế actor Customer. Search by Keyword giữ tên Assignment, xử lý bằng semantic encoder. Ba mode text/voice/image là specialization của Search Product; multimodal là specialization bổ sung.

| FR | Hành vi bắt buộc | Use case |
| --- | --- | --- |
| FR-01 | Nhận yêu cầu tìm sản phẩm, trả danh sách hoặc empty hợp lệ | UC-01 |
| FR-02 | Mô tả tiếng Việt có dấu và câu gần nghĩa được mã hóa text | UC-02 |
| FR-03 | Ghi mic hoặc upload WAV, Azure nhận dạng tiếng Việt, sửa transcript rồi tìm | UC-03 |
| FR-04 | Upload ảnh thật hợp lệ, tìm tương đồng ảnh | UC-04 |
| FR-05 | Tìm mã đơn hàng chính xác thuộc C001 | UC-05 |
| FR-06 | Mở chi tiết sản phẩm, back giữ trạng thái tìm kiếm | UC-06 |
| FR-07 | Mở chi tiết đơn hàng thuộc C001 | UC-07 |
| FR-08 | Retrieval, filter, threshold, rank ổn định, Top-k; hiện score hữu hạn | UC-01 |
| FR-09 | Kết hợp text tiếng Việt + ảnh, thay trọng số text, tìm lại | UC-08 |
| FR-10 | Filter category, brand, min/max price, in_stock; Top-k 1–20 | UC-01 |
| FR-11 | Hiện input, mode, các bước xử lý và timing cho demo | UC-01/03/08 |
| FR-12 | Input lỗi/dependency lỗi có thông báo, recovery; không trả kết quả giả | Tất cả |
| FR-13 | Catalog dùng ảnh chụp thật trên mạng, có nguồn/giấy phép/credit | UC-06 |

## Quy tắc chung

Text NFC, trim, gộp whitespace; giữ dấu tiếng Việt và chữ gốc để hiển thị. Không dịch bằng bảng từ khóa; không bỏ dấu làm đường xử lý duy nhất. Bộ lọc cứng lấy từ control UI, không infer giá/tồn kho từ cosine. Có một request đang active cho mỗi workflow; response cũ không được ghi đè request mới.

`nearest` trả sản phẩm gần nhất trong tập sau filter, không khẳng định liên quan. `relevant` lọc theo policy đã calibration. Empty nêu nguyên nhân `filters`/`threshold`/`catalog_empty`; thiếu model/index/policy là lỗi dependency, không giả empty.

## Luồng use case

| UC | Trigger và main flow | Alternate/error flow | Postcondition |
| --- | --- | --- | --- |
| UC-01 Search Product | Chọn mode→nhập input→đặt options→submit→validate→encode→retrieve→filter/rank→results | Input 422; readiness 503; empty 200; request lỗi giữ input | Grid kết quả mới hoặc lỗi rõ, không có score giả |
| UC-02 Search by Keyword | Nhập “giày chạy bộ màu đen”→Tìm kiếm→pipeline text | Rỗng/over-token từ chối trước inference; chỉnh và tìm lại | Results tiếng Việt, summary đúng input |
| UC-03 Search by Voice | Chọn Voice→cho phép mic→ghi 1–15s→Dừng→nhận dạng Azure vi-VN→hiện transcript editable→Tìm theo lời nói | Denied mic có upload WAV; NoMatch có ghi lại; 429/timeout có retry thủ công; mock được ghi nhãn | Transcript xác nhận đi chung pipeline text; không tự search khi còn sửa |
| UC-04 Search by Image | Chọn file JPEG/PNG/WebP→preview→Tìm bằng ảnh→decode→encode→results | Loại/bytes/pixel/ảnh lỗi bị từ chối; thay ảnh có thể tìm lại | Results ảnh, preview và source đúng |
| UC-05 Search Order | `/orders`→nhập O001→tra cứu scoped C001→summary→mở detail | O002 của C002 và O999 đều cùng 404/message; empty ID 422 | Chỉ dữ liệu đơn hàng C001 |
| UC-06 View Product | Click card→`/products/P001`→application lookup→detail→Back | ID sai/không tồn tại 404; image lỗi hiện alt; direct reload hoạt động | Metadata, stock, giá demo, credit ảnh; không thêm checkout |
| UC-07 View Order | Click summary O001→`/orders/O001`→scoped detail→Back | Direct link O002 vẫn 404; refresh không bypass scope | Date/status/items/total C001 |
| UC-08 Multimodal | Nhập text + ảnh→slider text_weight default .5→Tìm kết hợp→hai embeddings→fused query→results | Thiếu một input 422; norm fusion lỗi không chia 0; slider đổi đánh dấu cần tìm lại | Metadata weight và component scores giải thích kết quả |

Transcript mô phỏng là alternate mode demo offline, nhãn “Transcript nhập tay · mô phỏng”. Không dùng nó để nghiệm thu phần Azure trong FR-03.

## Chất lượng đo được

| NFR | Điều kiện | Evidence/gate |
| --- | --- | --- |
| NFR-01 Performance | Đề xuất laptop ≥4 CPU threads, RAM 8GB; catalog 12–100, model/index warm; p95 text/image/multimodal ≤5s cho mỗi mode, 30 requests tuần tự | Ghi CPU/RAM/OS/model revision, riêng cold start; nếu vượt phải tối ưu và công khai số thực |
| NFR-02 Usability | UI tiếng Việt; responsive 360/768/1440px; keyboard cho tabs/file/filter/modal; có loading/empty/error | E2E + kiểm tra tay/a11y, không overflow ngang |
| NFR-03 Reliability | Input sai không gọi encoder/Azure; stale cache không được phục vụ; dependency lỗi không làm API crash toàn bộ | Integration boundaries + health/recovery |
| NFR-04 Maintainability | Presentation→Application→Data; service injection; repository không tính ranking | Kiểm tra import và UML/code mapping |
| NFR-05 Extensibility | Thay encoder/STT bằng adapter; thay encoder rebuild cache và calibration | Interface tests + invalidation tests |
| NFR-06 Privacy | Không khóa trong browser/log; không tồn tại public upload store; order scoped server | Secret scan, network inspection, isolation tests |
| NFR-07 Reproducibility | Model commit và package lock, canonical IDs; score tie ổn định | Hai lần chạy cùng môi trường đạt thứ tự giống, score tolerance 1e-5 |
| NFR-08 Relevance | Test set tách calibration, truy vấn tiếng Việt; mục tiêu Hit@3 ≥0.80 cho mỗi mode; OOD rejection ≥0.60 ở relevant | Evaluation thật theo 10; không sửa nhãn để làm test xanh |

Voice đề xuất deadline backend 25s/lượt sau upload, browser 30s; record ≤15s. Không tính thời gian người nói vào inference latency. Không cam kết Azure network có độ trễ cố định.
