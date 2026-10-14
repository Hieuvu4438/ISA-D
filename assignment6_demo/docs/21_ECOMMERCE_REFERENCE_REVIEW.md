# Đối chiếu module ecommerce với website hiện có

Nguồn tham khảo được đọc ngày 2026-10-15. Đây là review tài liệu công khai và nghiên cứu UX; không phải bằng chứng đã thao tác mua hàng trên các website nguồn. Các quyết định Cortis dưới đây là đề xuất kiểm thử/triển khai, không sao chép chính sách bán hàng của thương hiệu khác.

## Quan sát có nguồn

- [Baymard — filter UI](https://baymard.com/blog/ecommerce-filter-ui): nên cho người dùng thấy các điều kiện đang áp dụng và bỏ từng điều kiện ngay trên danh sách.
- [Baymard — search query types](https://baymard.com/research-articles/ecommerce-search-query-types): tìm theo thuộc tính và cách gọi thông thường cần được xử lý cùng tìm tên sản phẩm; các điều kiện được hiểu cần hiển thị cho người dùng.
- [UNIQLO — availability](https://faq-us.uniqlo.com/articles/en_US/FAQ/How-can-I-find-out-when-an-item-will-be-back-in-stock-us): kiểm tra khả dụng trên trang sản phẩm sau khi chọn màu và size.
- [Nike — cancel/change order](https://www.nike.com/help/a/change-cancel-order): việc hủy đơn có điều kiện và được truy cập từ thông tin đơn. Trang mở trực tiếp trả ít nội dung; thông tin nút hủy được đối chiếu qua kết quả chỉ mục chính trang Nike. Không xác nhận thời hạn cụ thể hay đã thử hủy đơn thật.

## Áp dụng cho Cortis và test cần có

| Module | Hành vi cần bảo đảm | Tình huống phải kiểm tra | Trạng thái bằng chứng |
|---|---|---|---|
| Tìm kiếm | Tên, mã, tiếng Việt có/không dấu, từ đồng nghĩa; kết hợp điều kiện | Sai chính tả, từ khóa rỗng/dài, không có kết quả, lỗi encoder, request cũ trả muộn | Hybrid đã có; xem evidence E2; chưa đạt mọi quality gate |
| Bộ lọc/sắp xếp | Thấy điều kiện đang chọn, xóa từng điều kiện, URL có thể mở lại | Điều kiện mâu thuẫn, giá biên, đổi lọc khi ở trang cuối, Back/Forward, kết quả rỗng | Browse đã có; cần kiểm tra đối chiếu UX đầy đủ |
| Danh mục | Nhãn nhất quán giữa menu, metadata, facet và kết quả | Sản phẩm nhiều thuộc tính, danh mục rỗng, ảnh/metadata sai, SKU không còn tồn tại | Dữ liệu còn pending theo docs17 |
| Chi tiết/biến thể | Giá, ảnh và tồn kho đúng lựa chọn màu/size | Size hết hàng, chưa chọn size, biến thể bị gỡ, tồn kho thay đổi sau mở trang | Tồn kho cấp sản phẩm có; biến thể còn pending |
| Giỏ hàng/yêu thích | Lưu theo tài khoản, không trộn dữ liệu khách khác | Hai tab cập nhật, hết hàng sau thêm, đăng xuất, lỗi mạng và thử lại | E3 đã có; biến thể chưa có |
| Checkout | Báo giá có hạn, đặt đơn một lần, trừ kho nguyên tử | Gửi lặp, stock race, giá/giỏ thay đổi, báo giá hết hạn, thiếu địa chỉ | E4 có test transaction; COD demo |
| Đơn hàng | Chỉ xem đơn thuộc mình; thao tác theo trạng thái | Hủy lặp, hủy sau giao, hai tác nhân cập nhật, hoàn kho một lần | E4/E5 có test; đổi trả/refund pending |
| Tài khoản/quyền | API kiểm quyền; đổi quyền thu hồi phiên | Truy cập URL admin trực tiếp, quyền bị đổi lúc chờ transaction, tự hạ quyền | E1/E5 có test; khóa/xóa tài khoản pending |
| Admin/dữ liệu | Version chống ghi đè, audit cùng transaction | Dữ liệu stale, audit lỗi, retry thao tác, cập nhật metadata làm index cũ | Vận hành E5 có; metadata/asset CRUD và index publication pending |
| Multimodal/voice | Trạng thái tải/lỗi rõ, có đường nhập văn bản để tiếp tục | Ảnh sai định dạng, mic bị từ chối, provider timeout, tiếng Việt không dấu | Gate encoder/local/Groq/Azure phải ghi riêng; không suy ra từ ecommerce tests |

Thông báo restock, kho cửa hàng, vận chuyển và thanh toán thật không được tự coi là đã tích hợp từ việc tham khảo. Muốn thêm phải cập nhật hợp đồng, dữ liệu, UI, test và evidence tương ứng. Theo dõi acceptance trong docs10 và milestone docs09; không đánh dấu complete chỉ vì các test hiện có xanh.
