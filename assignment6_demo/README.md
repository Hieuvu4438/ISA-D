# Assignment 6 Demo — backend tìm kiếm đa phương thức

Backend FastAPI đã triển khai cho đợt demo nhanh: text tiếng Việt, ảnh, text + ảnh, transcript voice, Azure Speech adapter, lọc, sản phẩm, ảnh/credits và đơn hàng khách demo. Frontend chưa triển khai. Xem [hướng dẫn chạy backend](docs/BACKEND_QUICKSTART.md) và [bằng chứng kiểm tra](artifacts/backend/).

Chạy tại thư mục này bằng PowerShell:

```powershell
./scripts/setup_backend.ps1
./scripts/run_backend.ps1
```

Mở **http://127.0.0.1:8000/docs** để thử các API. Setup tải hai model một lần; lượt khởi động và tìm kiếm dùng model local CPU. Speech cần `AZURE_SPEECH_KEY` ở environment hoặc `.env` riêng; region `southeastasia`, language `vi-VN`. Không chạy Azure trả phí trong setup hoặc smoke mặc định.

Đã chạy lại setup và khởi động backend: **85 tests đạt**, coverage **87,3%**, lint/compile/dependency check đạt; build index/calibration bằng model CPU thật đạt; **45 lượt kiểm tra HTTP đạt**. Đã sửa lỗi Unicode escape bất hợp lệ gây 500 và JSON float tràn bị phân loại sai. Xem [báo cáo chạy thử](artifacts/backend/RUN_REPORT.md). Sáu query tiếng Việt demo đúng top 1. Bộ calibration nhỏ còn một query text ngoài catalog trả false positive; không coi đây là benchmark chất lượng độc lập. Azure SDK/adapter đã kiểm tra bằng stub và cấu hình local, chưa gọi nhận dạng Azure thật.

Website mục tiêu: tìm sản phẩm bằng mô tả tiếng Việt, giọng nói tiếng Việt, ảnh thật và text + ảnh; lọc kết quả; xem sản phẩm; tìm và xem đơn hàng của khách hàng demo. AI chạy CPU, voice dùng Azure Speech. Mọi ảnh sản phẩm phải là ảnh chụp thực tế từ mạng, có nguồn, tác giả và giấy phép; không tạo ảnh bằng AI.

Frontend Cortis đang chạy bằng React/TypeScript, hướng showroom với ảnh thật, màu đá sáng và đỏ rượu. Có tìm bằng mô tả tiếng Việt, transcript/voice, ảnh, kết hợp; bộ lọc, chi tiết sản phẩm, tra đơn scoped C001 và nguồn ảnh qua API thật. Bộ 15 query hiện tại dùng calibration/smoke nhỏ, không chứng minh chất lượng trên dữ liệu độc lập. Azure thật chưa được nghiệm thu từ các test adapter.

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
npm test
npm run build
$env:PLAYWRIGHT_BROWSERS_PATH = 'D:/PROJECTS/ISA-D/assignment6_demo/runtime/browsers'
npx playwright install chromium
npm run test:e2e
```

`npm run preview` phục vụ bản build trên port 5173 và dùng cùng proxy backend; dừng dev server trước khi chạy preview. Model/runtime, env, node_modules và dist nằm ngoài Git; clean checkout cần setup backend và tải model theo hướng dẫn. Các gate nghiệm thu đầy đủ được đối chiếu riêng trong [docs/10_TESTING_ACCEPTANCE.md](docs/10_TESTING_ACCEPTANCE.md).

Các quyết định chính:

- FastAPI/Python cho application và API; React/TypeScript/Vite cho website.
- Text: `sentence-transformers/clip-ViT-B-32-multilingual-v1`, có tiếng Việt; ảnh: `sentence-transformers/clip-ViT-B-32`. Hai encoder được thiết kế để dùng chung không gian 512 chiều.
- Azure Speech STT: `vi-VN`, region `southeastasia`. Khóa chỉ đặt trong `.env` cục bộ hoặc môi trường backend.
- JSON lưu metadata, NPZ lưu embedding, exact cosine scan cho dữ liệu demo. Không cần database server hay GPU.
- Khách hàng demo `C001` do server xác định. Giao diện và API không được tự chọn chủ đơn hàng.

`docs/CONTEXT.md` giữ nội dung phân tích gốc để đối chiếu. Khi implement, dùng bộ đặc tả mới theo quy tắc ưu tiên tại [docs/README.md](docs/README.md), không sao chép prototype 88 chiều hoặc biến voice thật thành transcript mô phỏng.
