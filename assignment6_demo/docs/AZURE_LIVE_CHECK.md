# Kiểm tra Azure Speech thật, tối đa 5 lượt

Người dùng đã cho phép tối đa **5 lượt Azure**. Không hỏi lại quyền, thử key/region bằng request bổ sung hoặc tự thu microphone. Hiện chưa có năm WAV giọng người thật; FR-03/G8 vẫn **pending**. Script không đọc key, tạo âm thanh mẫu hay giả transcript.

`scripts/verify_speech_live.py` mặc định chỉ kiểm tra WAV/manifest/ledger và GET `/api/v1/meta`, không POST âm thanh. Exit code `2` khi phụ thuộc còn thiếu. Boolean `configured_unverified` không chứng minh key hoạt động.

## Nhãn đã được review trước khi gọi

[voice_cases.json](../evaluation/voice_cases.json) dùng metadata catalog và nhãn primary agent đã chấp thuận, không lấy CLIP ranks làm đáp án. Chỉ freeze sau khi đủ năm WAV thật và review phương thức thu.

| Case | Câu nói cần ghi | Expected product | Phương thức |
| --- | --- | --- | --- |
| V001 | Tìm giày chạy bộ On Cloud màu đen. | P001 | Microphone thật trong frontend |
| V002 | Tìm túi da Les cuirs d'Agathe màu nâu. | P011 | WAV ghi giọng người thật, upload |
| V003 | Tìm áo thun trơn màu đen. | P041 | WAV ghi giọng người thật, upload |
| V004 | Tìm đồng hồ Candino mặt trắng dây nâu. | P050 | WAV ghi giọng người thật, upload |
| V005 | Tìm kính mát Ray-Ban Original Wayfarer màu đen. | P059 | WAV ghi giọng người thật, upload |

Mỗi bản ghi là một utterance ngắn, không dữ liệu cá nhân; WAV PCM16 little-endian, mono 16 kHz, 1–15 giây, tối đa 1 MiB. Năm hash phải khác nhau. Đổi tên WebM thành WAV, tone, giọng tổng hợp, fake microphone Chromium và transcript nhập tay không đủ nghiệm thu live.

## Chuẩn bị local, chưa gọi Azure

Working directory `assignment6_demo`. Đặt năm file dưới ignored `runtime/speech/incoming/`. Với V001, ghi microphone thật tại `http://127.0.0.1:5173`, dừng và lưu WAV từ UI **trước khi nhận dạng**. Người vận hành nghe file, đối chiếu câu đã chốt và ghi quan sát thiết bị/quyền trong `runtime/speech/V001-capture.json`:

```json
{
  "input_source": "browser_real_microphone",
  "human_speech": true,
  "fake_audio": false,
  "synthetic_voice": false,
  "fake_device": false,
  "microphone_permission_observed": true,
  "reviewer": "demo-operator",
  "observation": "Thực sự quan sát microphone thật và nghe file khớp câu đã chốt."
}
```

V002–V005 có capture JSON riêng, `input_source=human_recorded_wav_upload`, `human_speech=true`, `fake_audio=false`, `synthetic_voice=false`, reviewer sau khi nghe. JSON khai báo tự tạo không tự chứng minh có giọng người thật.

```powershell
& .\backend\.venv\Scripts\python.exe scripts\verify_speech_live.py
& .\backend\.venv\Scripts\python.exe scripts\verify_speech_live.py --bind-audio V001 --audio runtime/speech/incoming/V001.wav --capture-evidence runtime/speech/V001-capture.json --reviewer demo-operator
& .\backend\.venv\Scripts\python.exe scripts\verify_speech_live.py --bind-audio V002 --audio runtime/speech/incoming/V002.wav --capture-evidence runtime/speech/V002-capture.json --reviewer demo-operator
```

Lặp bind cho V003–V005. Bind xác nhận người review đã nghe giọng thật khớp nhãn; script chỉ kiểm tra cấu trúc WAV, hash, thời lượng và evidence khai báo.

```powershell
& .\backend\.venv\Scripts\python.exe scripts\verify_speech_live.py --freeze-labels
& .\backend\.venv\Scripts\python.exe scripts\verify_speech_live.py --arm-budget
```

Freeze ghi hash catalog và thời điểm trước request đầu. `manifest_sha256` dùng SHA256 của UTF-8 canonical JSON: `json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':'))`.

## Ledger bền, dùng chung UI và CLI

Backend [speech_budget.py](../backend/app/data/speech_budget.py) giữ ignored `runtime/speech-live-budget.json`, khóa file và reserve **trước SDK dispatch**. Bootstrap `awaiting_fixtures` có zero hash và không attempts, khóa provider. Script được bind/freeze trong trạng thái này; arm chỉ chuyển sang `armed` sau đủ năm file, giữ `session_id`.

Nếu ledger chưa có, arm dùng exclusive create. Backend có root nhưng thiếu ledger sẽ chặn provider, không chạy không giới hạn. Ledger đã armed, có attempt, malformed hoặc thuộc manifest khác không bị reset để lấy lượt mới. Reload/restart, timeout, auth/provider error và nhấn lại không hoàn tiền lượt reserve. WAV validation/busy trước dispatch không tính SDK call; operation đã dispatch vẫn tính nếu HTTP timeout. `reserved` chưa kết thúc phải pending, không gọi lại.

Ledger chỉ giữ UUID, SHA-256 **toàn bộ WAV**, thời lượng/thời điểm và enum outcome; không key, audio hay transcript. CLI không reserve một ledger riêng. Không xóa/sửa ledger, session hoặc limit sau năm lượt; đợt mới cần quyền mới.

## Live khi cấu hình backend sẵn sàng

Người dùng điền `.env` backend đã ignore hoặc environment riêng rồi restart backend. Agent không mở/in key. GET meta chỉ kiểm tra boolean; region `southeastasia`, language `vi-VN`, không thử hàng loạt regions.

V001 chạy bằng bản ghi microphone đã lưu/bind trong frontend, bấm nhận dạng **một lần**. Giữ response JSON thật từ Network panel trong `runtime/speech/V001-response.json`, quan sát transcript editable và giữ evidence thao tác. Không fake/intercept speech route lần này.

```powershell
& .\backend\.venv\Scripts\python.exe scripts\verify_speech_live.py --collect-browser V001 --response-file runtime/speech/V001-response.json
& .\backend\.venv\Scripts\python.exe scripts\verify_speech_live.py --max-calls 5 --confirm-live
```

Lệnh sau gửi WAV V002–V005 qua endpoint local, mỗi file một POST, không retry. Chạy một file bằng `--case V002 --confirm-live`. Hash đã có attempt thì bỏ qua, không gửi lại. Thiếu năm file/freeze/arm/config thì không gửi speech POST. Backend đếm SDK dispatch thực tế cho cả UI và CLI.

Collect V001 khớp hash/thời lượng với một attempt SDK thật đã recognized; người review vẫn phải đối chiếu response/evidence với lần chạy thực tế. File response tự dựng không chứng minh UI/provider chạy. Raw transcript chỉ lưu trong ignored `runtime/speech/live-results.json`, không in ra log.

## Review gốc, xác nhận rồi search

Đọc transcript **gốc** và nhãn trước khi sửa. Chấm ngữ nghĩa gốc riêng:

```powershell
& .\backend\.venv\Scripts\python.exe scripts\verify_speech_live.py --review-original V001 --semantic-match pass --reviewer demo-operator
& .\backend\.venv\Scripts\python.exe scripts\verify_speech_live.py --confirm-transcript V001 --reviewer demo-operator
```

Nếu sửa, lưu text người dùng xác nhận trong `runtime/speech/V001-confirmed.txt`, thêm `--confirmed-text-file runtime/speech/V001-confirmed.txt`. Confirm gọi search local mode voice, provenance azure, Top3 nearest, giữ retrieval gốc và đã xác nhận riêng. Không tự search ngay sau STT, không sửa raw transcript hay ghi đè điểm. Lặp review/confirm cho case recognized.

`runtime/speech/live-report.json` ghi dispatch count/tổng thời lượng/outcome/nguyên bản/đã sửa/retrieval. Không đoán chi phí khi thiếu billing evidence. Chỉ passed khi năm attempts kết thúc, khớp năm WAV freeze khác nhau, có real browser mic recognized, ít nhất 4/5 transcript gốc nonempty giữ ý theo review và 4/5 confirmed voice searches có expected product trong Top3. Typed errors/timeout vẫn tính lượt, không tính recognition thành công.

## Phụ thuộc còn thiếu

- Năm WAV tiếng Việt giọng người thật và review khớp câu đã chốt.
- Evidence mic thật/quyền browser, lưu WAV trước nhận dạng và response live V001.
- Backend Azure đã cấu hình/restart; boolean cấu hình chưa chứng minh authentication.
- Freeze/arm, năm calls thật, review STT gốc và voice search sau xác nhận.

Fake SDK/microphone và manual transcript trước đây kiểm tra luồng offline/lỗi; không thay những mục thiếu này.
