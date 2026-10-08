# Nhận dạng tiếng Việt trên CPU

Theo yêu cầu mới của người dùng ngày 08/10/2026, Cortis hỗ trợ nhận dạng local khi Azure không hoạt động. Azure đang trả HTTP401 tại endpoint xác thực regional; cấu hình `vi-VN`/`southeastasia` hợp lệ nhưng chưa chứng minh credential thuộc đúng resource. Không tự gọi lại Azure hoặc chuyển provider trong một request.

## Cài và chạy

Từ thư mục `assignment6_demo`, sau `scripts/setup_backend.ps1`:

```powershell
backend/.venv/Scripts/python.exe scripts/provision_speech_model.py
```

Đặt trong `.env` riêng:

```dotenv
SPEECH_PROVIDER=local
LOCAL_SPEECH_CPU_THREADS=4
LOCAL_SPEECH_TIMEOUT=90
```

Restart backend rồi mở http://127.0.0.1:5173/, tab **Giọng nói**, ghi âm hoặc tải WAV PCM16 mono16kHz dài1–15s, bấm **Nhận dạng lời nói**. UI hiện **Whisper CPU · tiếng Việt**. Có thể sửa transcript rồi tìm sản phẩm. Local chạy trên backend, không gửi audio ra Azure, không cần API key và không tiêu quota5 Azure.

Model `Systran/faster-whisper-small` đa ngôn ngữ, revision `2ec96c5472da50d38d40c0cfe0602af2e94b4c8a`, ~486MB; runtime Faster Whisper1.2.1/CTranslate2 INT8 CPU. Giữ1 worker,4 threads, `language=vi`, beam5, VAD, không carry context. Reject silence trước decoder; không coi noise filter là bảo đảm chống mọi hallucination. Chỉ tải bằng script provision rõ ràng; runtime đọc model local và không tự tải. File model/cache/audio thử được gitignore.

Để chuyển lại Azure, đặt `SPEECH_PROVIDER=azure`, dùng key/region đúng resource và hoàn thành quy trình bounded live trong [AZURE_LIVE_CHECK](AZURE_LIVE_CHECK.md). ProviderAzure vẫn giữ ledger/quota, không tự gọi khi startup/CI. `voice_source` chỉ provenance UI, không chứng thực provider hoặc quyền truy cập.

## Bằng chứng ban đầu

```powershell
backend/.venv/Scripts/python.exe scripts/fetch_speech_samples.py
backend/.venv/Scripts/python.exe scripts/verify_speech_local.py
```

5 mẫu người thật của Google FLEURS test `vi_vn`, pinned revision và reference được lấy trước inference. [Evidence](../artifacts/backend/speech-local-check.json): nhận dạng5/5, WER22/126=17.46%, thời gian6.45–9.60s/mẫu7.26–14.88s trong lúc kiểm thử khác chạy cùng máy. Kết quả nhỏ này chưa chứng minh giọng microphone người dùng, mọi giọng vùng miền hoặc tên sản phẩm.

Playwright thực trên production preview: upload FLEURS WAV→POST200 providerlocal→transcript→sửa→search giữ `voice_source=local`,1/1 đạt. Chạy riêng bằng `LOCAL_SPEECH_E2E_AUDIO` chỉ đến WAV đã fetch; test không tự tải hoặc gọi Azure.

Nguồn: [Faster Whisper](https://github.com/SYSTRAN/faster-whisper), [model](https://huggingface.co/Systran/faster-whisper-small), [Google FLEURS](https://huggingface.co/datasets/google/fleurs) CC-BY4.0, Conneau et al.2022. [Azure hỗ trợ tiếng Việt](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=stt), [regions](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions), [xác thực và HTTP401](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-speech-to-text-short).
