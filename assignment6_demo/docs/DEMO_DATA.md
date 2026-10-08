# Dữ liệu demo Cortis mở rộng

Người dùng chọn 60 sản phẩm thời trang và khoảng 30 đơn hàng, ưu tiên danh mục đa dạng. Catalog mục tiêu có 12 danh mục, mỗi danh mục 4–6 sản phẩm: giày chạy bộ, giày địa hình, giày thường ngày, boots, sandal, túi xách, balo, túi tote, áo thun, áo khoác, đồng hồ và kính mát. Ảnh sản phẩm là ảnh chụp thật đã tải từ mạng, lưu nguồn và giấy phép trong `data/image_sources.json`; giá, tồn kho và đơn hàng là dữ liệu giả định phục vụ demo.

## Seed đơn hàng

`scripts/seed_orders.py` giữ nguyên O001–O003 và chỉ thêm các ID còn thiếu tới O030. Mỗi đơn mới có 1–4 dòng sản phẩm, số lượng 1–3, snapshot tên/giá lấy từ catalog lúc import. Tổng dòng và tổng đơn được kiểm tra trước khi ghi. Bốn trạng thái `processing`, `shipped`, `delivered`, `cancelled` đều xuất hiện. Ngày UTC cố định trong tháng 9 và đầu tháng 10/2026 giúp tái hiện demo.

Kết quả yêu cầu là 24 đơn của C001 và 6 đơn của C002. Backend chỉ cho xem C001: sáu đơn C002 dùng để kiểm chứng cách ly quyền, phải trả cùng 404 và thông báo như đơn không tồn tại. Không có tên, địa chỉ, email hoặc số điện thoại khách hàng thật. Seed không thay đổi tồn kho khi tạo dữ liệu demo.

Chạy từ `assignment6_demo` sau khi import đủ 60 sản phẩm:

```powershell
& .\backend\.venv\Scripts\python.exe scripts\seed_orders.py
& .\backend\.venv\Scripts\python.exe scripts\seed_orders.py --apply
& .\backend\.venv\Scripts\python.exe scripts\validate_dataset.py
```

Lệnh đầu chỉ tạo `runtime/order-seed-preview.json`, thuộc vùng ignored. `--apply` thay file đơn hàng bằng ghi nguyên tử sau validation. Chạy lại giữ nguyên mọi snapshot đã tồn tại; không tự cập nhật giá lịch sử. ID ngoài O001–O030 làm script dừng để tránh ghi đè dữ liệu ngoài phạm vi.

## Kiểm chứng dữ liệu và API thật

Sau thay ảnh/mô tả, phải rebuild index và calibration rồi khởi động lại backend. Không reuse policy/fingerprint của catalog cũ. Khi `/health/ready` trả 200 và `/api/v1/meta` báo `product_count=60`, chạy:

```powershell
& .\backend\.venv\Scripts\python.exe scripts\verify_expanded_demo.py
& .\backend\.venv\Scripts\python.exe scripts\benchmark_backend.py --requests-per-mode 30
```

`artifacts/backend/expanded-demo.json` ghi các kiểm tra thực tế:

- Toàn bộ 60 product detail, ảnh phục vụ qua API khớp SHA256/bytes/ETag của file có provenance và credit.
- Phân trang 20 sản phẩm ở offset 0/20/40 và trang rỗng 60/80; đủ ID, không trùng/mất sản phẩm.
- Từng danh mục lọc trên toàn bộ catalog; top_k=20 phải trả chính xác tập ID đủ điều kiện. Brand, cận giá bao gồm và còn hàng được kết hợp, đối chiếu trực tiếp metadata.
- Cả summary và detail của 30 đơn, tổng tiền/snapshot đúng; 24 đơn C001 xem được, sáu đơn C002 cùng 404 với mã không tồn tại.
- Ranh giới text/category/brand/top_k/giá/phân trang/owner, ảnh hỏng và query ngoài contract; backend vẫn ready sau lỗi.
- Tìm text tiếng Việt không lọc cho 12 danh mục; ghi nguyên kết quả và category Hit@3 thực đo. Image/multimodal dùng ảnh catalog để kiểm tra decode/alignment cho mỗi danh mục; transcript nhập tay dùng encoder thật nhưng được ghi rõ không phải Azure.
- Relevant OOD với fixture pizza đã có ghi kết quả/ngưỡng thực tế và kiểm tra policy mới khớp snapshot.

Các probe category và ảnh catalog là smoke, không thay frozen test độc lập theo `10_TESTING_ACCEPTANCE.md`. Một HTTP 200 với payload/rank đúng chỉ chứng minh pipeline thực hiện đúng contract; không tự chứng minh mọi truy vấn đúng ý người dùng. Báo cáo giữ số đo không đạt thay vì sửa nhãn để tăng điểm.

## Hiệu năng

`artifacts/backend/performance.json` ghi 30 request tuần tự cho từng mode text/image/multimodal, cộng ba lượt warm-up không tính vào latency. Có phần cứng, phiên bản package, model revision, index/dataset/lock hash và raw sample cho từng lượt. p95 mục tiêu ≤5 giây mỗi mode; lỗi được lưu và làm gate fail, không bỏ outlier. Benchmark chạy khi không có batch QA khác để tránh tranh CPU.

Cold start chưa đo trong lệnh này vì backend đã tải model. Chi phí/độ trễ Azure và thời gian ghi âm không nằm trong benchmark. Không có lệnh nào trong tài liệu tự gọi Azure trả phí. Azure vi-VN và frozen quality split cần evidence riêng trước nghiệm thu toàn bộ website.

## Evidence hiện tại

Catalog đã import 60 sản phẩm và 30 đơn; lượt HTTP kiểm tra ngày 08/10/2026 lúc 05:35 UTC chạy command ở trên với exit code 0. [expanded-demo.json](../artifacts/backend/expanded-demo.json) ghi **271/271 kiểm tra contract/dữ liệu đạt**, không có kiểm tra thất bại. Index của lượt này là `fbb823590b942a7432948c7482b97b9fa7323f33f866b563ba34a7bdcf98bd13`.

| Danh mục | Số sản phẩm |
| --- | ---: |
| Giày chạy bộ | 5 |
| Giày thường ngày | 6 |
| Giày chạy địa hình | 4 |
| Túi xách | 5 |
| Boots, sandal, balo, túi tote, áo thun, áo khoác, đồng hồ, kính mát | Mỗi danh mục 5 |

Category Hit@3 của 12 câu tiếng Việt tổng quát không áp hard filter là **7/12 (58,3%)**. Năm category không xuất hiện trong Top3 của probe tương ứng: giày chạy bộ, giày địa hình, giày thường ngày, túi xách và túi tote. Đây là giới hạn chất lượng thực đo cần giữ công khai; 271 kiểm tra contract đạt không đồng nghĩa tìm kiếm ngữ nghĩa mọi danh mục chính xác. Không thay câu hỏi hoặc expected category theo rank để làm điểm đẹp hơn.

Image và multimodal dùng ảnh catalog có self Hit@3 **12/12 mỗi mode** trên 12 đại diện; chỉ chứng minh alignment smoke. Pizza relevant bị từ chối ở cả ba mode với policy mới; fixture này thuộc calibration smoke nên không tính là frozen OOD test độc lập. Các hard category/brand/price/stock filters đều trả chính xác tập metadata đủ điều kiện. Toàn bộ 24 đơn C001 xem được, sáu đơn C002 bị ẩn như đơn không tồn tại.

Benchmark chạy sau khi QA chức năng kết thúc, ngày 08/10/2026 lúc 05:39 UTC, exit code 0. [performance.json](../artifacts/backend/performance.json) giữ đủ **90 measured requests + 3 warm-ups**, không có lỗi và snapshot không đổi trong lượt chạy (tổng 25,84 giây).

| Mode | Requests đạt / tổng | Wall p95 | Server p95 | Mục tiêu wall p95 |
| --- | ---: | ---: | ---: | ---: |
| Text | 30/30 | 81,69 ms | 74,15 ms | ≤5.000 ms: đạt |
| Image | 30/30 | 380,78 ms | 370,79 ms | ≤5.000 ms: đạt |
| Multimodal | 30/30 | 455,44 ms | 445,29 ms | ≤5.000 ms: đạt |

Máy đo: Windows 11 AMD64, Intel Family 6 Model 154, 16 logical CPUs, RAM vật lý khoảng 15,70 GiB; Python 3.12.8, PyTorch `2.14.1+cpu`, Sentence Transformers 6.1.0. Raw sample và hash đầy đủ ở JSON. Mỗi request tuần tự đo cả HTTP/upload/queue/inference; không có lượt QA inference chạy đồng thời. Số liệu chỉ áp dụng máy và catalog này, không suy ra khả năng chịu tải production. Git commit trong artifact là baseline repository tại lúc chạy; script hash, lock hash và fingerprints ghi phiên bản nội dung thực dùng, có thể gồm thay đổi chưa commit.

Cold startup **chưa đo** vì process đã tải model. Azure báo `unconfigured` ở thời điểm verification; hai lệnh trên không gọi Azure. Nghiệm thu Azure và frozen quality test vẫn cần evidence riêng.
