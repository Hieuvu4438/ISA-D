# Cortis — trạng thái kiểm chứng catalog mở rộng

Dữ liệu hiện có: 60 sản phẩm, 12 danh mục, mỗi danh mục 4–6 mẫu; 30 đơn, 24 thuộc khách demo C001 và 6 thuộc C002 để kiểm tra quyền. Ảnh chụp thật đã tải và duyệt, nguồn/giấy phép/checksum đầy đủ. Giá, tồn kho và đơn là minh họa.

| Kiểm tra | Kết quả / bằng chứng |
| --- | --- |
| Backend unit/integration | 103 tests đạt; tests.xml/coverage.json ghi lần chạy thực. Statement coverage và branch coverage tách biệt; branch chưa đạt 80%. |
| Expanded API | 271/271 checks đạt, expanded-demo.json. |
| Model/index | CPU CLIP 512D thật, 60 rows; index fingerprint fbb823590b942a7432948c7482b97b9fa7323f33f866b563ba34a7bdcf98bd13. |
| Performance | 90 requests +3 warmups, 0 errors; p95 text81,69ms / image380,78ms / multimodal455,44ms; chưa đo cold start. |
| Reproducibility | 5 query probes qua baseline +2 restarts, ID/rank/score ổn định tolerance1e-5; reproducibility.json. |
| Architecture | Dựng chỉ mục chuyển sang Application; AST directions/Data orchestration checker đạt. Chưa có formal Protocols, OrderService/ImageStorage riêng và Visual Paradigm .vpp. |
| Frontend | npm ci, lint/typecheck/17 unit/build đạt; 19/19 production wiring E2E đạt. |
| Quality | Hai E2E quality tests fail với labels giữ nguyên; text demo Hit@3 5/6, category Hit@3 7/12. 15 fixtures chưa phải 60-case frozen test độc lập. |
| Azure | Quyền tối đa5 lượt đã xác nhận; 0 lượt đã dùng, thiếukey/5WAV/mic evidence. Ledger bền dùng chung UI/CLI, hết5 hoặc chưaarm sẽ chặn provider; không auto retry. |
| Dependencies | npm audit0; pip-audit không tìm thấy vulnerability trong các package audit được, torch2.14.1+cpu bị skip do không có trên PyPI. |
| Visual | Reviewer tương đương xác nhận fix side stripe resolved; DESIGN.md/sidecar ghi hệ thống thật. QUALITY BAR unavailable, không có approved comp trên code-first path. |

Swagger: http://127.0.0.1:8000/docs. Frontend: http://127.0.0.1:5173/. Đây là demo local; không có kết luận nghiệm thu tất cả G1–G9 khi quality/live speech/artifacts còn thiếu.

Tự đánh giá: accuracy4/5 (raw evidence và fail được giữ); completeness3/5 (Azure/frozen quality/UML còn thiếu); clarity4/5 (tách wiring, model quality và provider evidence); actionability4/5 (URL chạy thật + AZURE_LIVE_CHECK); conciseness3/5 (nhiều artifact kỹ thuật). Trung bình3,6/5. Ưu tiên tiếp theo: đủ audio/config Azure, quality split độc lập và cải thiện retrieval theo protocol, hoàn thiện kiến trúc/UML. Người dùng có thể đối chiếu mọi kết luận với report thực.
