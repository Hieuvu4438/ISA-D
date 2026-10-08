# Kiểm chứng frontend

## Phạm vi và bằng chứng

Playwright chạy Chromium isolated trong `runtime/browsers`, context tạm, không thay profile Chrome/MCP configuration. Website dùng backend local thật, encoder CLIP CPU và ảnh chụp đã tải; provider speech trả phí không được gọi trong E2E.

Đợt đầu trên catalog 12 sản phẩm: **19/20 tests đạt**. Một assertion permission-denied dùng sai wording; DOM thực tế hiển thị “Chưa truy cập được microphone…” và fallback nhập tay hoạt động. Selector đã sửa, chưa ghi nhận rerun đạt cho tới khi có kết quả thật.

Các luồng đã đạt ở đợt đầu: text tiếng Việt (6 query đúng top 1), image/multimodal và trọng số, hard filters/giá 0/relevant empty, transcript nhập tay, product direct route/reload/back giữ draft/results/scroll, orders own/foreign/missing, credits, keyboard tab arrows, race response cũ, lỗi 422/retry, WAV sai được backend chặn trước Azure, degraded AI vẫn xem catalog/orders, recorder native với microphone synthetic chuyển PCM16 mono 16 kHz và đóng tracks khi rời mode.

Accessibility: axe không có serious/critical violations trên `/`, `/products/P001`, `/orders`, `/orders/O001`, `/credits`. Các happy-path tests theo dõi console/page errors có kết quả rỗng. Không có horizontal overflow trên 5 routes ở 360/768/1440 px. Đây là phạm vi đã test, không thay cho kiểm tra mic phần cứng/Azure recognition thật.

Impeccable static detector lần đầu trả `[]`, lưu ở `artifacts/frontend/impeccable-detector-initial.json`. Screenshot ban đầu chưa chờ lazy image load nên không được dùng làm bằng chứng visual. Capture đã sửa để scroll, đợi mọi `main img` tải thật, rồi chụp full page từ đầu trang. Visual review hợp lệ sẽ thực hiện trên catalog mở rộng 60 sản phẩm; tối đa một lượt xác nhận sau batch sửa lỗi.

## Catalog mở rộng

Người dùng đã xác nhận 60 fashion products, 12 categories và 30 orders. Lượt functional đầu trên catalog mở rộng đạt **16/20**, 4 fail: ba assertion top-1 semantic (Converse P006 bị P028 đứng đầu trong hai tests; query voice “túi da màu nâu” P011 bị P033 đứng đầu), và một selector category test chọn hero link P006 thay card catalog. Selector đã sửa scope `product-card`; chưa ghi nhận rerun đạt.

Wiring/navigation và voice integration đã tách khỏi quality baseline: kiểm tra UI hiển thị cùng API response và giữ state khi quay lại; các expected labels cũ vẫn giữ nguyên ở tests quality. Raw kết quả fail giữ tại `artifacts/frontend/e2e-expanded-initial-results.json`. Không đổi expected SKU thành model đang đứng đầu để đạt test. Final production confirmation còn pending.

Batch visual hợp lệ đầu tiên trên đủ 60 ảnh đã đạt: script đợi fonts + mọi ảnh load thật, chụp full page từ đầu trang ở 1440/768/360 px và các routes. 9 ảnh ở `artifacts/frontend/screenshots/initial-valid/`; crops first viewport ở `.impeccable/review/first-viewport-*.png`. Ảnh desktop/mobile catalog đã mở kiểm tra: ảnh thật xuất hiện đúng, không overflow và whole-card link đủ target; mũi tên nhỏ là decoration trong card link, không phải touchpoint riêng. Chưa phát hiện lỗi visual chặn demo trong những ảnh đã xem; fresh reviewer sẽ đánh giá toàn batch trước lượt xác nhận cuối.

## Chạy lại

Production confirmation sau sửa lỗi giữ scroll: **19/19 wiring tests đạt** trên Vite preview build và backend CPU thật; evidence [e2e-wiring-final.json](../artifacts/frontend/e2e-wiring-final.json). Bao gồm download WAV đúng bytes đã upload, revoke object URL khi xóa, native synthetic microphone cleanup, direct reload, owner isolation, filters, race và recovery. Mic synthetic/provider stub vẫn không là Azure live.

Hai tests `@quality` vẫn fail, giữ labels cũ: Converse P006 bị P028 đứng đầu; túi da có dây P011 bị P045; transcript ngắn túi nâu P011 bị P033. Raw production run [e2e-production-results.json](../artifacts/frontend/e2e-production-results.json) còn ghi một lỗi scope variable của test mic ở lượt trước; assertion đó đã chuyển về đúng test, rồi chạy lại 19 wiring tests đạt. Không báo toàn suite đạt hoặc đổi expected SKU để che regression.

Final visual có 11 captures ở `artifacts/frontend/screenshots/final/`, cùng batch 3 kích thước và 5 routes, thêm voice desktop/mobile. Reviewer yêu cầu bỏ side stripe của unavailable notice; verdict đã xác nhận **fix resolved**, phạm vi một finding. Review dùng role tương đương do custom agent không có trong harness; QUALITY BAR unavailable. Đây không phải approval chất lượng model hoặc live Azure. Không chạy detector lần hai.

```powershell
cd assignment6_demo/frontend
$env:PLAYWRIGHT_BROWSERS_PATH = (Resolve-Path ../runtime/browsers).Path
npx playwright test --grep-invert '@visual'
```

Backend phải `/health/ready` HTTP 200; frontend ở `127.0.0.1:5173`. Fixtures microphone/upload là sine synthetic, các test provider stub được ghi rõ trong tên; chỉ kiểm tra kỹ thuật và luồng UI. JSON, traces và screenshots ở `artifacts/frontend/` là evidence local, không phải dữ liệu catalog hoặc asset production.
