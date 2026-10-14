# E3 — giỏ hàng và danh sách yêu thích

Mở rộng ecommerce theo yêu cầu mới. Tài khoản đăng nhập có giỏ và wishlist riêng lưu SQLite; không mặc định C001. Mỗi product ID hiện là một lựa chọn catalog, chưa có size/variant SKU. Phải hoàn thiện variants và checkout/order transactions ở mốc sau, không coi giỏ hiện tại là luồng mua hàng đầy đủ.

## Hành vi và data contract

ShoppingRepository dùng cùng AccountRepository SQLite connection với parameterized SQL/FK account. Tables:

- cart_versions: user_id PK/FK account, version integer≥0.
- cart_items: (user_id,product_id) PK, quantity integer1–99.
- wishlist_items: (user_id,product_id) PK.

Không lưu price/stock từ browser. Cart GET hydrate metadata/price từ validated catalog snapshot hiện tại của process. Tính unit_price_vnd × quantity và subtotal VND server. Khi restart với catalog mới, cart tự dùng metadata/price mới; không sửa order snapshot lịch sử. Stock kiểm tra khi set quantity, đọc issue khi cart cũ vượt stock. Cart không reserve hoặc decrement stock. Checkout cần transaction đọc inventory mới + reserve/decrement + snapshot price + insert order; vẫn pending.

Cart mutations là desired-state quantity, không increment mù. Body bắt buộc version từ lần GET/mutation gần nhất. BEGIN IMMEDIATE → compare version → mutate → bump version chỉ khi quantity thực sự thay đổi. Concurrent updates cùng version chỉ một bên thành công; bên kia 409 CART_CHANGED. Same desired quantity/current version là no-op. Replay với version cũ không auto-apply. Quantity0 xóa, kể cả product bị gỡ khỏi catalog. Giới hạn 100 line items/user; tối đa99 quantity/line. Wishlist desired-state saved true/false idempotent, tối đa100 entries; bỏ lưu SKU đã gỡ được phép.

GET cart snapshot version và item rows trong một read transaction. Wishlist định danh user server, không public/query customer context. Các SKU thiếu catalog vẫn giữ entry cho thao tác xóa/recovery, product=null và line price0; không biến thành SKU khác. `issue=PRODUCT_UNAVAILABLE|OUT_OF_STOCK|INSUFFICIENT_STOCK|null`, has_issues cho summary. available_quantity=min(99,current stock). Theo phạm vi hiện tại total chỉ subtotal; không thu shipping/tax/payment.

## HTTP API

| Method | Endpoint | Body | Success |
| --- | --- | --- | --- |
| GET | `/api/v1/cart` | Không query | request_id,cart |
| POST | `/api/v1/cart/items` | product_id,quantity,version | request_id,cart sau update |
| GET | `/api/v1/wishlist` | Không query | request_id,items,total |
| POST | `/api/v1/wishlist/items` | product_id,saved | request_id,items,total |

Tất cả require phiên HttpOnly hợp lệ, anonymous/expired401. Query fields bất kỳ bị422; context headers/customer_id vẫn rejected global. User/admin đều có giỏ riêng; admin role không bypass ownership. JSON strict/extra forbid, product_id pattern ^P[0-9]{3}$; quantity/version strict ints reject boolean/string/float, quantity0–99, version0–1e9; saved strict boolean. Mutation bắt buộc JSON và `X-Cortis-Intent: commerce`; global origin allowlist và credential CORS như accounts. Không auto retry POST. Missing product khi add/save404, stock thiếu409 INSUFFICIENT_STOCK, cap422 CART_LIMIT/WISHLIST_LIMIT. Currency VND integer, no-store/request_id envelope cùng baseline.

Cart wire: version,items[],item_count(sum quantities),subtotal_vnd,currency="VND",has_issues,stock_reserved=false. Item: product_id,product summary|null,quantity,unit_price_vnd,line_total_vnd,available_quantity,issue. Wishlist items: product_id,product summary|null. Không user_id/customer_id/internal image_path/DB path/password hashes/session token trong response.

## UI/UX

Header links Yêu thích/Giỏ hàng/Tài khoản; `/cart`/`wishlist` support direct reload. Product detail có quantity, thêm giỏ, toggle yêu thích (aria-pressed), sold-out disabled, trạng thái/error và login recovery. Product add và wishlist add đọc cart version mới rồi set desired quantity=existing+requested; double clicks bị khóa bằng ref trong cùng workflow, cross-tab conflict không silent overwrite. Pending wishlist GET không overwrite mutation response.

Cart: summary thực, update quantity form/xóa, lỗi stock/discontinued, empty CTA về catalog/wishlist, version conflict reload state mới và giữ thông báo để người dùng quyết định. Không tự submit lại request cũ. Wishlist: lưu qua reload, bỏ lưu, thêm một sản phẩm vào giỏ khi còn stock, giữ wishlist entry sau add. Auth expiry dọn private results khỏi page và hiển thị login link; unmount abort GET và bỏ apply response muộn.

UI stone/wine Cortis, ảnh thật API, nav keyboard/screen reader, field labels, disabled/loading/error/empty, responsive product list và summary. Catalog images/data defects còn pending theo17; shopping UI không chứng nhận catalog thật toàn bộ.

## UML/code mapping

```mermaid
sequenceDiagram
  actor U as Customer
  participant UI as ProductShopping / CartPage
  participant API as Shopping routes
  participant A as ShoppingService
  participant DB as ShoppingRepository SQLite
  participant P as ProductRepository
  U->>UI: Chọn quantity và thêm vào giỏ
  UI->>API: GET cart với session cookie
  API->>API: Resolve server identity
  API->>DB: Read cart version + items snapshot
  API-->>UI: cart với prices hiện tại
  UI->>API: POST product_id, quantity, version + commerce intent
  API->>API: JSON/origin/identity validation
  API->>A: Set desired quantity(user_id)
  A->>P: Validate product và stock
  A->>DB: Transaction compare version + update
  alt Stale version hoặc stock thiếu
    API-->>UI: 409; không ghi đè
    UI->>API: GET snapshot mới khi CART_CHANGED
  else Version khớp
    DB-->>A: Commit
    A->>P: Hydrate current price/metadata
    API-->>UI: cart totals và version mới
  end
```

Data shopping_repository.py → application shopping_service.py → presentation shopping.py, main DI. UI ProductShopping, ShoppingPages. Tests test_shopping.py (SQLite thật; catalog-change case dùng double rõ nhãn), browser shopping.spec.ts API thật. Mermaid không thay .vpp editable pending.

## Verification và phần còn thiếu

Evidence `artifacts/backend/SHOPPING_REPORT.md`; default tests không gọi STT/model providers. Không checkout giả, không thanh toán thật hoặc shipping integration. Variants/sizes/guest-cart merge, checkout/COD/idempotency/stock transaction, order states/list/cancel/returns/full admin tiếp tục ở E3–E6. Giá/tồn kho catalog còn demo; không gắn stock UI thành warehouse live verified. Goal active tới đầy đủ modules và gates có evidence.
