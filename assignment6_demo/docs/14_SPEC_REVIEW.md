# Kiểm chứng bộ đặc tả và trạng thái bàn giao

Revision 1 · 08/10/2026. **Hoàn thành ở mức đặc tả để người dùng kiểm tra. Website chưa được implement.** Báo cáo này phân biệt bằng chứng đã có với gate thực thi của Agent sau này.

## Đối chiếu yêu cầu người dùng

| Yêu cầu | Bằng chứng hiện tại | Trạng thái |
| --- | --- | --- |
| Đọc CONTEXT và nắm dự án | 01 rà soát Analysis, Detailed Design và prototype; giữ nội dung gốc, thêm note ưu tiên | Đã thực hiện |
| Tối ưu thiết kế để Agent không đoán/mâu thuẫn | D01–D15; vector/model/fusion/cache, order scope, invalid input, recovery được khóa ở03–08 | Đã đặc tả |
| File hướng dẫn hoàn chỉnh end to end | 02–12 liên kết requirements→data/service/API/UI→milestone→test→runbook→demo/UML | Đã bàn giao tài liệu |
| Website phải có đầy đủ chức năng theo đặc tả | FR-01–13, UC-01–08, ma trận AC và G1–G9 | Đã xác định; triển khai/kiểm thử pending |
| Chỉ thay đổi assignment6_demo | Git status chỉ có các file mới/chỉnh trong folder này | Đã kiểm tra |
| CPU, tiếng Việt | Model pair aligned512, Vietnamese model card, pinned revisions, true-model test protocol | Đã xác minh model metadata; chưa chạy model |
| Azure Speech, tiếng Việt | region chuẩn hóa southeastasia, vi-VN; micWAV/SDK/error/deadline; env không có key | Đã đặc tả; resource/live calls chưa kiểm chứng |
| Mọi ảnh sản phẩm lấy ảnh thực tế từ mạng, không gen | 12 downloaded photos, [credit](IMAGE_CREDITS.md), manifest source/license/hash, visual review | Đã chuẩn bị và kiểm tra seed |
| Người dùng kiểm tra Markdown trước implement | [Chỉ mục](README.md) và [kế hoạch Agent](09_AGENT_IMPLEMENTATION_PLAN.md) | Sẵn sàng review |

## Kiểm tra đã chạy trong đợt tài liệu

- Kiểm tra UTF-8, local Markdown links, balanced code fences và JSON fenced examples; kết quả máy đọc được tại [spec-audit.json](assets/spec-audit.json).
- Đối chiếu IDs: 13 FR, 8 UC, 8 NFR và 46 AC trong ma trận nghiệm thu; không loại nhánh đơn hàng hoặc multimodal.
- Kiểm tra toàn bộ 12 file ảnh có thể decode, hash/byte count đúng, có nguồn/tác giả/license, local_path trong folder, metadata chủ thể phù hợp ảnh. [dataset-audit.json](assets/dataset-audit.json) ghi phạm vi chính xác; [contact sheet](assets/asset-contact-sheet.jpg) là evidence visual.
- Kiểm tra 3 đơn hàng: ID/owner/date/item reference và tổng VND; có C001/C002 để kiểm thử isolation sau implement. Đây là schema/seed check, chưa phải authorization API chạy thật.
- Secret scan trên file văn bản bàn giao: không có Azure key được gán giá trị thật. Không gọi Azure trả phí, không chỉnh resource hoặc credentials.
- Reviewer độc lập đối chiếu contracts xuyên file; những vấn đề phát hiện được sửa trước bàn giao. Không coi review của Agent như kết quả browser/runtime.

Các chỉnh sửa sau review: đổi CC0 license links sang HTTPS phù hợp API; khóa fingerprint 64 ký tự hex không prefix để dùng được trên Windows; thêm search deadlines 10s/15s, timeout 504 và test giữ slot; audit chỉ bao gồm bộ tài liệu bàn giao. Các thư mục temp của công việc khác nằm ngoài reading map/audit này và không bị xóa hoặc chỉnh sửa. Reviewer đã kiểm tra lại những chỉnh sửa này và kết luận sẵn sàng cho người dùng review.

## Các gate còn cho đợt triển khai

Tất cả M0–M6 và G1–G9 ở09/10 vẫn để trống. Chưa có backend/frontend, dependency locks, model snapshots/index/policy, query evaluation set, browser E2E, benchmark, live5 Azure hoặc VP project xuất từ ứng dụng mới. Lệnh runbook và UML source là hướng dẫn đích, không được trình bày là đã chạy.

Không có chỗ thiếu cần người dùng cung cấp để hoàn thành bộ tài liệu này. Key/resource của Azure chỉ cần kiểm chứng khi làm voice thật; tiếng Việt/canonical region và chính sách ảnh đã được đưa vào contracts. Chất lượng CLIP, latency CPU, browser mic và ngưỡng OOD phải được đo thực tế theo10; nếu không đạt, Agent tiếp tục sửa và báo evidence, không tự giảm scope hoặc bịa số liệu.

## Tự đánh giá chất lượng tài liệu

Dùng skill `agent-self-evaluation`; đây là đánh giá tài liệu, không phải điểm chất lượng website.

| Tiêu chí | Điểm /5 | Bằng chứng và cải thiện cụ thể |
| --- | --- | --- |
| Accuracy | 4 | Nguồn chính thức xác minh pair tiếng Việt, region, PCM; mẫu JSON parse được. API SDK/dependencies phải smoke test với versions lock ởM0 |
| Completeness | 4 | Đủ13FR/8UC/8NFR,46AC, scope và paths. Relevance/benchmark/live/VP evidence cố ý dành cho đợt implement, không có kết quả runtime để điền |
| Clarity | 4 | Có reading map, quyết định, schema, state và error tables. Người review vẫn cần đọc04–08 cùng nhau để nắm các contract kỹ thuật |
| Actionability | 4 | M0–M6, target file tree, PowerShell commands và exact gates. Commands chỉ có thể thực thi sau khi Agent tạo các entrypoints/scripts |
| Conciseness | 4 | Mỗi file phụ trách một hợp đồng; schema chuẩn tập trung04/06. Một số nguyên tắc secret/live/score được nhắc lại ởrunbook vàtest để tránh lỗi lúc bàn giao |

Trung bình **4.0/5**. Cải thiện tiếp theo: xác minh dependencies/browser/SDK trên implementation thật; render và dựng UML trong VP; lưu evaluation/latency/live evidence. Tự kiểm tra: đánh giá này không tuyên bố ảnh/license/models metadata chứng minh website đã hoạt động.
