# Phân tích yêu cầu — Assignment 06

Nguồn chuẩn: [PDF đề bài](../storage/inf_sys_analysis_design_assignment_06_design_code.pdf), 23 trang. Số trang bên dưới là số trang PDF, trùng số in trên trang. Tài liệu này cụ thể hóa Task 1, không thay đổi yêu cầu đề.

## Bối cảnh, mục tiêu và phạm vi

Customer của hệ thống thương mại điện tử muốn tìm sản phẩm bằng từ khóa, lời nói hoặc hình ảnh, sau đó xem kết quả theo mức độ phù hợp. Nguyên tắc trung tâm là **Different Inputs → Common Query Representation → Retrieval → Ranking → Results** (trang 1, 22–23). Prototype phải thể hiện được quan hệ giữa yêu cầu, UML và chương trình chạy thực tế; không phải hệ thống bán hàng production.

Actor duy nhất của prototype là **Customer**. SpeechService, ImageService, repository và vector index là thành phần nội bộ, không phải actor. Không có payment gateway, microphone thật hay dịch vụ AI bên ngoài.

Baseline bắt buộc gồm text search, simulated voice search, image similarity, repository, ranking và ba diagram native trong Visual Paradigm (trang 7–9, 17–19). Bản hoàn chỉnh thêm fusion text + image, price/category filters, product details và customer-scoped order lookup. Các mở rộng này không thay thế baseline.

## Sáu task và sản phẩm

| Task | Trang nguồn | Nội dung phải đáp ứng | Artifact |
|---|---|---|---|
| T1 | 17–18 | Description, actor, ≥5 FR, NFR, modalities, outputs | Tài liệu này và report trang 2–3 |
| T2 | 7–8, 18 | Customer và bảy use case đúng UML | `.vpp`, use-case export, screenshot VP |
| T3 | 8–9, 18 | Ba layer/package, dependencies rõ | `.vpp`, component export, architecture.md |
| T4 | 9, 18 | Voice sequence có bảy participants | `.vpp`, sequence export, report trang 6 |
| T5 | 9–15, 19 | Python repository, text/voice/image, ranking | Source, dataset, index, manifests, tests |
| T6 | 19 | Ba query text/voice/image; input, processing, products, scores | `artifacts/demo/` và screenshots thực tế |

Yêu cầu bổ sung: ≥10 sản phẩm (trang 11); thực nghiệm có total, successful, success rate và incorrect examples (trang 20); report khoảng 10–12 trang và ảnh VP/Python (trang 20–21); bảy nhóm sản phẩm nộp (trang 21); retrieval khác ranking, UI không truy cập Data (trang 22).

## Yêu cầu chức năng

| ID | Yêu cầu | Điều kiện nghiệm thu |
|---|---|---|
| FR-01 | Customer tìm bằng keyword/text | Chuẩn hóa chữ hoa/khoảng trắng; trả sản phẩm có score và top-k |
| FR-02 | Customer tìm bằng transcript giọng nói mô phỏng | Đi qua `SpeechService.transcribe`, giữ `type=voice`; kết quả tương đương text cùng nội dung |
| FR-03 | Customer tìm bằng ảnh | Mở và encode pixels; cùng encoder với product images; cosine, ranking và top-k |
| FR-04 | Thống nhất query contract | Text/voice/image/fusion có cùng envelope; validate type, filters, weights và top-k |
| FR-05 | Xếp hạng và hiển thị scores | RankingService riêng, final_score giảm dần; tie-break product_id tăng dần |
| FR-06 | Xem thông tin product | Có id/name/category/color/price/stock/image; product id không tồn tại có thông báo |
| FR-07 | Tìm và xem order theo customer context | O001/C001 đúng; customer khác không nhận order; not-found rõ |
| FR-08 | Dataset có ≥10 product và ảnh/index hợp lệ | Unique ids, field/range/path/dimension/hash hợp lệ |
| FR-09 | Xử lý input sai và no-match | Empty query/image hỏng/dimension sai bị từ chối; no-match hợp lệ trả list rỗng |
| FR-10 | Fusion text + image | Score thành phần công khai; weight hợp lệ; dùng union candidates trước ranking |
| FR-11 | Price/category filter | `under 100` là `<100`; category filter đúng; filters xuất hiện trong processing |
| FR-12 | Demo và evaluation tái lập | CLI/JSON/log + sample inputs có thật; metrics tính từ results, criterion được công bố |

FR-01–06, FR-08–09 cụ thể hóa baseline; FR-07 và FR-10–11 là extension được triển khai để thống nhất UML/code. FR-12 đáp ứng yêu cầu demo/evaluation. Đề cho phép artificial feature vectors, nhưng bản này dùng descriptor từ pixels, không lấy product_id từ tên ảnh.

## Yêu cầu phi chức năng

| ID | Yêu cầu | Cách kiểm chứng và giới hạn |
|---|---|---|
| NFR-01 | Maintainability | Presentation chỉ import Application; Data không import tầng trên; `main.py` composition root được phép ghép dependencies |
| NFR-02 | Reproducibility | Dataset/encoder/version cố định; stable tie-break; script không thay ground truth theo kết quả |
| NFR-03 | Robustness | Test invalid inputs, zero norm, NaN/dimension, corrupt image, missing dataset field, no-match |
| NFR-04 | Usability | `--help`, README, default demo; output in input/processing/products/scores; simulation được gắn nhãn |
| NFR-05 | Performance | Mục tiêu đề xuất ≤1 giây/query trên dataset nhỏ sau load; chỉ kết luận khi có phép đo và phạm vi đo |
| NFR-06 | Portability | `pathlib`, paths tương đối với project root, clean install từ ZIP; không phụ thuộc Start Menu shortcut |
| NFR-07 | Data isolation | Customer context chặn order của người khác; đây là mô phỏng context, chưa có authentication production |
| NFR-08 | Offline operation | Không cần API key, remote AI model, microphone hoặc network để chạy search |

NFR-05 là mục tiêu triển khai, không phải yêu cầu thời gian cứng trong PDF. Dataset nhỏ và phép đo local không chứng minh khả năng chịu tải production.

## Input, processing và output

| Mode | Input thực tế | Processing | Output |
|---|---|---|---|
| Text | Chuỗi English keyword/natural language giới hạn | Normalize, stopwords, alias, filters, keyword retrieval | Ranked products, matched_terms và text/final scores |
| Voice | Transcript string đã có sẵn | Simulated STT → voice query → text retrieval | Như text, có nhãn mô phỏng |
| Image | File ảnh PNG/JPEG tương đối/absolute hợp lệ | Pixel encoder 88 chiều → cosine trên index | Products, image/final scores và encoder metadata |
| Multimodal | Text và image | Common query, candidate union, filter, score fusion | Scores từng modality và final_score |
| Order | Order id + customer id | Exact lookup trong customer scope | Order status/total/date hoặc not-found |

Result envelope chứa `query`, `processing`, `results`. Processing ghi modality, normalized query, filters, encoder dimension khi cần, candidate count, weights và top-k. Product details không phải product retrieval ranking mới.

## Xử lý khác biệt trong đề và giả định

1. Bìa/trang 1 là Assignment 06; ví dụ trang 6, 12, 23 và folder trang 9 còn ghi Assignment 05. Dùng Assignment 06 thống nhất.
2. Trang 15 nói ít nhất hai mode, Task 6 trang 19 yêu cầu text/voice/image. Thực hiện đủ ba mode.
3. Search Order/View Order bắt buộc trong use case (trang 18), order code là extension (trang 16, 19). Thực hiện lookup đơn giản, không thêm toàn bộ order management.
4. Fusion là extension (trang 15–16, 19), rubric có Multimodal search 10 điểm (trang 22). Thực hiện score fusion; không cộng vectors khác không gian.
5. Trang 1 ghi V01 TODAY trước 16:00 class 03/19:00 class 04; V02 trước 23:00 thứ Tư 07/10. Mốc năm 2026 theo tài liệu; class chưa cung cấp, không suy ra từ license/user account.
6. Tên sinh viên, MSSV, lớp chưa cung cấp. Cover ghi đúng trạng thái đó. Không mặc định tên tài khoản Windows/VP là thông tin sinh viên.

## Nghiệm thu và bài nộp

Rubric trang 22: requirements 10, use case 15, architecture 20, sequence 10, Python 20, multimodal 10, evaluation 5, report 5, demonstration 5; tổng 100. Đây là tiêu chí ưu tiên, không phải điểm tự nhận.

Bài nộp phải có report PDF, project `.vpp`, Python source, product dataset, sample images, README và demonstration results. Mở lại `.vpp` trong VP xác minh diagram native; không dùng ảnh chèn vào VP để thay UML. Report có số liệu thực tế từ evaluation và ảnh thực tế. Hướng dẫn nộp local không đồng nghĩa đã nộp LMS.
