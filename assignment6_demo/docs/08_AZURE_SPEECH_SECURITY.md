# Azure Speech tiếng Việt và bảo vệ dữ liệu demo

Revision 2. Adapter và frontend voice đã triển khai; tests mặc định dùng provider/microphone giả có nhãn. Website local đã chạy nhưng chưa có evidence Azure live. Người dùng đã cho phép tối đa 5 lượt nhận dạng và sẽ cấu hình `.env`; key chưa sẵn sàng ở lần kiểm tra gần nhất. Workflow thực tế ở [AZURE_LIVE_CHECK.md](AZURE_LIVE_CHECK.md), contract HTTP ở 06, UX/state ở 07.

## Cấu hình Azure bắt buộc

Người dùng trả lời `southeastasis`; mã hợp lệ được chuẩn hóa thành **`southeastasia`**. Microsoft yêu cầu region trùng resource của key; việc sửa lỗi gõ không xác minh resource thực tế. Vietnamese speech-to-text dùng **`vi-VN`**. Baseline không cần Azure OpenAI, deployment name, Whisper local hoặc TTS. [Azure regions](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions), [language support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=stt).

`.env.example` chỉ có:

```dotenv
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=southeastasia
AZURE_SPEECH_LANGUAGE=vi-VN
DEMO_CUSTOMER_ID=C001
```

**Không chép key vào file bàn giao, sample, transcript fixture, command line, test, screenshot hoặc log.** Người chạy điền key trong env backend/local `.env` đã ignore, không gửi key qua chat. Vite không có `VITE_AZURE_SPEECH_KEY`; không truyền secret vào frontend build. Không print config object/`os.environ` khi kiểm tra.

Agent implement cần tạo `.gitignore` trong `assignment6_demo` cho `.env`, `.env.*` ngoại trừ `.env.example`, uploads/temp, model cache/index artifacts theo 09; check ignore trước dùng secret. Nếu key không có, thiếu SDK, region/language sai hoặc config không hợp lệ, speech capability unavailable và `/speech/transcriptions` trả 503 `SPEECH_UNAVAILABLE`; text/image/order không bị ảnh hưởng. Với demo này region allowlist chỉ `southeastasia`, language chỉ `vi-VN`; đổi region sau này phải cập nhật config và đặc tả rõ, không tự thử tuần tự các regions bằng key.

Startup xác minh **cú pháp/có cấu hình** và local SDK import, không gọi Azure trả phí. `/meta` chỉ báo `unconfigured` hoặc `configured_unverified`, không suy `connected` từ env. Key sai hoặc key khác region chỉ được nhận biết khi user chủ động gọi speech thật; lỗi sanitized.

## Luồng end to end cần thực hiện

1. Customer chọn Voice, UI giải thích “Nói một câu ngắn tiếng Việt, tối đa 15 giây. Âm thanh được gửi đến Azure để nhận dạng khi bạn bấm nhận dạng.”
2. User bấm ghi→browser xin microphone permission. Ghi có đếm thời gian, stop/cancel rõ; tự dừng ở 15s. Record ít hơn 1s không gửi.
3. Browser kết thúc capture, tạo WAV PCM16 mono 16kHz; user bấm nhận dạng. Nếu UX chọn tự gửi khi bấm Dừng, nút phải ghi rõ “Dừng và nhận dạng”; **không tự gửi từ việc mở tab**.
4. API đọc cap→validate WAV→acquire bounded speech slot→SDK Azure vi-VN→recognized transcript hoặc error.
5. UI hiển thị transcript editable và nhãn “Azure Speech · tiếng Việt”; user sửa/xác nhận rồi bấm “Tìm theo lời nói”. API speech chưa gọi search.
6. UI gọi `/api/v1/search` với mode voice, text đã sửa, `voice_source=azure` và options. Search đi qua multilingual text encoder đúng 05.
7. NoMatch/mic denied/provider fail có hành động ghi lại/upload WAV/sửa cấu hình/chuyển transcript thủ công phù hợp. Không tạo transcript giả hoặc gửi search âm thầm sau lỗi Azure.

Manual transcript phải là lựa chọn riêng có nhãn “Transcript nhập tay · mô phỏng”, gửi `voice_source=manual_transcript`. Nó giúp demo search offline nhưng không chứng minh FR-03 Azure đã chạy. Provenance là client claim cho UX/trace, không là auth hoặc security receipt.

## Ghi microphone và xuất WAV trong browser

`getUserMedia` chỉ hoạt động ở secure context như HTTPS hoặc localhost; thiếu quyền/thiết bị cần được hiển thị thành recovery state. Quyền browser là điều kiện runtime, không phải lý do hỏi lại user khi viết đặc tả. [Browser microphone API](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia).

Baseline implement bằng Web Audio + `AudioWorklet` hoặc bộ capture PCM đã kiểm tra license/version. Không lấy WebM của `MediaRecorder` rồi đổi extension `.wav`; đổi tên không thay đổi codec. Không dùng browser Web Speech API làm Azure adapter.

- Đọc sample rate thực của AudioContext/device (thường 44.1/48kHz), gom floating-point samples. Request constraint sampleRate 16000 chỉ là hint; output phải được kiểm tra và resample thật.
- Nếu nhiều channels, downmix mono có kiểm soát; resample về 16,000 Hz với anti-alias filtering hoặc OfflineAudioContext/libraries đã smoke test. Không đổi header sample rate mà giữ sample count cũ vì sẽ đổi duration/pitch.
- Clamp samples [-1,1], đổi signed int16 little-endian. WAV gồm RIFF/WAVE, fmt PCM format tag 1, channels1, rate16000, bits16, byteRate32000, blockAlign2; data length chẵn; RIFF/data sizes đúng.
- Duration đo từ số output frames/16000; 1–15s inclusive. WAV chuẩn 15s có khoảng 480,044 bytes với header 44 bytes, nằm trong 1MiB cap. Upload WAV của user vẫn cần server validate toàn bộ.
- Tạo Blob MIME `audio/wav`, FormData field `audio`; optional `language=vi-VN`. Không tự set multipart Content-Type/boundary.
- Stop/unmount/cancel phải `track.stop()` tất cả MediaStream tracks, disconnect nodes, đóng AudioContext, terminate worklet nếu applicable, xóa sample buffers/blob cũ và revoke object URLs. Browser cấp quyền muộn sau khi UI đã cancel: lập tức stop tracks, không bắt đầu record.
- Mỗi capture/transcribe/search có sequence token + AbortController. Response từ phiên cũ không cập nhật transcript/input mới; abort fetch không chứng minh Azure request đã dừng.

Test resampling bằng input fixture 44.1k/48k và kiểm tra output rate/duration/channels/PCM bytes; kiểm tra capture/permission trên browser thật không gọi Azure. Bước mic→Azure nằm trong gate 5 calls dưới đây. CI microphone giả có thể xác minh flow, không thay cho quyền/thiết bị thực tế.

## Backend WAV validation và SDK adapter

API baseline chỉ nhận WAV RIFF, uncompressed signed16 PCM, mono16kHz, duration1–15s, tối đa1MiB. Không thêm FFmpeg/GStreamer hoặc codec compressed vào đường chính. Speech SDK stream hỗ trợ signed16 PCM mono và 16kHz; raw samples phải little-endian. Đây là cơ sở chọn WAV baseline, còn duration/size cap là quyết định của demo. [SDK audio input requirements](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-use-audio-input-streams).

Adapter làm theo thứ tự:

1. Stream-read request với caps trong 06; không để multipart spool vượt cap trước validator. Bỏ filename; không nhận remote URL/path.
2. Parse RIFF chunks bằng parser có boundary checks hoặc `wave` kết hợp checks: container WAV thực, fmt format1, channels1, sample width2, rate16000, actual data length/frame count hữu hạn/chẵn/không thiếu. Reject WAVE_FORMAT_EXTENSIBLE và float PCM baseline để không phụ thuộc khác biệt Python decoder.
3. Xác minh duration từ actual frames; thiếu data/malformed chunks/header length sai/extra non-audio payload không được bypass byte cap. Với chunks metadata hợp lệ có thể bỏ qua an toàn; không decode dữ liệu ngoài chunk declared length.
4. Tạo `SpeechConfig(subscription=<backend env key>,region="southeastasia")`; set `speech_recognition_language="vi-VN"` trước tạo recognizer. Không log config/key. Không thêm ngôn ngữ autodetect ngoài scope.
5. Tạo `AudioStreamFormat(samples_per_second=16000,bits_per_sample=16,channels=1)`, `PushAudioInputStream(stream_format=...)`, `AudioConfig(stream=...)` và `SpeechRecognizer(speech_config=...,audio_config=...)` trong adapter scope.
6. Gọi `recognize_once_async()` ở bounded worker; feed **PCM data không chứa WAV header** vào push stream, rồi close input để báo EOF; wait `ResultFuture.get()` trong worker, không trên FastAPI event loop. Write-before/after-start phải được kiểm chứng với SDK version đã pin, không dựa vào giả định await native future. Push stream copy bytes nội bộ; có cap trước write. [Python PushAudioInputStream](https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.audio.pushaudioinputstream?view=azure-python).
7. Dispatch `ResultReason.RecognizedSpeech|NoMatch|Canceled`; normalize recognized transcript NFC+trim, reject rỗng như NoMatch. Không gọi search từ adapter.
8. `finally`: close push input, disconnect callbacks nếu có và release SDK references theo API của version pin. Python SpeechRecognizer docs không khai báo `close()` hoặc `cancel()` generic; không copy hàm disposal TypeScript/C# sang Python. Không gọi stop_continuous để giả dừng recognize_once. [Python SpeechRecognizer](https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.speechrecognizer?view=azure-python).

Single-shot nhận **một utterance**, có thể kết thúc ở khoảng im lặng; không hứa nhận đủ nhiều câu trong file 15s. UI nhắc nói một câu liên tục. Nếu sau này hỗ trợ nhiều utterances phải dùng continuous recognition/callbacks và sửa contract/test; không chỉ tăng duration limit. Cùng [Python recognizer reference](https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.speechrecognizer?view=azure-python).

## Timeout, concurrency và retry

`ResultFuture.get()` chờ kết quả và không có tham số timeout trong Python reference; native future không phải asyncio Future. Implement deadline HTTP ở lớp orchestrator. [ResultFuture API](https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.resultfuture?view=azure-python).

- Speech executor riêng với tối đa **1 native recognition active**, không queue audio chờ; đang busy→429 `SPEECH_BUSY`, Retry-After5. Search executor/semaphore riêng theo 03 để Azure chậm không khóa route catalog/search.
- Deadline backend25s tính từ validation/provider dispatch sau upload. Browser abort30s. Trả504 `SPEECH_TIMEOUT` khi deadline hết; tuyệt đối không nhả speech slot trong lúc native operation còn chạy chỉ vì `wait_for`/fetch bị cancel.
- Track completion thực của native worker; giữ strong reference/lifetime input cho tới khi worker kết thúc, sau đó cleanup và release slot. Response muộn bị bỏ; không cập nhật request khác. Nếu SDK treo không kết thúc, capability speech unavailable cho đến khi worker/process được phục hồi; worker treo không tạo thêm native threads. Runbook cho phép restart backend để phục hồi, text/order vẫn có thể phục vụ trong process chưa restart.
- Shutdown có bounded grace25s; nếu native thread chưa kết thúc thì quản lý process cần cưỡng bức chấm dứt process, không claim graceful cancel. Không tự spawn worker vô hạn hoặc chạy vòng retry khi timeout.
- Không retry tự động transcription POST ở browser/backend/HTTP interceptor. Nếu SDK có internal retry do version/provider, ghi rõ behavior đã kiểm chứng và giữ outer deadline/cap; không nhân thêm application retry.
- Speech429/504 có retry thủ công, giữ input cục bộ để ghi lại/thử lại. Không tự replay audio sau đổi tab/reload; log không lưu âm thanh để replay.

## Mapping provider errors

Đọc enums/result reason từ SDK version pin, map allowlist; không parse substring `error_details` làm điều kiện bảo mật. Python enum có AuthenticationFailure, Forbidden, ConnectionFailure, ServiceTimeout, TooManyRequests, ServiceUnavailable và ServiceError; version lock phải được smoke test. [CancellationErrorCode](https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.cancellationerrorcode?view=azure-python).

| SDK/event | API code/status | UI recovery |
| --- | --- | --- |
| RecognizedSpeech + nonempty text | 200 transcript | Sửa rồi bấm Tìm |
| NoMatch hoặc recognized text rỗng | `SPEECH_NO_MATCH`422 | “Chưa nhận rõ lời nói. Hãy ghi lại một câu ngắn.” |
| Backend env/SDK import/config validation fail | `SPEECH_UNAVAILABLE`503 | Kiểm tra cấu hình backend; nhập transcript tay có nhãn |
| AuthenticationFailure/Forbidden | `SPEECH_AUTH_FAILED`502, retryablefalse | Người chạy kiểm tra key+resource region; không hiển thị key/error_details |
| TooManyRequests | `SPEECH_RATE_LIMITED`429, retryabletrue | Chờ theo Retry-After và tự bấm lại |
| ServiceTimeout hoặc outer deadline | `SPEECH_TIMEOUT`504, retryabletrue | Thử lại chủ động; có thể còn native request đang kết thúc |
| ConnectionFailure/ServiceUnavailable/ServiceError | `SPEECH_UPSTREAM_FAILED`502, retryabletrue | Kiểm tra mạng/dịch vụ, retry thủ công |
| Canceled/NoError do cancel nội bộ, BadRequest, RuntimeError hoặc enum khác | `SPEECH_UPSTREAM_FAILED`502 | Message chung, log enum sanitized; nếu lỗi adapter cần sửa trước thử lại nhiều lần |

Retry-After mặc định5s; chỉ dùng provider giá trị nếu API typed của version pin cung cấp và đã validate bounded integer. Không cắt/trích provider error_details rồi đưa ra UI. Envelope theo06: có request_id/code/message/field_errors/retryable, không raw exception body. Endpoint sai schema validation phải fail trước provider.

## Boundary bảo mật và riêng tư

| Boundary | Agent phải thực hiện | Evidence bắt buộc |
| --- | --- | --- |
| Browser→API | Strict schemas/caps/content sniff; no URL/path upload; AbortController/stale guard | Integration invalid/oversize + E2E race |
| API→Azure | Key backend-only; TLS của SDK; region/language cố định; bounded concurrency/deadline | Network browser không có key; adapter tests + gate live tối đa 5 calls |
| API→order data | C001 từ env server, lookup scoped; reject client context; foreign/missing cùng404 | Test query/body/header/direct detail |
| API→image storage | Product ID→allowlist file resolved trong storage root; không static-mount toàn data; no symlink/path traversal escape | Test unknown ID/query path/dot-dot/escaped separators |
| Catalog internet images | Ảnh chụp thật đã ingest offline, provenance/license/checksum hợp lệ; no generated/synthetic | Manifest+visual inspection theo [04_DATA_CONTRACTS.md](04_DATA_CONTRACTS.md) và [IMAGE_CREDITS.md](IMAGE_CREDITS.md) |
| Logs/errors | Allowlist scalar fields, không raw request/provider payload | Secret scan + log capture failures |
| Browser render | React text rendering; không `dangerouslySetInnerHTML` cho transcript/name/source; links HTTPS validated | XSS text/link input checks |
| Local runtime | Listen127.0.0.1 mặc định; CORS origins explicit Vite localhost; không wildcard credentials | Config review + browser smoke |

Customer context demo là ràng buộc minh họa data scope, không có login/cookie/session production. CORS không thay cho auth. Không public demo hoặc proxy LAN như một hệ thống có danh tính người dùng thật khi chỉ có C001. Nếu mục tiêu deploy thay đổi, phải bổ sung auth/authorization, quota theo identity và ràng buộc secret trước external publish; không tự mở flow login/admin trong scope hiện tại.

Image storage resolved path phải thuộc root tuyệt đối đã khai báo, kể cả symlink. Source image URLs trong manifest chỉ để ingest/credit; API runtime không fetch URL từ client và không lấy ảnh mạng mỗi request. Network product ingestion được kiểm tra theo [04_DATA_CONTRACTS.md](04_DATA_CONTRACTS.md), với credit tại [IMAGE_CREDITS.md](IMAGE_CREDITS.md). Không dùng ảnh gen làm fallback sản phẩm; lỗi ảnh hiện placeholder trung tính và alt.

Log allowlist gợi ý: request_id, route template, status, code, stage, latency_ms, byte_count, duration_ms, safe SDK enum. **Không log** key/token/auth headers/env, raw transcript/audio/image, original filename, full provider URL, `CancellationDetails.error_details`, exception `repr`/stack có locals. Không bật Azure SDK verbose diagnostics hoặc audio logging mặc định. Uvicorn access log query raw cần tắt hoặc sanitize nếu có thông tin ngoài ID demo.

API upload chỉ tồn tại trong memory/bounded temporary spool suốt request; temp không nằm public storage, không commit và được close/delete trong finally. Audio không lưu persistent/cache trong hệ thống demo; browser giữ blob trong RAM khi user đang thao tác rồi xóa khi clear/unmount. Không đưa transcript/audio vào localStorage hay telemetry. Chính sách lưu/processing của Azure là chính sách dịch vụ ngoài hệ thống; không tuyên bố server demo kiểm soát retention bên Azure.

## Kiểm thử và nghiệm thu

Tests mặc định không gọi Azure: inject SpeechAdapter fake cho unit/integration, đặt tên fixture/mock rõ. Không tạo fake transcript trong production adapter. Cover recognized/NoMatch/auth429/timeout/unavailable và mapping unknown enum; assert provider không được gọi với invalid WAV, client context, request oversize.

Audio boundary fixtures phải kiểm tra codec/rate/channels/PCM duration, bytes thực sự thiếu, truncated RIFF, chunk length overflow, stereo, float PCM, silence. Assert25s timeout không release native slot sớm và request tiếp theo busy/unavailable cho đến completion; giữ clock controllable/test worker deterministic, không thực sự sleep25s mỗi CI.

Live Azure smoke trước nghiệm thu FR-03, chạy chủ động trong local configured runtime và nằm trọn trong gate **tối đa 5 SDK calls** theo [09_AGENT_IMPLEMENTATION_PLAN.md](09_AGENT_IMPLEMENTATION_PLAN.md) và [10_TESTING_ACCEPTANCE.md](10_TESTING_ACCEPTANCE.md), dùng đúng `evaluation/voice_cases.json`:

1. Xác nhận `.env` ignore và chỉ backend có key; meta còn configured_unverified trước probe.
2. Phân bổ 5 cases đã có phrase labels/expected product IDs trước lời gọi: ít nhất một case qua mic thật và ít nhất một case qua upload WAV. Case mic tạo WAV từ UI, ghi thông tin fixture/hash vào manifest trước submit; các cases khác dùng WAV tương ứng của bộ fixture. Mỗi case một lời gọi, không gửi lại cùng WAV để tạo bài test bổ sung.
3. Trong các happy paths đã phân bổ, nhận transcript Azure rồi xác nhận/sửa và search; UI trace đúng voice_source và results model thật. Ghi riêng transcript STT gốc và bản đã sửa; không dùng sửa tay để nâng điểm STT. Mic và WAV upload được nghiệm thu từ chính các calls này, không có call smoke riêng ngoài quota.
4. Ghi evidence case_id, input method, request_id, SDK version, region, language, duration, sanitized status, latency, số calls và tổng audio duration; không ghi key/audio raw vào report. Log “PASS live Azure” chỉ khi đủ evidence và các điều kiện 4/5 ở 10 đạt.
5. Silence/NoMatch, invalid WAV, denied mic, network/auth/rate/timeout và manual transcript được kiểm tra bằng test mặc định với fake SDK có nhãn. Invalid WAV phải assert **0 provider calls**. Không gửi silence hoặc audio lỗi lên Azure ngoài bộ 5 live cases; không gộp fake/manual evidence thành live pass.

Không auto retry. Mỗi lần retry chủ động vẫn là **một SDK call mới**, tính vào quota; mở phiên mới/reload/thay request_id không đặt lại số calls của cùng đợt nghiệm thu. Giữ outcome ban đầu của từng case và mọi lần thử trong report, không chọn lần tốt nhất hoặc cộng outcomes từ nhiều lượt để đạt 4/5. Không vượt 5 calls; nếu retry chiếm quota khiến chưa chạy đủ 5 cases thì gate chưa đạt và cần ghi pending, không tự chạy thêm để bù.

Không đánh dấu FR-03 complete từ env, mock test, tài liệu hoặc ảnh UI giả. Chưa có resource credentials/network để chạy live phải ghi rõ pending evidence trong14, không thay bằng fake success.
