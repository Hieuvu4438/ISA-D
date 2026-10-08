# Nhận dạng tiếng Việt qua Groq Whisper-large-v3

Theo yêu cầu ngày 08/10/2026, Cortis tích hợp thêm model **Groq Cloud Whisper-large-v3** cho nhận dạng giọng nói tiếng Việt tốc độ cao và độ chính xác vượt trội.

## 1. Cấu hình

Đặt trong file `.env` (được `.gitignore`):

```dotenv
SPEECH_PROVIDER=groq
GROQ_API_KEY=<khóa_api_groq_của_bạn>
GROQ_SPEECH_MODEL=whisper-large-v3
GROQ_SPEECH_TIMEOUT=30
```

File `.env.example` cung cấp các biến placeholder không chứa key.

## 2. Hoạt động

1. **Khởi động backend:**
   ```powershell
   ./scripts/run_backend.ps1
   ```
2. Mở showroom tại `http://127.0.0.1:5173/`, chọn tab **Giọng nói**.
3. UI hiển thị trạng thái `Groq Whisper Large v3 · tiếng Việt`.
4. Người dùng có thể:
   - Bấm **Bắt đầu ghi âm** qua microphone trình duyệt (chuyển đổi chuẩn WAV PCM16 mono 16 kHz).
   - Hoặc tải lên tệp WAV PCM16 mono 16 kHz.
   - Bấm **Nhận dạng lời nói**.
5. Backend gửi audio tới Groq endpoint `https://api.groq.com/openai/v1/audio/transcriptions` với `language=vi`, `temperature=0`.
6. Trả về transcript chuẩn chính tả tiếng Việt. Người dùng có thể kiểm tra, chỉnh sửa rồi bấm tìm kiếm sản phẩm.

## 3. Bằng chứng kiểm thử và độ chính xác

Đo đạc trên 5 mẫu người thật từ bộ dữ liệu Google FLEURS tiếng Việt (`runtime/speech-evaluation/`):

* **Kết quả nhận dạng:** 5/5 mẫu thành công.
* **Tỉ lệ lỗi từ (Word Error Rate - WER):** **3.97%** (so với 17.46% của mô hình local nhỏ).
* **Thời gian phản hồi API:** trung bình 1.2 – 3.0 giây mỗi câu nói.
* Bằng chứng chi tiết được lưu tại `artifacts/backend/speech-groq-check.json`.
