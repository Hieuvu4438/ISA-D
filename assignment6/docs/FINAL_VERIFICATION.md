# Final Verification — Assignment 06

Bản bàn giao được kiểm tra từ file thật, service output, native model inventory và ZIP extraction sạch. Báo cáo PDF dùng đúng `artifacts/report/Assignment_06_Report.pdf`.

| Gate | Kết quả |
|---|---|
| Required submission groups and evidence | PASS |
| Dataset, real images, and matching pixel index | PASS |
| Complete English LaTeX PDF, full Python listings and approved visual evidence | PASS |
| UML exports and real screenshot image files | PASS |
| Native VP model inventory and required UML semantics | PASS |
| Three mandatory demo modes, fusion, order, and scores | PASS |
| Frozen ground truth, metrics, separate denominators, and failures | PASS |
| Test, coverage, lint, typecheck, and dependency consistency evidence | PASS |

Tests: **78 PASS**, failures/errors=0, skipped=0; application/data line coverage **100.00%**. Ruff/typecheck/pip-check evidence PASS. Complete English LaTeX PDF has no page limit, includes all Python files and all 25 approved images; required UML exports and screenshots exist and decode.

Clean extraction smoke dùng interpreter `.venv` của workspace để reuse dependency, nhưng chạy source từ ZIP snapshot giải nén trong cwd riêng, không dùng PYTHONPATH workspace. Đây là portable-source smoke, không tuyên bố clean dependency installation.

Các lệnh đã chạy thành công từ cwd của source giải nén, gọi đường dẫn interpreter workspace tuyệt đối:

```powershell
& "D:\PROJECTS\ISA-D\assignment6\.venv\Scripts\python.exe" main.py --demo --json
& "D:\PROJECTS\ISA-D\assignment6\.venv\Scripts\python.exe" main.py --mode text --query "black shoes" --json
& "D:\PROJECTS\ISA-D\assignment6\.venv\Scripts\python.exe" main.py --mode voice --query "find black running shoes" --json
& "D:\PROJECTS\ISA-D\assignment6\.venv\Scripts\python.exe" main.py --mode image --image data/queries/black_shoe_query.png --json
& "D:\PROJECTS\ISA-D\assignment6\.venv\Scripts\python.exe" -m pytest -q
```

Kết quả chi tiết: `artifacts/tests/submission_validation.json`, `artifacts/tests/clean_extraction.json`. Ground-truth và results được đối chiếu SHA-256/IDs/counts; primary, extension, challenge, robustness có denominator riêng. Challenge failures được giữ nguyên trong report/evaluation.

ZIP chọn source Python, dataset/image/query fixtures, frozen ground truth, docs, report PDF, native `.vpp`, UML exports, assignment screenshots, test/demo/evaluation evidence, desktop script và Java/XML plugin source. Không đưa `.venv`, backup, VP seed/workspace/plugin classes, ảnh project cũ, source PDF đề vào ZIP.

Manifest chứa SHA-256 và byte size cho mỗi file payload, không hash chính manifest. Timestamp ZIP cố định giúp tái tạo byte-identical archive từ cùng input. `submission/manifest.json` ngoài ZIP bổ sung SHA-256 của archive; ZIP hash không được ghi vào manifest bên trong để tránh vòng tự tham chiếu.

Giới hạn: voice là simulated STT; ảnh synthetic và pixel descriptor không phải semantic learned encoder; order context không phải production authentication; chưa nộp LMS. Native model inventory chứng minh object types; việc reopen/render thật trong Visual Paradigm do root ghi ở progress/screenshots.
