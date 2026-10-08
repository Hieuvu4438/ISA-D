# Bàn giao backend demo — 08/10/2026

Backend API đã triển khai và chạy thử bằng model CPU thật. Chỉ sửa trong `assignment6_demo`; không triển khai frontend hay publish dịch vụ.

| Kiểm tra | Kết quả | Bằng chứng |
| --- | --- | --- |
| Unit/integration/concurrency | 85 passed; 87,3% coverage | `tests.xml`, `coverage.json` |
| Dataset/ảnh thực tế | 12 sản phẩm, 3 đơn, 1 ảnh query; hash/decode/provenance đạt | `dataset-validation.json` |
| Index CPU aligned 512D | Build bằng hai checkpoint cố định đạt | `index-build.json` |
| Calibration/evaluation demo | 3 policies; 6 query tiếng Việt đúng top 1 | `calibration.json`, `demo-evaluation.json` |
| HTTP chức năng thật | 30 checks passed, 0.884s | `http-smoke.json` |
| HTTP giới hạn/lỗi | 15 checks passed, không gọi Azure thật | `runtime-check.json` |
| Khởi động/setup lại | Script setup exit 0; server ready; không có ERROR/traceback/500 sau sửa | `RUN_REPORT.md`, `server-rerun.log` |
| OpenAPI/Swagger | HTTP 200; schema đã export | `openapi.json` |
| Tokenizer thật | Text dưới 500 ký tự nhưng vượt 128 tokens bị chặn 422 TEXT_TOO_LONG | kiểm tra HTTP bằng `ạ ` lặp 140 lần |
| Lint/compile/dependencies | Exit 0 | các lệnh bên dưới |
| Azure Speech SDK/adapter | SDK cài được, cấu hình local vi-VN/southeastasia; 30 tests speech đạt | `tests.xml`; không gọi Azure trả phí |

Index fingerprint: `c7e6d0a0dbd1a4ecc87428f411b7e88e0ff910e38ee49cd8bc98bf925f623005`.

Các checks tương ứng đã chạy từ repo root với exit 0. Lệnh tái kiểm tra dưới đây đặt thêm đường dẫn database coverage trong thư mục demo:

```powershell
$env:PYTHONPATH='D:/PROJECTS/ISA-D/assignment6_demo/backend'
$env:COVERAGE_FILE='D:/PROJECTS/ISA-D/assignment6_demo/artifacts/backend/coverage.sqlite'
assignment6_demo/backend/.venv/Scripts/python.exe -m pytest assignment6_demo/backend/tests -q --cov=app --cov-report=json:assignment6_demo/artifacts/backend/coverage.json
assignment6_demo/backend/.venv/Scripts/python.exe -m pytest assignment6_demo/backend/tests -q --junitxml=assignment6_demo/artifacts/backend/tests.xml
assignment6_demo/backend/.venv/Scripts/python.exe -m ruff check --config assignment6_demo/backend/pyproject.toml assignment6_demo/backend assignment6_demo/scripts
assignment6_demo/backend/.venv/Scripts/python.exe -m compileall -q assignment6_demo/backend/app assignment6_demo/scripts
assignment6_demo/backend/.venv/Scripts/python.exe -m pip check
assignment6_demo/backend/.venv/Scripts/python.exe assignment6_demo/scripts/validate_dataset.py
```

Các script `download_models.py`, `build_index.py`, `calibrate_thresholds.py`, `evaluate.py`, `smoke_backend.py` chạy bằng cùng Python venv, file nằm trong `assignment6_demo/scripts`. Paths resolve theo demo root, không phụ thuộc cwd. PowerShell scripts dùng UTF-8 BOM để chạy được trên Windows PowerShell 5.1.

Giới hạn thực tế: calibration chỉ có 15 query nhỏ, ảnh positive dùng lại ảnh catalog để kiểm tra mechanics. OOD text loại 2/3, còn truy vấn ô tô false positive; `nearest` luôn chọn các sản phẩm gần nhất, `relevant` phụ thuộc threshold demo. Không có kết quả benchmark độc lập. Azure thật chưa gọi; cần key local rồi gửi WAV PCM16 mono 16 kHz 1–15s để xác minh. Không có frontend trong đợt này.

Self-evaluation theo skill `agent-self-evaluation`:

| Tiêu chí | Điểm | Bằng chứng/giới hạn |
| --- | --- | --- |
| Accuracy | 4/5 | API và model thật có evidence; speech live chưa xác minh |
| Completeness | 4/5 | Các chức năng backend có đủ; Azure runtime cần key bên ngoài |
| Clarity | 4/5 | Quickstart và Swagger hiện hành; tài liệu website rộng hơn scope backend |
| Actionability | 4/5 | Hai script setup/run, lock và model/index local; máy khác cần tải model lần đầu |
| Conciseness | 4/5 | Data JSON/NPZ và API đủ demo; các tài liệu đặc tả giữ nhiều chi tiết cho đợt website |

Trung bình **4.0/5**. Cải thiện theo mức tác động: xác minh Azure bằng giọng Việt thật khi cấu hình key; thêm query ảnh độc lập nếu cần đánh giá chất lượng ngoài demo. Người dùng có thể đối chiếu đánh giá này với API đang chạy và artifacts; không coi điểm số là gate nghiệm thu.
