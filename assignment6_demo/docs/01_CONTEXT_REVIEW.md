# Rà soát CONTEXT và các quyết định

## Cơ sở và trạng thái thực tế

Đã đọc toàn bộ phần văn bản `CONTEXT.md`, bao gồm Analysis, Detailed Design và kiến trúc prototype ở cuối. Thư mục `assignment6_demo` ban đầu chỉ có `.gitkeep` và CONTEXT chứa ảnh nhúng. Không có website hay CLIP/Azure chạy được trong thư mục này. Prototype ở `assignment6` chỉ được đọc đối chiếu, không chỉnh sửa hoặc coi là implementation của demo mới.

Yêu cầu người dùng: tạo các file `.md` để Agent implement website đầy đủ, chỉ làm trong folder này; model chạy CPU; STT dùng Azure; cập nhật 08/10: **tiếng Việt** và **tất cả ảnh sản phẩm là ảnh thật từ mạng, không tự gen**.

## Các điểm được thống nhất

| ID | Vấn đề trong nguồn | Quyết định cho website | Đặc tả thực hiện |
| --- | --- | --- | --- |
| D01 | Phần mở đầu loại order, Analysis FR-05/07 lại có order | Giữ Search Order + View Order, scoped theo khách demo | 02, 04, 06 |
| D02 | FR01–FR07 mở đầu khác FR-01–FR-08 Analysis | Giữ ID có dấu gạch FR-01–08; bổ sung FR-09–13 | 02, 10 |
| D03 | CLIP 512D và descriptor 88D cùng xuất hiện | Chỉ pipeline pretrained 512D; 88D là lịch sử | 03, 05 |
| D04 | Bảng nói “Có CLIP” nhưng phần cuối nói không có | Không khẳng định hiện trạng từ nội dung đó; mọi runtime pending | 09, 14 |
| D05 | SpeechService lúc nhận transcript, lúc được mô tả STT | Mic/upload WAV→Azure STT thật; transcript mô phỏng riêng có nhãn | 07, 08 |
| D06 | CLIP tiếng Anh không đủ cho tiếng Việt | Multilingual DistilBERT đã aligned với CLIP image encoder; cả hai 512D | 05 |
| D07 | Multimodal chỉ có trong kiến trúc cuối | Text + image là luồng bắt buộc UC-08 | 02, 05, 06 |
| D08 | Threshold chưa calibration nhưng Analysis hứa no-results | nearest có nhãn; relevant chỉ khả dụng khi calibration hợp lệ | 05, 10 |
| D09 | Lấy Top-k trước filter/fusion dễ mất ứng viên | Exact scan toàn catalog; hard filters; threshold; stable rank; Top-k cuối | 05 |
| D10 | Cache chưa nêu publish/corruption/concurrency | Fingerprint đầy đủ, validate NPZ, atomic replace, một builder | 04, 05 |
| D11 | Customer ID truyền tay không tạo quyền truy cập | `DEMO_CUSTOMER_ID=C001` từ backend; reject client customer_id | 06, 08 |
| D12 | CLI local image path không phù hợp browser | Upload bytes có giới hạn, decode thật; không nhận path/URL từ client | 06, 08 |
| D13 | Metadata price chưa thống nhất tiền tệ | VND số nguyên, filter bằng trường dữ liệu; không suy giá bằng embedding | 04, 06 |
| D14 | Chưa có web/API/state/error contract | FastAPI + React, contracts dưới đây; stale-response guard | 03, 06, 07 |
| D15 | Có ảnh synthetic trong prototype cũ | Catalog mới chỉ ảnh chụp thật trên mạng, attribution tại detail/credits | 04, 07 |

## Giả định demo được công khai

- Website local dành cho giảng viên/nhóm, một khách demo C001; chưa phải hệ thống đăng nhập production. Không public khi chưa bổ sung auth thực tế.
- Giày là nhóm chính; có thể thêm túi để kiểm tra category và truy vấn không liên quan. Ít nhất 12 sản phẩm, ảnh đối tượng khác nhau.
- Giá VND, stock/order/status là số liệu giả định có nhãn. Ảnh thật không làm những số liệu này trở thành thông tin bán hàng thật.
- Bộ lọc được người dùng đặt trong UI. Không hứa tự phân tích điều kiện giá/brand từ mọi câu tự nhiên; ví dụ “Nike dưới 2 triệu” phải có brand/max_price rõ trên UI.
- Không giỏ hàng, thanh toán, tài khoản mới, tracking logistics thật hoặc admin. Text-to-speech không phải requirement trong CONTEXT; chỉ STT bắt buộc.
- Chỉ tiêu hiệu năng ở 02 là mục tiêu đề xuất cho laptop CPU, cần đo trên máy thực tế; không phải SLA do giảng viên công bố.

## Azure và model

Người dùng trả lời region `southeastasis`; mã Azure được tài liệu chính thức liệt kê là **`southeastasia`**, dùng mã này trong cấu hình. Đây là chuẩn hóa lỗi gõ, chưa xác minh resource/key thực tế thuộc region đó. `vi-VN` là ngôn ngữ STT; không cần Azure OpenAI deployment hoặc thêm model voice local. [Nguồn regions](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions), [nguồn language support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support).

Multilingual text model được chọn dựa trên model card liệt kê `vi` và hướng dẫn ghép với `clip-ViT-B-32`; chất lượng với catalog của nhóm vẫn phải kiểm chứng. Không ghép một text model 512D bất kỳ với ảnh CLIP chỉ vì trùng số chiều. [Model card](https://huggingface.co/sentence-transformers/clip-ViT-B-32-multilingual-v1).

Khóa thật không được lưu trong các file bàn giao. Không thực hiện lời gọi Azure tính phí trong đợt viết đặc tả.
