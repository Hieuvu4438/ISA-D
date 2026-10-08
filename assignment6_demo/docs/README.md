# Chỉ mục đặc tả kỹ thuật

Revision 2 · 08/10/2026 · đặc tả website đầy đủ. Backend CPU và frontend Cortis đã triển khai; browser verification đang chạy. Dùng [BACKEND_QUICKSTART.md](BACKEND_QUICKSTART.md) để chạy backend và [README](../README.md) để mở frontend. Bằng chứng ở `artifacts/backend/` và `artifacts/frontend/`; Azure live và benchmark chất lượng độc lập phải có báo cáo riêng trước khi nghiệm thu đầy đủ.

## Cách đọc và nguồn quyết định

Yêu cầu mới của người dùng ưu tiên cao nhất. Trong bộ tài liệu: 02 định nghĩa hành vi; 04 định nghĩa dữ liệu; 05 định nghĩa toán/AI; 06 định nghĩa wire API; 07 định nghĩa UI; 08 định nghĩa voice và bảo vệ dữ liệu. 09–12 hướng dẫn thực hiện và chứng minh các hợp đồng đó. Có mâu thuẫn thì sửa đồng thời các tài liệu liên quan trước khi thay đổi code.

`CONTEXT.md` là nguồn phân tích gốc, có nhiều phiên bản thiết kế. Những đoạn được thay thế được liệt kê tại 01. Không lấy bảng “prototype hiện có” trong CONTEXT làm bằng chứng website đã chạy.

| Tài liệu | Nội dung | Người đọc chính |
| --- | --- | --- |
| [01_CONTEXT_REVIEW.md](01_CONTEXT_REVIEW.md) | Mâu thuẫn, tối ưu, quyết định, giả định | Người dùng, Agent |
| [02_REQUIREMENTS_USE_CASES.md](02_REQUIREMENTS_USE_CASES.md) | Scope, FR/NFR, main/error flows | Tất cả |
| [03_ARCHITECTURE.md](03_ARCHITECTURE.md) | Ba lớp, module, DI, sequence | Backend, UML |
| [04_DATA_CONTRACTS.md](04_DATA_CONTRACTS.md) | Product/order/query/index/ảnh thật | Backend, dataset |
| [05_AI_SEARCH.md](05_AI_SEARCH.md) | Encoder tiếng Việt, fusion, ranking, cache | AI, backend |
| [06_API_CONTRACT.md](06_API_CONTRACT.md) | Endpoints, payload, validation, lỗi | Backend, frontend |
| [07_WEB_UX.md](07_WEB_UX.md) | Trang, thành phần, state, accessibility | Frontend |
| [08_AZURE_SPEECH_SECURITY.md](08_AZURE_SPEECH_SECURITY.md) | Mic→WAV→Azure→transcript, secrets | Voice, backend |
| [09_AGENT_IMPLEMENTATION_PLAN.md](09_AGENT_IMPLEMENTATION_PLAN.md) | Milestones, file tree, prompt bàn giao | AI Agent |
| [10_TESTING_ACCEPTANCE.md](10_TESTING_ACCEPTANCE.md) | AC, test matrix, quality gates | QA, tất cả |
| [11_RUNBOOK.md](11_RUNBOOK.md) | Windows setup, lệnh chạy, recovery | Người chạy demo |
| [12_DEMO_UML_HANDOFF.md](12_DEMO_UML_HANDOFF.md) | Kịch bản demo, UML, evidence | Người thuyết trình |
| [13_REFERENCES.md](13_REFERENCES.md) | Nguồn kỹ thuật được kiểm tra | Người review |
| [14_SPEC_REVIEW.md](14_SPEC_REVIEW.md) | Kiểm chứng bộ đặc tả, giới hạn | Người dùng |
| [IMAGE_CREDITS.md](IMAGE_CREDITS.md) | Nguồn/tác giả/giấy phép của 12 ảnh mẫu | Dataset, người review |

## Hai mốc hoàn thành riêng

- **Bàn giao tài liệu hiện tại:** đủ đặc tả end to end, liên kết hợp lệ, không có secret, truy vết scope gốc và yêu cầu bổ sung. Đây là nhiệm vụ hiện tại để người dùng kiểm tra.
- **Bàn giao website sau implement:** tất cả gate trong 10 đạt, có evidence chạy thật. Tài liệu không phải bằng chứng tính năng đã hoạt động.

Bộ ảnh được tải về nằm ở `../data/images/`; manifest nguồn ở `../data/image_sources.json`. Chỉ dùng asset có trạng thái kiểm tra ảnh thật đạt. Các giá, tồn kho và đơn hàng là dữ liệu demo giả định, không lấy giá bán thật từ ảnh.
