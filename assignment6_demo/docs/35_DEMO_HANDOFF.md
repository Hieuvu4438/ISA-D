# Bàn giao demo khách hàng — 15/10/2026

Theo yêu cầu mới nhất, chốt bản demo có giao diện và các luồng ecommerce phổ biến; không mở rộng edge case hoặc chặn bàn giao bằng các gate production/nghiên cứu. Thanh toán COD mô phỏng, không thu tiền thật. Đây là mốc kết thúc nhiệm vụ demo theo phạm vi mới, không phải chứng nhận đáp ứng toàn bộ tiêu chí nghiên cứu cũ ở docs10.

## Mở demo trên máy hiện tại

- Website: **http://localhost:5173**.
- API: **http://127.0.0.1:8000/docs**.
- Tài khoản **admin** và **user** đã tạo riêng. Xem email/mật khẩu trong `runtime/demo/access.json` trên máy; file được ignore, không có trong Git. Tài khoản mới tự đăng ký cũng dùng được.
- Groq đã cấu hình trong `.env` cục bộ và nhận dạng tiếng Việt thật thành công. Khóa không nằm trong source, artifact hoặc frontend bundle. Khi chuyển máy, tự điền `GROQ_API_KEY` vào `.env` theo `.env.example`.

## Chạy lại / cài trên máy khác

Yêu cầu Python3.12 và Node22.12+. Từ thư mục `assignment6_demo`:

```powershell
./scripts/setup_backend.ps1
./backend/.venv/Scripts/python.exe scripts/prepare_demo.py
./scripts/run_backend.ps1
```

Terminal thứ hai:

```powershell
cd frontend
npm ci
npm run build
npm run preview
```

Setup cài application package editable và tạo index CPU thật. Lần đầu cần tải model; mặc định không chạy calibration hoặc gọi speech trả phí. Muốn chạy kiểm định calibration riêng: `./scripts/setup_backend.ps1 -Calibrate`. Demo dùng chế độ “Sản phẩm gần nhất”.

`prepare_demo.py` là thao tác chủ động để tạo hai tài khoản local, sinh mật khẩu ngẫu nhiên và ghi vào file runtime đã ignore. Chạy lại giữ nguyên credentials, không reset tài khoản có sẵn. Không tự tạo admin khi server khởi động. Với máy khác, sao chép `.env.example` thành `.env`, chọn `SPEECH_PROVIDER=groq` và điền khóa trước khi chạy backend; nếu chưa cấu hình, nhập mô tả/transcript vẫn demo được.

Seed Git có **180 sản phẩm / 12 danh mục** và 30 đơn mẫu lịch sử. Máy hiện tại có **181 sản phẩm** vì P181 đã được admin xuất bản từ mốc trước. Đây là khác biệt runtime đã biết, không phải thiếu dữ liệu. Size demo cần được admin phân kho; P041-M/L đã có trên máy hiện tại. Khi có runtime release, sửa sản phẩm qua admin và bấm xuất bản; sửa seed đơn thuần không thay cửa hàng đang chạy.

## Kịch bản trình bày 8–10 phút

1. **Khám phá:** mở Bộ sưu tập; thử danh mục, thương hiệu, giá, sắp xếp, trang sau và xem chi tiết sản phẩm/nguồn ảnh.
2. **Tìm kiếm:** thử `balo màu hồng`, `đồng hồ Fossil`, `đồng hồ Citizen`, `giày chạy bộ hãng On`, `áo thun size M`. Bật “Chỉ còn hàng” để kiểm tra đúng size. Có tìm bằng ảnh và mô tả + ảnh.
3. **Giọng nói:** chọn Giọng nói → ghi âm hoặc tải WAV → Nhận dạng → kiểm tra/chỉnh transcript → Tìm sản phẩm. Mic yêu cầu quyền trình duyệt. Groq hiện đã hoạt động; không gắn nhãn kết quả Groq thành Azure.
4. **Khách hàng:** đăng nhập tài khoản user, lưu yêu thích, thêm sản phẩm/size vào giỏ, đổi số lượng, nhập địa chỉ và đặt COD. Mở lịch sử/chi tiết đơn, hủy đơn đang xử lý nếu cần.
5. **Admin:** đăng nhập tài khoản admin trong cửa sổ khác → `/admin`; tìm sản phẩm, sửa tồn kho, soạn metadata/ảnh nguồn và xuất bản. Thử ngừng/mở bán. Chuyển đơn vừa tạo sang giao hàng/đã giao; quản lý user/role và xem audit.

Các luồng giỏ, đặt đơn và quản lý kho ghi thật vào SQLite local. Dữ liệu giá/tồn và trạng thái thanh toán là demo; không dùng thông tin cá nhân thật để trình bày.

## Kết quả đã kiểm tra

- 517 backend tests đã đạt ở mốc code ứng dụng gần nhất; mốc dữ liệu/bàn giao này chạy thêm 151 tests liên quan, đều đạt.
- 20 bài Playwright trên API thật đạt: tài khoản, admin/role, kho, browse/search, authoring/preflight CPU, wishlist/cart, COD/order/cancel và Groq.
- Hai lần gọi Groq thật với cùng một mẫu giọng người thật tiếng Việt FLEURS: một lần API, một lần browser; đều thành công. Browser kiểm tra chỉnh transcript sang câu thời trang rồi tìm sản phẩm. Không nhận đây là test mic vật lý hoặc benchmark giọng thời trang.
- Build frontend từ bản nguồn tách riêng đạt; database mới + model CPU thật chạy text/ảnh, đăng ký, giỏ, COD, xem/hủy đơn và hoàn tồn. Tái sử dụng dependencies/model cache hiện có; không nhận đã cài mới toàn bộ dependencies từ mạng.
- Đã thay thêm 9 ảnh sai ở P061/P064/P067/P070/P088/P098/P117/P164/P167, sửa metadata, giữ giá/stock/order snapshots và xuất bản live qua admin API với index CPU mới.

Bằng chứng, fingerprints và lệnh thực chạy: [DEMO_HANDOFF_REPORT](../artifacts/validation/DEMO_HANDOFF_REPORT.md). Chi tiết lịch sử các module tiếp tục nằm ở docs15–34.

## Sau demo, nếu phát triển tiếp

Chưa làm trong phạm vi chốt này: payment/refund thật, variant màu/giá nâng cao, half-size/quy đổi hệ size, làm sạch hết catalog, benchmark relevance/OOD độc lập, Azure thật, triển khai public và UML editable hoàn chỉnh. Không cần các phần này để chạy kịch bản demo trên. Không tự triển khai public hoặc mở thêm tích hợp trả phí.
