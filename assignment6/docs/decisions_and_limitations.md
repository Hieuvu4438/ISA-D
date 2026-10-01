# Quyết định thiết kế và giới hạn

## Các quyết định

| Quyết định | Lý do | Hệ quả có thể kiểm chứng |
|---|---|---|
| Dùng CLI cho Presentation | Tập trung thiết kế/UML/prototype; đề không bắt buộc web UI | Chạy offline, --help/default demo; UI không truy cập Data |
| Simulated speech-to-text | PDF trang 2, 5, 12–13 cho phép transcript trực tiếp | SpeechService tồn tại và được gọi; không cần audio/model/API |
| Pixel descriptor 88 chiều | Có image file query thực tế mà không tải deep model | Encode cả products/query cùng pipeline; chỉ mô tả handcrafted descriptors |
| JSON + in-memory cosine index | Dataset nhỏ, dễ bàn giao và tái lập | Metadata/version/dimension/hash phải validate; không gọi vector database |
| Retrieval và RankingService tách riêng | PDF trang 22 yêu cầu tách hai operation | Retrieval candidates chưa sort/top-k; rank có score/tie-break/top-k |
| Score-level fusion | Token/pixel khác feature space | Weights normalized; fusion dùng union candidates và scores công khai |
| Exact order lookup với customer scope | Đồng bộ use case bắt buộc và extension trang 16 | Không trả O001 cho customer khác; không tuyên bố authentication |
| Dataset và ảnh synthetic local | Không cần remote images/credentials; reproducible | Dataset/source generator công khai; hình minh họa không phải photograph |
| Native diagrams trong VP | Task 2–4 yêu cầu UML trong Visual Paradigm | `.vpp` có model elements/relationships sửa được, exports và screenshots thật |

## Giới hạn và diễn giải kết quả

Voice input là **transcript string**, không có thu microphone, nhận diện âm thanh hoặc đo ASR accuracy. Một voice query thành công chứng minh pipeline voice adapter → query → retrieval/ranking, không chứng minh speech recognition.

Image search thực sự đọc pixels nhưng sử dụng handcrafted descriptor histogram/thumbnail. Tìm ảnh gần giống trên hình synthetic không chứng minh tìm theo ngữ nghĩa trên ảnh sản phẩm thực tế, khả năng chịu nền/phối cảnh/ánh sáng/occlusion. Cosine cao không phải xác suất đúng.

Keyword search English dùng stopwords và alias hạn chế. Không hiểu tự nhiên đầy đủ, không có semantic embeddings hay multilingual NLP. Query như từ đồng nghĩa ngoài vocabulary có thể không match; kết quả sai phải lấy từ evaluation hiện tại để phân tích, không tạo số liệu bằng tay.

Dataset nhỏ có ground truth tự xây cho acceptance experiment. Success rate chỉ đúng theo criterion đã công bố và tập query đó, không ước lượng chất lượng tìm kiếm production. Same-source image queries đo consistency tốt hơn khả năng generalization; report phải nêu rõ biến thể query và failure case. Không sửa ground truth để nâng success rate.

Customer_id do người dùng CLI nhập là **customer context mô phỏng**. Scope test ngăn accidental cross-customer result theo context đó; người dùng có thể tự nhập context khác. Không có login/session/authorization production, không dùng dữ liệu khách hàng thật. Products/orders chỉ là fixtures local. Không gửi private workspace/report lên dịch vụ ngoài.

Không có thanh toán, tồn kho đồng bộ, checkout, order management, real-time updates, concurrency/load test, network deployment, semantic AI, vector database hay web UI. Stock-aware score nếu có là heuristic công khai, không phải business optimization đã được kiểm chứng.

Sinh viên/MSSV/lớp chưa được cung cấp: report để `Chưa cung cấp`. Deadline không được diễn giải thành bằng chứng đã nộp đúng hạn; LMS submission cần chỉ dẫn riêng.

## Hướng cải thiện có thể kiểm thử

1. Thêm tập ảnh query độc lập (góc chụp/nền/ánh sáng), đo Recall@k và precision; so sánh với descriptor hiện tại.
2. Tích hợp ASR thật trong adapter riêng; đo word error rate và downstream retrieval, vẫn giữ offline fixture.
3. Thay encoder học sâu có model/version/cost/latency rõ; rebuild index và đối chiếu ground truth không đổi.
4. Mở rộng corpus và semantic text retrieval; benchmark p50/p95 sau load và memory footprint.
5. Tích hợp authenticated customer identity trước phục vụ orders thật; thêm policy và audit/retention tests.
