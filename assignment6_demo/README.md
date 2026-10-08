# Cortis — demo tìm kiếm thời trang đa phương thức

Frontend React/TypeScript và backend FastAPI đã kết nối cho tìm kiếm tiếng Việt, ảnh, text + ảnh, transcript voice, lọc, chi tiết sản phẩm, nguồn ảnh và đơn hàng khách demo. Catalog có **60 sản phẩm / 12 danh mục**, mỗi danh mục 4–6 mẫu, và **30 đơn hàng**. Toàn bộ ảnh là ảnh chụp thật tải từ mạng, có nguồn và giấy phép. Xem [hướng dẫn chạy backend](docs/BACKEND_QUICKSTART.md) và [dữ liệu demo](docs/DEMO_DATA.md).

Chạy tại thư mục này bằng PowerShell:

```powershell
./scripts/setup_backend.ps1
./scripts/run_backend.ps1
```

Mở **http://127.0.0.1:8000/docs** để thử các API. Setup tải hai model tìm kiếm một lần; inference dùng model local CPU. Voice hỗ trợ model local không cần key hoặc Azure; xem [cài model speech](docs/LOCAL_SPEECH.md). Không chạy Azure trả phí trong setup hoặc smoke mặc định.

Sau mở rộng dữ liệu, **103 tests backend đạt** sau bổ sung guard Azure và chuyển index builder về Application; coverage statements và branches được công bố riêng trong [coverage.json](artifacts/backend/coverage.json). [API verification](artifacts/backend/expanded-demo.json) có **271/271 kiểm tra đạt**. [Benchmark](artifacts/backend/performance.json) đo 90 requests không lỗi; p95 text **81,69 ms**, ảnh **380,78 ms**, kết hợp **455,44 ms** trên CPU local. Cold start chưa đo. [Báo cáo cũ](artifacts/backend/RUN_REPORT.md) thuộc catalog 12 sản phẩm, không dùng để xác nhận kết quả hiện tại.

Chất lượng tìm kiếm có giới hạn: các truy vấn danh mục tổng quát đúng category trong Top 3 ở **7/12** trường hợp; calibration text nhỏ đạt **5/6 Hit@3**, còn một OOD false positive. Một số kỳ vọng Top 1 trước đây không còn đạt trên catalog 60 sản phẩm. Các bộ này chưa phải frozen test độc lập; xem raw ranks trong artifacts. Azure SDK/adapter được kiểm tra bằng stub; nhận dạng Azure thật vẫn chờ key và 5 bản ghi âm thực tế, tối đa 5 lượt theo quyền người dùng đã xác nhận.

Website mục tiêu: tìm sản phẩm bằng mô tả tiếng Việt, giọng nói tiếng Việt, ảnh thật và text + ảnh; lọc kết quả; xem sản phẩm; tìm và xem đơn hàng của khách hàng demo. AI chạy CPU, voice chọn local hoặc Azure Speech. Mọi ảnh sản phẩm phải là ảnh chụp thực tế từ mạng, có nguồn, tác giả và giấy phép; không tạo ảnh bằng AI.

Frontend Cortis đã cài sạch, typecheck/lint/17 unit tests/build đạt và 19/19 browser wiring tests đạt trên production preview; hai quality tests vẫn fail với labels giữ nguyên. Cortis chạy bằng React/TypeScript, hướng showroom với ảnh thật, màu đá sáng và đỏ rượu. Có tìm bằng mô tả tiếng Việt, transcript/voice, ảnh, kết hợp; bộ lọc, chi tiết sản phẩm, tra đơn scoped C001 và nguồn ảnh qua API thật. Bộ 15 query hiện tại dùng calibration/smoke nhỏ, không chứng minh chất lượng trên dữ liệu độc lập. Azure thật chưa được nghiệm thu từ các test adapter.

## Chạy frontend

Giữ backend ở terminal riêng trên port 8000. Trong terminal thứ hai:

```powershell
Set-Location -LiteralPath 'D:\PROJECTS\ISA-D\assignment6_demo\frontend'
npm ci
npm run dev
```

Mở **http://127.0.0.1:5173/**. Swagger: **http://127.0.0.1:8000/docs**. Frontend proxy API sang backend; không đặt Azure key vào frontend. Direct routes `/products/P001`, `/orders/O001`, `/credits` hỗ trợ refresh. Script tương đương: `./scripts/run_frontend.ps1` từ root demo.

```powershell
npm run typecheck
npm run lint
npm test
npm run build
$env:PLAYWRIGHT_BROWSERS_PATH = 'D:/PROJECTS/ISA-D/assignment6_demo/runtime/browsers'
npx playwright install chromium
npm run test:e2e
```

`npm run preview` phục vụ bản build trên port 5173 và dùng cùng proxy backend; dừng dev server trước khi chạy preview. Model/runtime, env, node_modules và dist nằm ngoài Git; clean checkout cần setup backend và tải model theo hướng dẫn. Các gate nghiệm thu đầy đủ được đối chiếu riêng trong [docs/10_TESTING_ACCEPTANCE.md](docs/10_TESTING_ACCEPTANCE.md).

Nhập lại demo có validation, preview trước khi áp dụng và giữ dữ liệu gốc:

```powershell
& .\backend\.venv\Scripts\python.exe scripts\import_catalog.py --help
& .\backend\.venv\Scripts\python.exe scripts\apply_catalog.py --help
& .\backend\.venv\Scripts\python.exe scripts\seed_orders.py --apply
& .\backend\.venv\Scripts\python.exe scripts\verify_expanded_demo.py
```

Các quyết định chính:

- FastAPI/Python cho application và API; React/TypeScript/Vite cho website.
- Text: `sentence-transformers/clip-ViT-B-32-multilingual-v1`, có tiếng Việt; ảnh: `sentence-transformers/clip-ViT-B-32`. Hai encoder được thiết kế để dùng chung không gian 512 chiều.
- Azure Speech STT: `vi-VN`, region `southeastasia`. Khóa chỉ đặt trong `.env` cục bộ hoặc môi trường backend.
- JSON lưu metadata, NPZ lưu embedding, exact cosine scan cho dữ liệu demo. Không cần database server hay GPU.
- Khách hàng demo `C001` do server xác định. Giao diện và API không được tự chọn chủ đơn hàng.

`docs/CONTEXT.md` giữ nội dung phân tích gốc để đối chiếu. Khi implement, dùng bộ đặc tả mới theo quy tắc ưu tiên tại [docs/README.md](docs/README.md), không sao chép prototype 88 chiều hoặc biến voice thật thành transcript mô phỏng.
