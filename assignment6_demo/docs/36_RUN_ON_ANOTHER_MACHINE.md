# Chạy Cortis trên máy khác

Bản bàn giao ngày 15/10/2026 đưa đầy đủ dữ liệu demo công khai vào Git và cung cấp import SQLite. Không cần cài MySQL hoặc SQL Server. Catalog/đơn mẫu đọc từ JSON; tài khoản, giỏ, tồn kho và đơn COD mới lưu vào SQLite tại `runtime/commerce/accounts.sqlite3`.

## Cài và chạy

Cài Git, Python **3.12 x64** (lệnh `python` trên PATH) và Node.js **22.12+** kèm npm. Pull code mới nhất rồi mở PowerShell tại `assignment6_demo`:

```powershell
git pull --ff-only
powershell -ExecutionPolicy Bypass -File .\scripts\setup_demo.ps1
```

Setup tạo `.env` từ mẫu nếu chưa có, cài dependencies theo lock, kiểm tra dữ liệu/ảnh, tải model đã ghim revision, tạo index CPU, import database, tạo hai tài khoản demo và build frontend. Lần đầu cần Internet để tải dependencies/model; inference tìm kiếm sau đó chạy CPU local. Setup không gọi speech trả phí và không chạy calibration nghiên cứu mặc định.

Chạy backend:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_backend.ps1
```

Mở terminal thứ hai tại cùng thư mục và chạy frontend:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_frontend.ps1 -Preview
```

Website: **http://localhost:5173**. API: **http://127.0.0.1:8000/docs**. Xem email/mật khẩu user và admin mới tạo trong `runtime/demo/access.json`. User demo gắn với C001 để xem đơn mẫu của mình; không được xem đơn của C002. Chạy lại setup giữ nguyên credentials và dữ liệu đã import.

Để dùng giọng nói, điền `GROQ_API_KEY` của bạn vào `.env`, giữ `SPEECH_PROVIDER=groq`, rồi khởi động lại backend. Khóa và mật khẩu không có trong Git. Khi chưa có khóa, tìm bằng mô tả/ảnh, quản lý sản phẩm và COD vẫn dùng được.

## Dữ liệu được bàn giao

- **181 sản phẩm / 12 danh mục**, đủ ảnh local và nguồn ảnh; bao gồm P181 đã xuất bản trên máy bàn giao.
- **183 dòng kho**: 181 SKU gốc và hai SKU size P041-M/P041-L. M có 3, L có 2; các dòng kho còn lại theo snapshot `data/demo_database.json`.
- **30 đơn mẫu lịch sử** trong `data/orders.json`. Đây là dữ liệu tra cứu đơn mẫu; lịch sử COD mới trong SQLite bắt đầu trống và lưu thật khi đặt đơn.
- Trạng thái bán của toàn bộ sản phẩm và cấu trúc các bảng nghiệp vụ SQLite được tạo tự động.

Có thể chỉ import sau khi đã setup backend:

```powershell
.\backend\.venv\Scripts\python.exe scripts/import_demo_database.py
.\backend\.venv\Scripts\python.exe scripts/prepare_demo.py
```

Lần đầu trả `applied: true`; lần sau `false`, không reset kho/đơn vừa thao tác. Snapshot kiểm tra fingerprint catalog và đơn trước khi ghi. Không sửa seed để thay sản phẩm của cửa hàng đã có runtime publication; dùng admin → xuất bản.

## Nếu máy đích đã có dữ liệu chạy cũ

Importer từ chối ghi đè database đã có hoạt động hoặc kho khác seed. Để có bản demo mới đúng snapshot, dùng một thư mục clone sạch và chạy setup ở đó; giữ bản cũ làm backup, không xóa runtime tùy tiện.

Git chuyển mã nguồn và snapshot demo, không chuyển tài khoản riêng, session, giỏ hoặc đơn COD từng phát sinh trên máy khác. Nếu cần giữ nguyên toàn bộ dữ liệu riêng cũ, dừng backend trước và sao lưu riêng `runtime/commerce/`, `runtime/catalog/`, `runtime/index/`, `runtime/demo/access.json` cùng `.env`; chuyển bảo mật ngoài Git và giữ chúng đồng bộ. Không chạy import snapshot vào bản dữ liệu riêng đang dùng. Model/cache có thể tải lại bằng setup backend. Bản bàn giao này không đưa database chứa thông tin riêng hoặc khóa vào repository.

## Bằng chứng kiểm tra

156 tests liên quan đạt. Bản nguồn tách riêng đã tạo SQLite mới, import hai lần, tạo tài khoản mới, build index CPU và chạy API thật: đăng nhập/phân quyền, ảnh P181, size/kho, tìm kiếm, tra cứu đơn đúng chủ, COD/hủy/hoàn kho. Có tái sử dụng cache dependencies/model trên máy kiểm tra; chưa chạy tải lại toàn bộ trên máy vật lý thứ hai. Xem [báo cáo](../artifacts/validation/PORTABLE_DATABASE_REPORT.md).
