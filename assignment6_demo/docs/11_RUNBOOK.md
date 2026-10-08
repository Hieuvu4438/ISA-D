# Runbook Windows cho website sau triển khai

**Backend CPU và frontend Cortis đã chạy local với 60 sản phẩm/12 danh mục và 30 đơn hàng.** Commands bên dưới dùng các script đã triển khai. Bằng chứng và giới hạn chất lượng được ghi trong README, DEMO_DATA và FRONTEND_VERIFICATION; live Azure và frozen test độc lập vẫn cần nghiệm thu riêng.

## Điều kiện trước khi chạy

- Windows PowerShell, Python **3.12** với `py -3.12`, Node **22 ≥22.12** và npm. Máy hiện tại có thể dùng Node 22.18; không dùng con số này như bằng chứng dependencies ứng dụng đã được install.
- Working directory `D:\PROJECTS\ISA-D\assignment6_demo`; tất cả venv, model/index, data, frontend và artifacts nằm trong folder này.
- Backend/frontend/scripts đã được implement theo 09, dependency locks đã qua clean-install smoke.
- Catalog ảnh thật đã được validate; inference chạy CPU. Lần tải model/npm cần mạng, search sau setup đọc local snapshots.
- Azure key chỉ đưa vào environment backend khi cần voice thật. Không cần key để chạy text/image/multimodal/order. Không gọi Azure trong setup, startup hoặc tests mặc định.

## 1. Cài backend bằng lock

Mở PowerShell trong root demo. Các lệnh tách riêng để biết bước nào thất bại; không tiếp tục nếu exit code khác0.

```powershell
Set-Location -LiteralPath 'D:\PROJECTS\ISA-D\assignment6_demo'
py -3.12 --version
node --version
npm --version
py -3.12 -m venv backend\.venv
& .\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.lock.txt
& .\backend\.venv\Scripts\python.exe -m pip install --no-deps -e .\backend
```

Không cần activate venv hoặc đổi ExecutionPolicy. `requirements.lock.txt` phải chứa versions tương thích Windows, torch CPU và SDK; `pyproject.toml` định nghĩa package `app` để scripts import được sau editable install. Mọi dependency update phải tạo lock mới và chạy gate; không tự upgrade packages giữa buổi demo.

## 2. Tải model, validate và build offline index

```powershell
& .\backend\.venv\Scripts\python.exe scripts\download_models.py
& .\backend\.venv\Scripts\python.exe scripts\validate_dataset.py
& .\backend\.venv\Scripts\python.exe scripts\build_index.py
& .\backend\.venv\Scripts\python.exe scripts\calibrate_thresholds.py
```

Xác nhận `runtime/models/model_manifest.json` chứa hai model IDs/commit revisions ở 05; index NPZ/sidecar nằm trong `runtime/index`, policy trong `runtime/policies`. Không publish threshold khi calibration không đạt. Nếu calibration chưa có fixture hoặc fail, `nearest` vẫn có thể chạy khi index hợp lệ; relevant capability unavailable và website chưa đạt quality gate.

`evaluation/queries.json` hiện có 15 demo calibration/sanity cases; ảnh positive là catalog self-match, chưa phải test độc lập. Frozen quality protocol ở 10 vẫn pending; không dùng report demo để tuyên bố gate quality đạt. Build là thao tác offline; không hot-reload JSON/index trong process API.

## 3. Khởi động backend

Trong terminal backend, root demo:

```powershell
$env:DEMO_CUSTOMER_ID = 'C001'
$env:AZURE_SPEECH_REGION = 'southeastasia'
$env:AZURE_SPEECH_LANGUAGE = 'vi-VN'
$env:HF_HUB_OFFLINE = '1'
& .\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Không dùng nhiều workers: mỗi worker nhân model memory và phá giả định giới hạn inference của demo. Startup chỉ đọc model/cache local; không gọi Azure. Không đặt key ở `VITE_*`, frontend `.env`, command-line arguments hoặc source. `127.0.0.1` là phạm vi demo local; chưa mở public khi chỉ có customer context C001.

Nếu cần Azure thật, đặt key vào `assignment6_demo/.env` đã ignore rồi khởi động lại backend; không gửi key qua chat. Có thể dùng prompt bảo mật trong terminal backend thay cho file `.env`. Lệnh sau chỉ đọc nhập của người dùng vào process environment, không hiển thị key:

```powershell
$speechKeySecure = Read-Host -Prompt 'Azure Speech key' -AsSecureString
$speechKeyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($speechKeySecure)
try {
    $env:AZURE_SPEECH_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($speechKeyPointer)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($speechKeyPointer)
    Remove-Variable speechKeySecure, speechKeyPointer
}
```

Giữ environment trong process; environment không phải vault. Đóng terminal hoặc `Remove-Item Env:\AZURE_SPEECH_KEY` sau khi dừng demo. Không ghi key vào `.env` được track. Thiếu key phải được health capability phản ánh, không fallback voice giả.

## 4. Cài và chạy frontend

Mở terminal khác:

```powershell
Set-Location -LiteralPath 'D:\PROJECTS\ISA-D\assignment6_demo\frontend'
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Mở `http://127.0.0.1:5173`. Vite proxy `/api`→`http://127.0.0.1:8000`; browser không gọi trực tiếp Azure. Vite config `strictPort=true` để không âm thầm đổi port. CORS backend chỉ allow local frontend origins cấu hình rõ theo 08. Direct refresh `/products/P001` và `/orders/O001` phải được SPA fallback xử lý.

Mic browser local loopback phải được browser cho phép; dùng origin nhất quán, chọn microphone đúng và thử ngắn. Nếu deny/không có thiết bị, dùng WAV upload; không coi manual transcript là nghiệm thu Azure.

## 5. Smoke và gates không tính phí

Mở terminal kiểm tra trong root demo, backend/frontend đang chạy:

```powershell
Set-Location -LiteralPath 'D:\PROJECTS\ISA-D\assignment6_demo'
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health/live'
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health/ready'
Push-Location backend
& .\.venv\Scripts\python.exe -m pytest tests --cov=app --cov-branch --cov-report=term-missing
Pop-Location
& .\backend\.venv\Scripts\python.exe scripts\evaluate.py
& .\backend\.venv\Scripts\python.exe scripts\benchmark_backend.py --base-url http://127.0.0.1:8000 --requests-per-mode 30
```

Health nằm ngoài `/api/v1` theo06. `/health/ready` có thể503 nếu index/model thiếu; PowerShell sẽ báo HTTP error và cần đọc sanitized response body, đây là dependency lỗi cần xử lý. Live200 không chứng minh search readiness hoặc Azure availability. `evaluate.py` chỉ kiểm tra lại demo fixtures, không chạy frozen test. `smoke_backend.py` phải chạy sau khi API đã khởi động. Readiness và policy/speech capabilities riêng trong `/api/v1/meta` phải được kiểm tra, không chỉ HTTP status.

Frontend terminal kiểm tra riêng:

```powershell
Set-Location -LiteralPath 'D:\PROJECTS\ISA-D\assignment6_demo\frontend'
npm run typecheck
npm run lint
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

`npm test` target phải chạy một lần, không bật watch mặc định trong gate. Playwright local driver được khóa theo package-lock; không dùng package `latest`. CI/default tests không có `--confirm-live`, không gọi Azure. Lưu reports theo 10, không ghi full raw user audio vào test logs.

## 6. Gate Azure có giới hạn, chạy thủ công

**Người dùng đã cho phép tối đa 5 lượt nhận dạng cho đợt nghiệm thu này.** Chỉ chạy khi cấu hình và đủ 5 WAV thật đã được chuẩn bị theo [AZURE_LIVE_CHECK.md](AZURE_LIVE_CHECK.md). Backend environment phải có key, region, language; script gọi endpoint local, không đọc key phía frontend. Nếu fixture chưa đủ5 files, không thực hiện một lượt partial rồi báo gate đạt.

```powershell
Set-Location -LiteralPath 'D:\PROJECTS\ISA-D\assignment6_demo'
& .\backend\.venv\Scripts\python.exe scripts\verify_speech_live.py --help
```

Đọc workflow và các flags thực tế trong AZURE_LIVE_CHECK; chạy preflight trước, arm shared budget khi đủ fixtures, rồi xác nhận live chủ động. `evaluation/voice_cases.json` và ledger không thay thế audio thật. Tối đa 5 SDK calls, không auto retry; reload/restart không reset quota. Report original transcript semantic matches và retrieval sau xác nhận riêng; ≥4/5 theo 10. Report số calls/duration, không suy giá dịch vụ. Resource region/auth mismatch phải sửa cấu hình theo resource thật; không thử hàng loạt regions/keys.

## Cập nhật catalog và phục hồi

1. Dừng API; sửa JSON/ảnh/manifest trong demo. Validate metadata và real photo review; nếu thay ảnh phải giữ source/credit/hash đúng.
2. Chạy validate→build index→calibrate bằng calibration split. Mỗi script fail giữ state trước; không xóa cache cũ để che lỗi.
3. Khởi động API lại, đọc ready/capability; evaluate frozen test và E2E liên quan. Fingerprint mới phải khớp catalog/model/index/policy.
4. Không sửa dataset trong process đang serve. Không dùng index trước cho dataset mới dù NPZ còn tồn tại.

| Triệu chứng | Kiểm tra/cách xử lý | Evidence cần giữ |
| --- | --- | --- |
| Missing/stale/corrupt index →503 | Đọc error code/hash; dừng API, validate và build, restart; không rebuild từ route | Failed loader + builder report + ready sau restart |
| `RELEVANCE_POLICY_UNAVAILABLE` | Xem fingerprint/weight/split; calibrate đúng .5; custom weights dùng nearest có nhãn | Calibration report; không tự đặt threshold |
| `SEARCH_BUSY`429 | Dừng submit liên tục, chờ/retry thủ công; xem queue/native calls; giữ1worker | Concurrency tests/trace; không tăng threads vô hạn |
| `SEARCH_TIMEOUT`504 | Deadline backend 10s/browser 15s; kiểm tra CPU/queue; nếu native worker không kết thúc thì restart đúng backend process; không auto replay input | Timeout/slot-retention report, latency và readiness sau phục hồi |
| Voice unavailable/auth fail | Env backend có key/region đúng? Resource Speech? Language vi-VN? Không print key | Sanitized dependency code/live report |
| STT NoMatch | Mic level/WAV format/phrase/duration; cho ghi lại hoặc nhập transcript mô phỏng có nhãn | Case result; không tự fabricate transcript |
| Mic denied | Browser permission/device; upload WAV đúng chuẩn | UI denied/upload case |
| Token/ảnh/WAV validation422 | Sửa input theo limit; không truncate/reencode tùy tiện để giấu lỗi | Error code và successful resubmit |
| Builder lock còn nhưng process đã chết | Xác minh PID/liveness bằng OS, chỉ remove lock trong runtime sau xác minh; không lấy tuổi lock làm bằng chứng | PID/process evidence trước recovery |
| Port8000/5173 đang dùng | Xác định process mình đã chạy; Ctrl+C đúng terminal; không kill process khác chưa rõ | Port/process info; không âm thầm đổi origin |
| Ảnh mạng nguồn không truy cập | Runtime dùng file local; hiển thị credit URL đã ghi; bổ sung nguồn sau nếu cần | Local SHA/decode/source record |

## Hồ sơ bàn giao và dừng demo

Giữ artifacts validation/evaluation/performance/E2E/UML của phiên đã pass; các metric đúng model/index/policy fingerprints. Khi dừng, Ctrl+C frontend và backend, dọn key environment của terminal backend. Upload temporary phải được code dọn trong request lifecycle; không tự xóa recursive thư mục rộng để “cleanup”.

Trước demo chính thức đọc tracker ở [10](10_TESTING_ACCEPTANCE.md). Bất kỳ G1–G9 pending/failed phải nêu cụ thể; không dùng runbook hoặc screenshot sơ đồ làm evidence website hoàn thành.
