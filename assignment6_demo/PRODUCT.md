# Cortis

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React, TypeScript, Vite theo đặc tả hiện có; backend FastAPI/Python CPU. Người dùng chọn dựng trực tiếp bằng code.

## Users

Khách hàng và người trình diễn demo tiếng Việt: tìm giày/túi theo mô tả, giọng nói hoặc ảnh; kiểm tra sản phẩm và đơn hàng của khách demo C001.

## Product Purpose

Biến ý định bằng tiếng Việt và hình ảnh thành danh sách sản phẩm để khám phá. Thành công là thực hiện các workflow qua giao diện với API/model thật, kết quả có thể giải thích, lỗi có recovery rõ.

## Positioning

Một cửa hàng demo kết hợp text, ảnh và text + ảnh trong cùng không gian CLIP 512D; không biến cosine thành xác suất hoặc transcript nhập tay thành kết quả Azure thật.

## Operating Context

Demo local, desktop và mobile browser. Các route tìm kiếm, sản phẩm, đơn hàng, nguồn ảnh. Chưa thanh toán, giỏ hàng, đăng nhập hay admin.

## Capabilities and Constraints

Theo docs/04–08: filter giá/category/brand/còn hàng; nearest/relevant; queue/timeout; các state loading/empty/error, request cancellation và chống response cũ; WAV PCM16 mono16k, tối đa15s. Azure key backend-only; cloud STT chưa được xác minh nếu chưa có cấu hình và live evidence.

## Brand Commitments

Người dùng xác nhận tên Cortis, giao diện tiếng Việt, học hỏi thiết kế ecommerce đẹp. Mọi ảnh sản phẩm phải là ảnh chụp thật trên mạng, không ảnh generated hoặc synthetic.

## Evidence on Hand

12 sản phẩm, 3 đơn seed, 12 ảnh thật cùng credits/hash; API đang chạy với CLIP CPU thật; artifacts/backend lưu tests/model/index/HTTP evidence. Giá/tồn kho là dữ liệu minh họa, không là giá bán thực tế của các thương hiệu.

## Product Principles

- Hành động khách hàng dẫn đường, chi tiết model chỉ trong panel giải thích.
- Kết quả phải đến từ API thật, giữ nguyên submitted context khi draft thay đổi.
- Mất một dependency không làm mất các luồng vẫn sẵn sàng.
- Không dựng claims thương mại, nút mua/checkout hoặc quyền truy cập không có backend.

## Accessibility & Inclusion

Tiếng Việt có dấu; keyboard, screen reader, reduced motion; responsive360/768/1440; label thật, contrast và focus rõ; upload/manual transcript là lối thay thế khi mic/cloud unavailable.
