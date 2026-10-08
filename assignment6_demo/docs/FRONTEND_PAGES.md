# Các trang sản phẩm, đơn hàng và nguồn ảnh

Các trang dưới đây dùng dữ liệu từ HTTP API của backend. Không cần model tìm kiếm hoặc Azure Speech sẵn sàng để xem sản phẩm, nguồn ảnh và đơn hàng.

| Route | Trang | API | Thao tác chính |
| --- | --- | --- | --- |
| `/products/:productId` | `ProductPage` | `GET /api/v1/products/{product_id}` | Xem ảnh, mô tả, giá, tồn kho và tác giả/giấy phép; trở lại tìm sản phẩm |
| `/orders` | `OrdersPage` | `GET /api/v1/orders?order_id=…` | Nhập mã và bấm **Tra cứu đơn hàng**; mở chi tiết từ summary |
| `/orders/:orderId` | `OrderPage` | `GET /api/v1/orders/{order_id}` | Xem trạng thái, ngày đặt, từng sản phẩm và tổng tiền; mở sản phẩm từ dòng đơn hàng |
| `/credits` | `CreditsPage` | `GET /api/v1/credits` | Xem ảnh thật, nguồn, tác giả, giấy phép và các điều chỉnh ảnh |
| Đường dẫn khác | `NotFoundPage` | Không gọi API | Trở lại tìm sản phẩm hoặc tra cứu đơn hàng |

Các trang chi tiết tự tải dữ liệu khi mở trực tiếp. Request bị hủy khi rời trang hoặc đổi ID; response cũ không ghi đè dữ liệu của route mới. Loading và lỗi có thông báo tiếng Việt, lỗi có thao tác thử lại. Ảnh dùng media của backend và placeholder trung tính khi tải lỗi.

Form đơn hàng không gửi request khi chỉ nhập mã. Khi submit, mã được trim, đổi thành chữ hoa và kiểm tra dạng `O` + 3 chữ số trước khi gửi. Đơn không tồn tại và đơn ngoài phạm vi đều hiển thị cùng thông báo “Không tìm thấy đơn hàng.”; frontend không gửi customer context.

Giá tiền dùng VND theo locale `vi-VN`, ngày đặt hiển thị theo múi giờ Việt Nam. Tên và giá trong đơn hàng là snapshot từ backend. Các trang không bổ sung mua hàng, checkout hoặc cập nhật đơn hàng.

## Kiểm chứng

Chạy từ `assignment6_demo/frontend`:

```powershell
npm test -- src/pages/pages.test.tsx
```

Lần kiểm tra hiện tại: **4 tests đạt**. Các tests xác minh tải chi tiết trực tiếp và chống response cũ khi đổi route; tra đơn chỉ sau submit với chuẩn hóa/validation mã; lỗi đơn hàng không tiết lộ chủ sở hữu; credit và URL media lấy từ API. Fixtures trong unit tests chỉ phục vụ kiểm thử, không được dùng làm dữ liệu của ứng dụng.

Kiểm tra trình duyệt cho toàn website do bộ Playwright ở `frontend/e2e` thực hiện. Tài liệu này không dùng unit tests để kết luận Azure Speech đã được kiểm chứng trực tiếp.
