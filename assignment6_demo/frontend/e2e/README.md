# E2E website demo

Backend thật ở `127.0.0.1:8000` phải ready; frontend chạy ở `127.0.0.1:5173`. Các test chức năng dùng API và CLIP CPU thật với ảnh đã tải. Chỉ các test có tên `deterministic ... stub` hoặc `synthetic ...` thay response/thiết bị nhằm kiểm tra lỗi, race và microphone. Không chạy nhận dạng Azure trả phí.

Từ thư mục `frontend`, PowerShell:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = (Resolve-Path ../runtime/browsers).Path
npx playwright test --grep-invert '@visual'
```

Chromium dùng context tạm, không mở/sửa profile Chrome của người dùng. Evidence JSON/trace ở `artifacts/frontend/`; fixtures sine WAV chỉ phục vụ kỹ thuật, không chứng minh speech recognition thật.

Visual QA theo impeccable được thực hiện sau khi UI hoàn chỉnh: một lượt batched desktop/tablet/mobile, sửa lỗi trong một batch và tối đa một lượt xác nhận. Khi cần thực hiện lượt đầu:

```powershell
npx playwright test visual.spec.ts --grep '@visual'
```

Lượt xác nhận sau sửa lỗi dùng `VISUAL_ROUND=confirmation` và cùng lệnh. Screenshot đầu trang ở 1440/768/360 px, catalog ở desktop/mobile, và các trang detail/order/credits; không tạo hoặc sửa ảnh sản phẩm. Kết quả của đợt hoàn thiện được ghi tại `docs/FRONTEND_VERIFICATION.md`.
