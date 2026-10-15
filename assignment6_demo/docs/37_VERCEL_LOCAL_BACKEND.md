# Vercel + backend local qua HTTPS

Website đã triển khai: **https://cortis-demo.vercel.app**.

Frontend là bản build React thật trên Vercel. `/api/*` và `/health/*` được proxy qua Cloudflare Tunnel về FastAPI local cổng **8003**, model CLIP CPU thật và SQLite riêng. Trình duyệt gọi cùng domain Vercel; session cookie HttpOnly/Secure/SameSite=Lax, không đưa API key hoặc database vào frontend.

## Vận hành bản đang chạy

- Giữ máy này bật, có mạng, không sleep; giữ backend public và cloudflared chạy. Frontend vẫn mở được khi máy tắt nhưng API/tìm kiếm/đơn hàng sẽ không hoạt động.
- Public demo dùng `runtime/public-demo/app/`: đầy đủ catalog181/ảnh/kho/size/30 đơn mẫu, tài khoản và đơn phát sinh riêng. Dữ liệu local cổng8000 không bị dùng làm database public.
- Email/mật khẩu admin và user public nằm trong `runtime/public-demo/app/runtime/demo/access.json`. Không dùng nhầm file tài khoản local `runtime/demo/access.json`. Khách có thể tự đăng ký qua giao diện.
- Khóa Groq nằm riêng trong `runtime/public-demo/app/.env`; không nằm trong Vercel hoặc Git. Không gọi voice trả phí trong bước deploy/kiểm tra này.
- Vercel project: `hieuvus-projects-eea5c248/cortis-demo`. Đã ngắt liên kết tự build từ Git để các lần push repo tổng không thay deployment đã đóng gói.

Không cần mở port router. Cloudflare Quick Tunnel tạo URL tạm và đổi hostname mỗi khi khởi động đường hầm mới; khi đổi phải cập nhật proxy rồi deploy frontend lại. Đây là bản demo phụ thuộc máy local, không phải hosting backend24/7. Xem [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) và [Vercel rewrites](https://vercel.com/docs/routing/rewrites).

## Khởi động lại hoặc chuyển máy host backend

Từ thư mục `assignment6_demo`, làm setup theo [docs36](36_RUN_ON_ANOTHER_MACHINE.md), rồi:

```powershell
.\backend\.venv\Scripts\python.exe scripts/prepare_public_demo.py
```

Script tạo dataset/database riêng nếu chưa có, tái sử dụng model/index local đã setup. Chạy lại không reset tồn kho hoặc đơn. Nó không copy database local hoặc khóa. Trong `runtime/public-demo/app/.env`, đặt:

```dotenv
COOKIE_SECURE=true
CORS_ORIGINS=https://cortis-demo.vercel.app
SPEECH_PROVIDER=groq
GROQ_API_KEY=
```

Điền khóa riêng nếu cần voice. Giữ nguyên dòng CORS domain frontend thực tế; không dùng wildcard. Terminal backend:

```powershell
.\scripts\run_public_backend.ps1
```

Nếu chưa có cloudflared, tải binary chính thức vào thư mục đã ignore:

```powershell
New-Item -ItemType Directory -Force runtime/tools | Out-Null
Invoke-WebRequest https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe -OutFile runtime/tools/cloudflared.exe
```

Terminal thứ hai:

```powershell
.\scripts\run_public_tunnel.ps1
```

Lấy URL `https://....trycloudflare.com` vừa in. Terminal thứ ba đóng gói frontend đã build và proxy:

```powershell
.\backend\.venv\Scripts\python.exe scripts/prepare_vercel_site.py --backend-url https://YOUR-TUNNEL.trycloudflare.com
```

Nếu `runtime/public-demo/site` đã có từ lần trước, thêm `--update-proxy` để chỉ cập nhật đường hầm. Khi cần cập nhật code frontend, build lại và tạo package trong thư mục site mới sau khi đổi tên bản cũ để giữ backup; không copy `.env`, runtime hoặc toàn bộ repo vào deployment.

Deploy vào project đã có, dùng tài khoản được cấp quyền:

```powershell
$demoRoot = (Get-Location).Path
$demoAuth = Join-Path $demoRoot 'runtime/tools/vercel-auth'
npx.cmd --yes vercel@64.1.0 login --global-config $demoAuth
npx.cmd --yes vercel@64.1.0 link --yes --project cortis-demo --scope hieuvus-projects-eea5c248 --cwd runtime/public-demo/site --global-config $demoAuth
npx.cmd --yes vercel@64.1.0 deploy --prod --cwd runtime/public-demo/site --global-config $demoAuth
```

Chỉ upload frontend assets đã build và `vercel.json` proxy. URL mới của tunnel không cần đưa vào Git. Nếu chuyển máy và muốn giữ đơn public cũ, dừng backend rồi chuyển bảo mật toàn bộ `runtime/public-demo/app/`; không commit nó. Nếu bắt đầu demo mới, chạy seed/import như trên.

## Kiểm tra lại từ Internet

Mở website bằng cửa sổ ẩn danh, thử tìm kiếm, đăng ký/đăng nhập và COD. Bộ kiểm tra browser public dùng API thật, tạo tài khoản/đơn demo rồi hủy hoàn kho; không gọi speech:

```powershell
cd frontend
$env:PUBLIC_DEMO_URL='https://cortis-demo.vercel.app'
$env:PLAYWRIGHT_BROWSERS_PATH=Join-Path (Split-Path $PWD -Parent) 'runtime/browsers'
npx.cmd playwright test --config playwright.public.config.ts
```

Cần cài Chromium của Playwright nếu máy chưa có. Test admin dùng credentials public local ở đường dẫn nêu trên. Evidence thực tế: [VERCEL_PUBLIC_REPORT](../artifacts/validation/VERCEL_PUBLIC_REPORT.md).
