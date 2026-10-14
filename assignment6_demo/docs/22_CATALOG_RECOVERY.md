# Bộ sưu tập: bộ lọc, lỗi nhập liệu và recovery

Mốc 2026-10-15 sau admin operations. Giữ thiết kế Cortis hiện có; không đổi API hoặc thuật toán/model trong mốc này.

## Hành vi

- `in_stock=false` là không giới hạn tồn kho: checkbox bỏ chọn, không có chip “Còn hàng”. Xóa lọc loại bỏ cả tham số false khỏi URL nhưng giữ q/sort/limit.
- Khoảng giá có ràng buộc số nguyên0–1e9 từ input native. Nếu min>max, báo lỗi ngay tại hai trường và không gửi request hay thay URL. Giữ input để sửa; chỉnh input xóa lỗi cũ. Direct URL vẫn được backend validate422.
- Giá hợp lệ theo native input được chuẩn hóa thành chuỗi số nguyên trước khi gửi API: `1e3`→`1000`, `2000.0`→`2000`. Tránh việc browser chấp nhận số nhưng API từ chối cách biểu diễn. Backend không nới lỏng hợp đồng query integer.
- Kết quả rỗng có các hành động riêng: bỏ bộ lọc và giữ từ khóa; xóa từ khóa và giữ bộ lọc; hoặc chủ động xem toàn bộ bộ sưu tập. Xóa một phần giữ sort/limit và về trang đầu.
- Offset vượt dữ liệu có nút “Về trang đầu” giữ các lựa chọn. Không hiển thị thanh phân trang mâu thuẫn như trang5/4. Không tự âm thầm sửa URL hay bỏ bộ lọc.
- URL sai (tham số lạ/trùng/giá trị sai) có “Đặt lại tìm kiếm” bên cạnh thông báo lỗi và retry. Reset toàn bộ được ghi rõ bằng nhãn hành động; lỗi mạng/server vẫn có retry thông thường.
- Combobox chỉ tham chiếu listbox đang tồn tại. Escape đóng gợi ý và bỏ active descendant; Arrow/Enter vẫn dùng bàn phím để mở/chọn; Tab rời ô đóng gợi ý và giữ draft.

URL vẫn là nguồn điều kiện đã áp dụng. Các response cũ bị hủy/không được ghi đè kết quả mới. Facet và số lượng vẫn tính từ server trước pagination; AI search vẫn có route riêng và evidence model riêng.

## Evidence

- `npm run build`: exit0 (bao gồm TypeScript).
- `npm run lint`: exit0; `npm test`: exit0,17 passed.
- Từ workspace, đặt `$env:PLAYWRIGHT_BROWSERS_PATH = (Resolve-Path runtime/browsers).Path`; từ frontend chạy `npx playwright test e2e/browse-recovery.spec.ts e2e/browse.spec.ts --grep-invert 'responsive screenshots'`: exit0,13 passed trong7.5s ở lần cuối sau bổ sung normalize số. Tám test recovery mới và năm regression hiện có. Browser dùng API thật tại local server/production preview.
- Lần đầu chưa đặt browser cache env nên12 test không launch được Chromium, trước khi thao tác app. Report lỗi môi trường được giữ; sau đặt đúng path theo FRONTEND_VERIFICATION.md toàn bộ12 đạt, sau đó thêm ca normalize số và chạy lại13 đạt. Không coi lỗi launch là lỗi chức năng đã tái hiện.
- Các regression gồm keyword/alias/typo, SKU, facet/sort/URL/history, keyboard suggestions, delayed response và một request hybrid với encoder CPU thật. Test hybrid này chỉ xác nhận integration/contract, không chứng minh chất lượng mọi truy vấn.
- Không chạy lại screenshot suite trong mốc sửa hành vi này; không claim responsive/axe mới. Không thay backend, không gọi speech provider.

Raw: `artifacts/frontend/browse-recovery-results.json`, `browse-recovery-browser-start-failure.json`, `browse-recovery-verification.json` (source SHA256). Không kết luận toàn hệ thống complete: biến thể, dữ liệu/ảnh, CRUD/index publication, đổi trả, quality/live speech và acceptance clean checkout còn pending.
