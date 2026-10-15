# E3 data integrity — repair batch 1

Cập nhật 15/10/2026: P121–P130 đã được thay ảnh và sửa metadata trong [đợt 2](32_CATALOG_REPAIR_BATCH2.md). Các fingerprint và evidence bên dưới mô tả lịch sử đợt 1; bản preview/applied đợt 1 được giữ tại `artifacts/validation/catalog-repair-batch1-preview.json` và `catalog-repair-batch1-applied.json`. Các nhóm khác trong danh sách pending vẫn chưa được đánh dấu đạt.

Rà trực quan toàn bộ 180 asset qua 9 contact sheets phát hiện nhiều false-positive từ tìm ảnh bằng filename. Các từ “backpack”, “Leatherjacket”, “sunglasses” trong tên nguồn không chứng minh ảnh là sản phẩm. Tên/màu/brand tự gán trước đây cũng sai. Không chấp nhận trường real_photo_review=passed được importer tự điền như bằng chứng nhìn ảnh.

## Đã áp dụng

16 SKU P140–P150, P153, P171, P175, P177, P180 được review rõ từng hash trong `data/catalog_repair_review.json`. Thay 8 ảnh: P140 landscape→tote; P141 stain→áo nguyên chiếc; P147 infographic→áo thật; P153 apples→áo khoác; P171 workshop→kính; P175/P177/P180 portraits→kính. Tên/brand/màu/description sửa theo ảnh. P142/143/144/145/146/148/149/150 sửa metadata, giữ ảnh. Unsupported On claims bị loại; P171 Ray-Ban có logo nhìn được. Giá/stock demo giữ nguyên, không suy giá từ ảnh. IDs và 30 order snapshots giữ nguyên theo hợp đồng.

Nguồn Commons, author/license/original/download URL/bytes/sha256 ở `data/catalog_repair_candidates.json` và manifest hiện tại. Các ảnh được tải dạng thumbnail máy chủ; bytes không chỉnh local, không generation/recolor/crop. Contact sheets chỉ là artifact rà soát, không asset catalog.

Index model CPU rebuild, catalog fingerprint mới `5f8be9f5eea8af06a30e5212bf7f345d8385c49623e37194953fab64ac0da58c`, index `491a74808967f07cfa4c85df2c5636abaf810ef05b5bceeee209a28d883cf03e`. Process dùng snapshot mới; index cũ không còn match catalog. Policies cũ không được coi calibrated với snapshot mới.

## Công cụ phục hồi và reproducibility

```powershell
./backend/.venv/Scripts/python.exe scripts/prepare_catalog_repair.py --acquire-reviewed
./backend/.venv/Scripts/python.exe scripts/apply_catalog_repair.py
./backend/.venv/Scripts/python.exe scripts/apply_catalog_repair.py --apply
./backend/.venv/Scripts/python.exe scripts/validate_dataset.py
./backend/.venv/Scripts/python.exe scripts/update_image_credits.py
./backend/.venv/Scripts/python.exe scripts/build_index.py
```

Acquisition mặc định chỉ chuẩn bị candidates trong ignored runtime và ghi pending; không đánh dấu đã review. `--acquire-reviewed` phục hồi bytes đúng pinned hash, source đổi bytes thì fail để review lại. Apply tool chỉ nhận descriptive metadata được review, không tự sửa price/stock/category. Reject duplicate IDs, pending/empty notes, hash drift, source path ngoài workspace. Preview validate toàn dataset/orders ở staging trước ghi; apply backup toàn data trong runtime và rollback khi validation lỗi. Chạy offline và dừng server trước đổi snapshot; restart sau build. CLI không gọi Speech.

## Evidence

`artifacts/validation/catalog-repair-preview.json`, `catalog-repair-applied.json` ghi before/after và notes; `catalog-repair-tests.xml` **47 tests passed**, bao gồm data/filter/repair guards. `catalog-repair-http.json` **48 real HTTP requests passed** trên 16 detail/media/exact-SKU color-filter flows. `artifacts/backend/dataset-validation.json` chỉ chứng minh schema/hash/decoding/order totals, không tự chứng minh visual gate. `artifacts/backend/search-expansion-real-model.json`: 50 CPU HTTP requests, hybrid category smoke 24/24 còn đạt; independent multimodal/OOD gate vẫn false. Bản trước sửa giữ tại `artifacts/validation/search-before-repair.json`.

Contact sheets baseline 001–180 và repaired-16 được xem bằng view_image, nằm `artifacts/validation/catalog-visual-audit/`. Không có browser screenshot mới hoặc live STT call trong mốc này. Ruff passed, build_index/validation/acquisition replay/apply exit0. Một lệnh in raw Unicode stdout lỗi encoding CP1252; sửa bằng JSON escaped, không lỗi data UTF-8. Test suite có upstream Starlette/httpx deprecation warning.

## Pending sau đợt 1

Gate toàn catalog **chưa đạt**. Các ảnh phải thay/kiểm tra sâu: P061/P064/P067/P070 display/group scenes; P088 collage; P098 historical boots; P101/P102/P110 museum sandals; P103 display; P117 leather macro; P121/P123–P129 people/event/poster/landscape; P164 process photo; P167 watch back; P178 sunglasses composition cần ảnh product tốt hơn. Phải kiểm tra thêm các góc ảnh cùng một sản phẩm nhưng bị tạo thành SKU khác, ví dụ P075/P077, P085/P087, P112–115, P143/144, P145/146, P161/162 và P168–170. Không có byte/source-URL duplicates không chứng minh các SKU là đối tượng khác nhau.

Metadata màu/brand/name còn phải sửa hầu hết P061–P180 theo source và ảnh; On/Prada/Timberland hoặc màu demo cũ không được tin tự động. Nhiều candidate tải mới cũng là poster/logo/portrait/street thay sản phẩm; vẫn pending/rejected, không import bulk. Không giảm số sản phẩm hay xóa case khó để pass. Tiếp tục tìm ảnh thật phù hợp, review hash-bound, chỉnh metadata và rebuild/calibrate mỗi mốc.

Variants/cart/wishlist/checkout/order mutations/full admin/frozen quality/.vpp/provider-specific live voice regression vẫn nằm phạm vi goal và tiếp tục sau sửa dataset. Không đánh dấu E3 hay toàn ecommerce complete.
