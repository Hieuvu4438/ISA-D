# Hướng dẫn Agent trong assignment6_demo

## Yêu cầu mới đang áp dụng

Ngày 08/10/2026 người dùng mở rộng yêu cầu sang xây dựng frontend bằng code, nối API đầy đủ và kiểm tra hệ thống. Thương hiệu Cortis; hướng showroom mẫu vật, ảnh thật, màu đá sáng và đỏ rượu. Tối đa 3 subagent đồng thời. Ghi riêng bằng chứng model thật, browser và Azure thật; không dùng mock để nhận đã xác minh live. Người dùng đã cho phép commit và push các thay đổi của nhiệm vụ theo từng mốc, phải kiểm tra `.gitignore` và diff trước mỗi lần. Hướng dẫn backend ở `docs/BACKEND_QUICKSTART.md`.

## Phạm vi làm việc

Chỉ tạo/chỉnh sửa file trong `assignment6_demo`. Không sửa `assignment6`, cấu hình Codex, thư mục sibling hoặc private state. Không đưa thư mục công cụ agent cục bộ, env, model/runtime, node_modules hoặc build output vào commit của ứng dụng.

## Trình tự bắt buộc khi implement

1. Đọc `docs/README.md`, `docs/01_CONTEXT_REVIEW.md`, sau đó tài liệu theo thứ tự 02–12.
2. Đối chiếu trạng thái thực tế; cập nhật tiến độ theo milestone ở `docs/09_AGENT_IMPLEMENTATION_PLAN.md`.
3. Hiện thực đủ FR-01–FR-13 và UC-01–UC-08. Không bỏ order, multimodal, tiếng Việt, voice Azure hoặc lỗi/recovery để chỉ chạy được happy path.
4. Tuân thủ hợp đồng JSON/API và vector. Nếu cần đổi, cập nhật tài liệu, test và UML trong cùng thay đổi; ghi lý do. Không đổi scope âm thầm.
5. Kiểm thử logic bằng doubles; kiểm thử chất lượng bằng encoder thật. Không coi mocked voice là bằng chứng Azure hoạt động.
6. Ghi lệnh thực chạy, exit code, fingerprint và evidence; chỉ đánh dấu verified sau khi có bằng chứng trong `artifacts/`.

## Ràng buộc kỹ thuật

- CPU bắt buộc; không mặc định CUDA. Không dùng random vectors, histogram 88D hoặc keyword scoring làm kết quả AI thật.
- Mọi ảnh sản phẩm là ảnh thật lấy trên mạng. Không dùng image generation, ảnh minh họa vẽ bằng code, render 3D hoặc ảnh synthetic làm catalog. Kiểm tra bằng mắt và lưu provenance theo `docs/04_DATA_CONTRACTS.md`.
- Không hardcode/in khóa Azure từ hội thoại vào code, Markdown, fixtures, artifacts hoặc bundle frontend. `.env.example` chỉ có giá trị rỗng/placeholder.
- Region canonical `southeastasia`; language `vi-VN`. Không gọi dịch vụ trả phí tự động từ CI hoặc lúc khởi động.
- Không cho browser truy cập JSON nội bộ/NPZ; chỉ gọi application API. Không trả `customer_id` của đơn hàng khác.
- Commit và push được người dùng cho phép. Publish, triển khai public và sửa tài nguyên Azure chưa được cho phép.
- Không làm giỏ hàng, thanh toán, đăng ký hoặc admin CRUD nếu chưa có yêu cầu mới.

## Điều kiện kết thúc

Dùng toàn bộ gate trong `docs/10_TESTING_ACCEPTANCE.md`. Hoàn thành implement nghĩa là website chạy từ clean checkout, tất cả luồng được kiểm tra, tiếng Việt và Azure thật có evidence, dữ liệu/ảnh có nguồn và README khớp lệnh thực tế. Nếu còn thiếu live evidence thì ghi pending, không ghi complete.
