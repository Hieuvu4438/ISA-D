# Chạy backend demo

Backend và frontend Cortis đã kết nối trên catalog 60 sản phẩm/12 danh mục và 30 đơn. 271 API checks và 90 warm CPU benchmark requests đã chạy; xem DEMO_DATA. 15 fixtures hiện tại chỉ kiểm tra/calibration demo, chưa là frozen test độc lập. Voice adapter Azure và persistent budget đã triển khai; quyền tối đa5 lượt đã xác nhận nhưng còn thiếu key/5 WAV thật, xem AZURE_LIVE_CHECK. Setup/startup/test mặc định không gọi Azure.

Từ PowerShell tại `assignment6_demo`, dùng Python 3.12:

```powershell
./scripts/setup_backend.ps1
./scripts/run_backend.ps1
```

Model tải một lần khoảng 1 GB, commit cố định. Sau setup, model inference không cần mạng. Khi đổi dữ liệu/model, build index và calibration lại rồi restart server. Calibration chưa tìm được ngưỡng khả thi sẽ báo lỗi, giữ mode thiếu policy ở trạng thái unavailable thay vì tự đặt số ngưỡng.

Mở `http://127.0.0.1:8000/docs` để thử API. Tại terminal thứ hai:

```powershell
backend/.venv/Scripts/python.exe scripts/smoke_backend.py
backend/.venv/Scripts/python.exe scripts/check_runtime.py
backend/.venv/Scripts/python.exe scripts/evaluate.py
```

Smoke thử text tiếng Việt, transcript nhập tay, ảnh thật, multimodal, filter, relevant/OOD empty, chi tiết sản phẩm/credits và đơn hàng C001; kiểm tra đơn của C002 không lộ. WAV sai được chặn trước provider. Smoke không gọi Azure trả phí. Evidence xuất vào `artifacts/backend/`.

Speech dùng `AZURE_SPEECH_KEY` trong environment hoặc `.env` local, region `southeastasia`, language `vi-VN`. Không ghi key vào source/Markdown/fixture. WAV hợp lệ phải PCM16, mono, 16 kHz, dài 1–15 giây. `POST /api/v1/speech/transcriptions` trả transcript để chỉnh rồi gửi `POST /api/v1/search` mode `voice` với `voice_source="azure"`. Transcript nhập tay dùng `manual_transcript`; không ghi nhận như Azure đã chạy thật.

Ảnh catalog ở `docs/IMAGE_CREDITS.md`; ảnh query pizza ngoài catalog có credit riêng ở `evaluation/IMAGE_CREDITS.md`. `nearest` luôn trả gần nhất sau filter; `relevant` áp ngưỡng theo mode đã calibration. Ngưỡng demo không phải confidence hoặc xác suất đúng.
