# Báo cáo triển khai và chạy thử backend

Cập nhật 08/10/2026, 11:32 giờ Việt Nam. Backend đang chạy local tại `http://127.0.0.1:8000`, Swagger tại `/docs`. Sau sửa và khởi động lại, không thấy lỗi chặn các luồng demo đã kiểm tra.

## Đã triển khai

- FastAPI, request ID, lỗi tiếng Việt thống nhất, CORS cho frontend local, health và OpenAPI/Swagger.
- Model multilingual CLIP tiếng Việt và CLIP ảnh, CPU, vector aligned 512 chiều; tải một lần, inference offline.
- Tìm bằng text, transcript voice, ảnh và text + ảnh; trọng số multimodal, cosine ranking, Top-k, filter category/brand/giá/còn hàng, nearest/relevant, trace và timing.
- 12 sản phẩm với ảnh chụp thực tế tải từ mạng, nguồn/tác giả/giấy phép/hash; API danh sách, chi tiết, ảnh và credits.
- 3 đơn hàng seed, scope khách C001; xem summary/detail, kiểm tra tổng tiền. Đơn thuộc C002 và mã không tồn tại đều trả cùng lỗi 404.
- Azure Speech adapter: WAV PCM16 mono 16 kHz, vi-VN, southeastasia; validation, deadline, busy, NoMatch/rate/auth error mapping; key lấy từ environment hoặc `.env` riêng.
- JSON repositories, index NPZ/fingerprint, build/calibration scripts; giới hạn queue và timeout; PowerShell setup/run, dependency lock, test và evidence.

## Chạy thử và sửa lỗi

Đã chạy script setup trọn luồng trên môi trường hiện có, dùng lại checkpoint local, build index/calibration rồi khởi động lại server.

Phát hiện hai lỗi input và sửa trong `backend/app/main.py`:

1. JSON text chứa lone Unicode surrogate `\ud800` gây lỗi 500 khi gọi tokenizer thật. Parser hiện kiểm tra Unicode hợp lệ ở cả key/value, trả 400 INVALID_JSON trước model.
2. JSON float `1e999` được parser chuyển thành Infinity rồi trả 422 sai phân loại. Parser hiện chặn số không hữu hạn ngay khi parse, trả 400 INVALID_JSON.

Đã bổ sung 3 regression cases, xác nhận tests thất bại trước sửa và đạt sau sửa. Decoder cũng bắt RecursionError để không lộ lỗi 500 do độ sâu JSON vượt khả năng parse.

## Kết quả hiện tại

| Kiểm tra | Kết quả | Evidence |
| --- | --- | --- |
| Tự động: data/search/API/speech/concurrency | 85 passed; coverage 87,3% | `tests.xml`, `coverage.json` |
| HTTP các chức năng với model thật | 30/30 đạt; 0.884s cho toàn lượt smoke | `http-smoke.json` |
| HTTP lỗi/giới hạn/startup | 15/15 đạt | `runtime-check.json` |
| Setup từ script PowerShell | Exit 0: dependencies, dataset, model cache, index, calibration | Lệnh `assignment6_demo/scripts/setup_backend.ps1` đã chạy |
| Readiness/Swagger/OpenAPI | HTTP 200 | `runtime-check.json` |
| Dataset và ảnh thật | 12 sản phẩm, 3 đơn, 1 ảnh query; validate đạt | `dataset-validation.json` |
| Model/index/calibration | CPU thật; 3 policies; 6 query tiếng Việt đúng top 1 | `index-build.json`, `calibration.json`, `demo-evaluation.json` |
| Lint/format/compile/dependencies | Exit 0 | Ruff, compileall, pip check |
| Log server sau sửa | Không có ERROR, traceback hoặc HTTP 500 trong lượt kiểm tra | `server-rerun.log` |

15 runtime checks bao gồm JSON malformed/Unicode/float overflow, token thật vượt 128, request quá lớn, MIME/method sai, query lặp, language rỗng và WAV đúng format khi thiếu cấu hình Speech. Các lỗi 400/404/413/415/422/503 dự kiến là kết quả đúng, không phải app bị crash.

## Phần chưa xác minh và giới hạn demo

- Azure thật chưa gọi: backend hiện báo speech unconfigured, WAV hợp lệ trả 503 SPEECH_UNAVAILABLE. Key cần được đặt ở environment/`.env` backend; test adapter không chứng minh cloud STT đã chạy.
- Bộ 15 query là calibration/sanity nhỏ. Ảnh positive dùng lại ảnh catalog. Text ngoài catalog bị loại 2/3, còn một query ô tô false positive; không tuyên bố chất lượng trên bộ test độc lập.
- Có một cảnh báo deprecation ở Starlette TestClient dùng httpx; 85 tests vẫn đạt, không phải lỗi runtime API.
- Swagger đã kiểm tra bằng HTTP. Browser automation Chrome chưa chạy được vì thiếu Playwright extension; không ghi nhận visual/browser test đã đạt.
- Frontend chưa triển khai trong đợt backend.

Tự đánh giá: Accuracy 4/5 (API/model có evidence, Azure live pending); Completeness 4/5 (core backend đủ, cloud config bên ngoài); Clarity 4/5 (quickstart/Swagger/report, docs website vẫn rộng hơn scope); Actionability 4/5 (setup/run đã chạy, cần tải model trên máy mới); Conciseness 4/5 (demo dùng JSON/NPZ, giữ tài liệu đầy đủ cho đợt sau). Trung bình 4.0/5. Ưu tiên tiếp theo là xác minh STT bằng WAV tiếng Việt thật khi cấu hình key; thêm query ảnh độc lập nếu cần đo chất lượng rộng hơn. Đánh giá có thể đối chiếu trực tiếp với artifacts, không là gate nghiệm thu cloud.
