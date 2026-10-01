# Use Case Model

Nguồn: PDF trang 7–8, Task 2 trang 18. System boundary: **Multimodal E-Commerce Search System**. Actor: **Customer**. Native diagram: `UC_Multimodal_Ecommerce_Search` trong `models/Assignment_06_Multimodal_Search.vpp`.

## Quan hệ UML

Customer liên kết với Search Product, Search Order, View Product và View Order. Search by Keyword, Search by Voice, Search by Image **chuyên biệt hóa** Search Product; mũi tên generalization tam giác rỗng hướng về Search Product. Đây là các lựa chọn input, không có include bắt buộc chạy cả ba trong một lần search. View Product và View Order là mục tiêu xem chi tiết, không tự động bị include trong mọi search. Fusion thuộc mở rộng Search Product, không làm thiếu bảy use case bắt buộc.

## UC-01 — Search Product

| Thuộc tính | Mô tả |
|---|---|
| Actor, goal | Customer tìm sản phẩm phù hợp và xem danh sách xếp hạng |
| Preconditions | Repository/index đã load hợp lệ; ít nhất một modality được cung cấp |
| Trigger | Customer chọn text, voice, image hoặc fusion |
| Main flow | UI thu input → service tạo query chuẩn → SearchService retrieval/filter → RankingService rank → ResultView hiển thị products/scores |
| Alternate/error | Input sai bị từ chối rõ; không có candidate trả danh sách rỗng; lỗi index cần rebuild |
| Postconditions | Có result envelope, score components, processing metadata; dataset không bị sửa |

## UC-02 — Search by Keyword

| Thuộc tính | Mô tả |
|---|---|
| Actor, goal | Customer tìm sản phẩm bằng chuỗi từ khóa |
| Preconditions | ProductRepository hợp lệ; text không rỗng hoặc có filter được hỗ trợ |
| Trigger | `--mode text --query "black shoes"` |
| Main flow | QueryService normalize/tokenize/alias/extract filters → common query → candidates có token match → filter → rank theo text_score → display |
| Alternate/error | Uppercase/khoảng trắng được normalize; unknown keyword trả empty; `under 100` giữ semantics `<100`; invalid top-k trả error |
| Postconditions | Text query + ranked products + raw_text_score/text_score/final_score |

## UC-03 — Search by Voice

| Thuộc tính | Mô tả |
|---|---|
| Actor, goal | Customer tìm sản phẩm qua kết quả speech-to-text mô phỏng |
| Preconditions | Input là transcript string; chưa tích hợp microphone/ASR |
| Trigger | `--mode voice --query "find black running shoes"` |
| Main flow | SearchUI → SpeechService.transcribe → QueryService.voice_query → SearchService.search → ProductRepository → RankingService → output |
| Alternate/error | Transcript trống/sai type bị từ chối; transcript hợp lệ không match trả empty; cùng text/config cho kết quả tương đương text |
| Postconditions | Query giữ `type=voice`, output ghi Simulated STT; không tuyên bố nhận diện audio thật |

## UC-04 — Search by Image

| Thuộc tính | Mô tả |
|---|---|
| Actor, goal | Customer tìm sản phẩm có ảnh gần giống |
| Preconditions | File ảnh đọc được; index và query cùng encoder/version/dimension |
| Trigger | `--mode image --image data/queries/black_shoe_query.png` |
| Main flow | ImageUpload thu path → ImageService encode pixels → QueryService.image_query → VectorIndex cosine → metadata/filter → RankingService → display |
| Alternate/error | Missing/corrupt image hoặc dimension mismatch bị từ chối; zero norm cosine xử lý có kiểm soát; similarity thấp vẫn có thể trả top-k, không có semantic confidence threshold |
| Postconditions | Results có image_score/final_score; processing ghi descriptor 88 chiều |

## UC-05 — Search Order

| Thuộc tính | Mô tả |
|---|---|
| Actor, goal | Customer tìm đơn hàng của mình theo order id |
| Preconditions | Orders JSON hợp lệ; customer context mô phỏng được cung cấp |
| Trigger | `--mode order --order-id O001 --customer-id C001` |
| Main flow | SearchUI → OrderService → OrderRepository.find_order(order_id, customer_id) → scoped order → UI |
| Alternate/error | Order không tồn tại hoặc thuộc customer khác trả not-found; không tiết lộ dữ liệu của customer khác |
| Postconditions | Order scoped được trả hoặc empty/not-found; không chạy product ranking |

## UC-06 — View Product

| Thuộc tính | Mô tả |
|---|---|
| Actor, goal | Customer xem chi tiết một sản phẩm |
| Preconditions | Product id hợp lệ; repository đã load |
| Trigger | Customer chọn product id, hoặc lệnh CLI xem product detail |
| Main flow | SearchUI gọi Application service lấy product theo id → ResultView hiển thị id/name/category/color/price/stock/description/image |
| Alternate/error | Không tồn tại trả not-found; UI không tự đọc products.json |
| Postconditions | Chi tiết product được hiển thị; object repository không bị sửa |

## UC-07 — View Order

| Thuộc tính | Mô tả |
|---|---|
| Actor, goal | Customer xem status/date/total của order thuộc mình |
| Preconditions | Có order id và customer context |
| Trigger | Customer xem order tìm được |
| Main flow | UI → OrderService scoped lookup → OrderRepository → UI display status/date/total và order items nếu có |
| Alternate/error | ID sai hoặc khác owner trả cùng trạng thái not-found; context mô phỏng không thay authentication production |
| Postconditions | Thông tin order thuộc scope được hiển thị, không thay đổi order |

## Mở rộng có trong prototype

Fusion dùng text + image trong một common query và cộng scores đã chuẩn hóa. Category/price filters là bước xử lý nội bộ Search Product. Stock signal nếu bật thuộc ranking và phải xuất hiện trong processing. Các extension không cần thêm actor ngoài.
