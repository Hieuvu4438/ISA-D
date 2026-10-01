# Kiến trúc ba tầng và common query

Nguồn: PDF trang 2–9, 17–18, 22–23. Native component diagram: `CMP_Three_Layer_Architecture`; native voice sequence: `SEQ_Voice_Product_Search`. Các sơ đồ export nằm trong `artifacts/diagrams/`.

## Trách nhiệm và dependency

| Tầng | Thành phần | Trách nhiệm |
|---|---|---|
| Presentation | SearchUI, VoiceInput, ImageUpload, SearchResultView | CLI arguments/input adapter, gọi Application services, hiển thị/serialize result và lỗi |
| Application / Intelligence | QueryService, SpeechService, ImageService, SearchService, RankingService, OrderService | Chuẩn hóa/validate, modality conversion, retrieval/filter, scoring/ranking, order scope |
| Data | ProductRepository, OrderRepository, VectorIndex, ProductDatabase, OrderDatabase, ImageStorage | Load/validate JSON, product/order lookup, descriptor index, images |

Luồng phụ thuộc là Presentation → Application → Data. `presentation/` không load JSON/index, không gọi repository, không tính cosine. `application/` không phụ thuộc UI. `data/` không phụ thuộc tầng trên. `main.py` là composition root tạo repository/index/service và inject vào UI; việc import ba tầng ở composition root không vi phạm nguyên tắc UI → Application → Data.

ProductDatabase và OrderDatabase là **JSON storage**, không phải RDBMS. VectorIndex là **in-memory index có file JSON metadata/vectors**, không phải FAISS/vector database. ImageStorage là folder ảnh trên filesystem. CLI là Presentation Layer hợp lệ cho prototype.

Dependencies quan trọng: SearchUI → QueryService/SpeechService/ImageService/SearchService/OrderService; SearchService → ProductRepository/VectorIndex/RankingService; OrderService → OrderRepository; repositories → JSON storage; ImageService → ImageStorage. Input adapters và ResultView cùng tầng Presentation. Native package ownership phải đúng, không chỉ đặt shapes nhìn nằm trong khung.

## Pipeline

1. Presentation nhận input; boundary validate mode và arguments.
2. SpeechService trả transcript đã validate (mô phỏng). ImageService mở ảnh/encode pixels. Text được normalize bởi QueryService.
3. QueryService xây common query: type, raw_input, normalized query, unique tokens, embedding, filters, top_k, weights, encoder metadata.
4. SearchService `_retrieve` đọc products/index, tính match/similarity, lọc và thống kê candidates. Public `retrieve_candidates` là wrapper trả danh sách candidates cho kiểm thử/tích hợp; `search` dùng `_retrieve` để giữ processing statistics. Chưa sort hoặc cắt top-k cuối.
5. RankingService tính final score, sort decreasing, tie-break product_id increasing, cắt top-k.
6. Result envelope đưa query/processing/results về ResultView. UI không tự tính lại rank.

## Data contract

Product có `product_id`, name, brand, category, color, price USD, stock, description và image path. ID duy nhất; price ≥0; stock integer ≥0; ảnh tồn tại. Index liên kết product_id và encoder/version/dimension/hash ảnh, tránh dùng vectors cũ sau khi đổi ảnh.

Common query dùng một schema thống nhất dù modality khác nhau. Text/voice có query/tokens; image có embedding; multimodal có cả hai. Voice giữ `type=voice` để truy vết nguồn nhưng sử dụng text retrieval. Top-k là integer dương; weights và số trong vector phải hữu hạn; dimension phải phù hợp index; filter giá có exclusive/inclusive semantics.

Mỗi result chứa rank, product_id, name/category/color/price/stock/image_path, raw_text_score/text_score/image_score/business_score/final_score và matched_terms. Objects product gốc không bị mutation khi thêm score.

## Voice sequence

Participants: Customer, SearchUI, SpeechService, QueryService, SearchService, ProductRepository, RankingService. Customer gửi transcriptInput; SearchUI gọi transcribe rồi voice_query; SearchService nhận query, retrieve_candidates qua ProductRepository, gọi RankingService.rank và trả search_result; UI display products/ranking scores. Return messages nét đứt; calls đồng bộ và activation hợp lý. Note bắt buộc: **Simulated STT: input is already transcribed text**.

Luồng conceptual audio → STT trong PDF không đồng nghĩa prototype đã nhận audio. Thiết kế adapter SpeechService cho phép thay implementation ASR sau này mà không đổi retrieval/ranking.

## Search và ranking

Text matching là baseline có normalize/stopwords/aliases; raw count dựa trên query tokens duy nhất và token boundaries, không substring. `text_score = matched_unique_terms / query_term_count`. Category rõ ràng có thể được extract thành filter; chính sách phải khớp tests/query processing.

Descriptor ảnh nhẹ 88 chiều gồm RGB histogram 8 bins/channel (24) và grayscale thumbnail 8×8 (64), dùng cùng pipeline cho product/query. Histogram đọc ảnh RGB resize 128×128; thumbnail đọc grayscale 8×8. Hai blocks L2-normalize riêng, concatenate với weights bằng nhau, rồi L2-normalize descriptor cuối. ImageService xử lý EXIF orientation và từ chối ảnh vượt 20 triệu pixels. Đây là handcrafted descriptor từ pixels, không phải CLIP/CNN learned embeddings; nhạy với màu/bố cục, không hiểu ngữ nghĩa.

`cosine(a,b)=dot(a,b)/(norm(a)*norm(b))`; zero norm được xử lý về 0; vector invalid bị từ chối. Text/image scores được chuẩn hóa để score fusion có ý nghĩa. Text/voice weights (1,0), image (0,1), multimodal mặc định (0.5,0.5). Candidates fusion là union trước ranking, không lấy intersection hoặc top-1 riêng từng modality. Không cộng token vector và pixel vector khác không gian. `business_score=0` trong bản hiện tại, không có stock-aware boost; stock chỉ là metadata.

Order lookup đi qua OrderService và không đưa order vào product ranking. Customer_id là context fixture được truyền bằng CLI, chưa phải identity đã xác thực.

## Thay thế và mở rộng

Có thể thay SpeechService bằng real ASR, ImageService bằng learned encoder và VectorIndex bằng vector database qua các interfaces; phải rebuild embeddings và đánh giá lại, không chỉ đổi nhãn. Semantic text search và web UI chưa cần để đáp ứng baseline. Production auth, multi-tenant storage, encryption, logging policy và load testing cần thiết kế riêng trước triển khai thật.
