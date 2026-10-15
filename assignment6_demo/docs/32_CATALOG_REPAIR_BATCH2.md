# Catalog repair batch 2 — 15/10/2026

Đã thay ảnh và sửa tên, hãng, màu, mô tả của P121–P130 bằng 10 ảnh balo thật từ Wikimedia Commons. Các ảnh cũ gồm người, sự kiện, poster, phong cảnh và sản phẩm không khớp metadata. Đã xem contact sheet của 11 ứng viên và xem riêng các ảnh cần xác nhận; loại R201 vì chưa đủ rõ là balo. Không suy hãng từ badge không đọc được. Không tạo ảnh hoặc chỉnh màu ảnh.

Review theo SHA-256: `data/catalog_repair_batch2_review.json`; nguồn, tác giả, giấy phép, URL và hash trong `data/image_sources.json` và [IMAGE_CREDITS.md](IMAGE_CREDITS.md). Giữ ID, category, giá, tồn kho seed và toàn bộ 30 order snapshots. Review canonical hiện gồm 26 sản phẩm, 18 ảnh thay qua hai đợt.

## Seed và cửa hàng đang chạy

Seed có 180 sản phẩm. Khôi phục candidate đúng hash và áp dụng bằng các CLI sẵn có:

```powershell
./backend/.venv/Scripts/python.exe scripts/prepare_catalog_repair.py --acquire-reviewed
./backend/.venv/Scripts/python.exe scripts/apply_catalog_repair.py
./backend/.venv/Scripts/python.exe scripts/apply_catalog_repair.py --apply
./backend/.venv/Scripts/python.exe scripts/validate_dataset.py
./backend/.venv/Scripts/python.exe scripts/update_image_credits.py
./backend/.venv/Scripts/python.exe scripts/build_index.py
```

Seed catalog `d314b582afc37e4e047d03a25ce0370d291a5db29e8114e1e9499bc1e3462530`; seed index `2d30312b1504b13aaef7ea3ae38071e84d8471d6c5cecfa227a2a848d4761ba0`.

Cửa hàng đã có immutable runtime release nên việc sửa seed không cập nhật live. Đã cập nhật riêng 10 sản phẩm bằng admin draft, upload ảnh/provenance và publish qua API thật, mỗi lần xây index CPU thật. Giữ giá, tồn kho live và P181 đã xuất bản từ mốc trước. Sau restart, API vẫn trả đủ 181 sản phẩm, đúng metadata và hash của 10 ảnh mới; tài khoản admin tạm đã thu hồi quyền và session.

Live catalog `b7443e1ae152504e7e8186f6d14031a2dfeec01ae8841b7b538f62989b9d73df`; live index `2c9298c7992e02758bfd8e1df0da00d4b9c33e7e1619ba2d9470451f37c465c2`. Không dùng fingerprint seed để nhận đã kiểm tra cửa hàng live.

## Kiểm chứng và giới hạn

127 backend tests đạt. Một bài Playwright trên API/model thật kiểm tra 10 ảnh, attribution, tìm theo hãng, 5 mô tả tiếng Việt, accessibility và màn hình 360/1440px. Cả 5 sản phẩm mục tiêu đứng đầu; đây là regression có nhãn từ catalog, chưa phải benchmark độc lập. Sau restart, 50 request regression CPU: hybrid 24/24 Hit@3, semantic 23/24; upload ảnh và multimodal qua API thành công. Ảnh query trùng catalog chỉ chứng minh cơ chế upload/inference.

Lệnh, exit code, lỗi test ban đầu và artifact được ghi trong [báo cáo](../artifacts/validation/CATALOG_REPAIR_BATCH2_REPORT.md). Không đổi API/vector/UML ở mốc dữ liệu này. Không gọi Speech hoặc dịch vụ trả phí. Azure vẫn chưa được cấu hình trên backend hiện tại; full live voice acceptance chưa đạt. Relevant policy cần calibration theo index mới; nearest hoạt động.

Các nhóm ảnh khác và nghi vấn nhiều góc chụp bị tách thành SKU trong [đợt 1](17_CATALOG_REPAIR.md) vẫn cần rà soát, trừ P121–P130 đã sửa ở đây. Frozen independent relevance, OOD và các gate đầy đủ ở docs10 còn pending. Thanh toán giữ COD/demo theo yêu cầu mới; không mở thêm module thanh toán.
