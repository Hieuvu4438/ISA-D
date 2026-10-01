# Assignment 06 — Multimodal E-Commerce Search

Prototype Python offline cho tìm kiếm sản phẩm bằng text, voice transcript mô phỏng, ảnh và fusion text + image. Sản phẩm bàn giao gồm code, dataset, UML native Visual Paradigm, demo, đánh giá và báo cáo PDF. Voice không nhận microphone/audio; ảnh được đọc pixel bằng handcrafted descriptor 88 chiều, không phải mô hình AI học sâu.

## Cài đặt và chạy

Đã kiểm tra Python **3.12.8** trên Windows. Các dependency runtime được pin trong `requirements.txt`: NumPy 2.5.3 và Pillow 12.3.0. Dev/report tools nằm trong `requirements-dev.txt`; desktop automation không cần thiết để chạy prototype.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/prepare_dataset.py
.\.venv\Scripts\python.exe scripts/build_index.py
.\.venv\Scripts\python.exe main.py
```

Dataset và index đã được đóng gói nên người chấm có thể chạy `main.py` ngay sau cài dependency. `prepare_dataset.py` bảo toàn file có sẵn; dùng `--force` chỉ khi chủ động tái tạo dữ liệu mẫu. `build_index.py` tái tạo khi encoder/dataset/ảnh thay đổi. Chạy CLI từ thư mục khác vẫn được; các image path tương đối CLI được giải theo project root.

```powershell
.\.venv\Scripts\python.exe main.py --help
.\.venv\Scripts\python.exe main.py --demo --output artifacts/demo/demo_results.json
.\.venv\Scripts\python.exe main.py --mode text --query "black shoes" --top-k 5
.\.venv\Scripts\python.exe main.py --mode voice --query "find black running shoes"
.\.venv\Scripts\python.exe main.py --mode image --image data/queries/black_shoe_query.png
.\.venv\Scripts\python.exe main.py --mode multimodal --query "black shoes" --image data/queries/black_shoe_query.png --text-weight 0.5
.\.venv\Scripts\python.exe main.py --mode text --query "find Nike shoes under 100 dollars"
.\.venv\Scripts\python.exe main.py --mode text --query "shoes at most 100 dollars" --top-k 12
.\.venv\Scripts\python.exe main.py --mode text --query "under 100" --category shoes
.\.venv\Scripts\python.exe main.py --mode order --order-id O001 --customer-id C001
.\.venv\Scripts\python.exe main.py --mode product --product-id 1
.\.venv\Scripts\python.exe main.py --mode text --query "black shoes" --json --output artifacts/demo/text_result.json
```

Không có `--mode` sẽ chạy demo đủ text/voice/image/fusion/order. `--json` xuất JSON thuần ra stdout; `--output` lưu JSON UTF-8 trong khi stdout mặc định vẫn dễ đọc. Input sai trả exit code 2, có message và không traceback; query hợp lệ không có kết quả trả code 0. Order lookup bắt buộc customer context theo mẫu `C001`, không trả order của người khác. Đây là context mô phỏng, không có authentication production.

## Thiết kế và phương pháp

`main.py` là composition root inject dependency. `presentation/` nhận input và hiển thị; `application/` chuẩn hóa query, transcribe giả lập, encode pixel, retrieval và ranking; `data/` validate JSON, load metadata và cosine index. Presentation không import data. Query object thống nhất có `type`, `raw_input`, `query`, `tokens`, `embedding`, `filters`, `top_k`, `weights`, `customer_id`, `encoder`.

Text: lowercase + whole-word matching OR trên name/brand/category/color/description; unique tokens; stopwords `find/show/me/a/an/the/please/for/dollar/dollars/usd`; aliases `shoe→shoes`, `bags→bag`, `backpacks→backpack`, `shirts→shirt`. Category được suy ra từ `shoes`, `bag/backpack`, `shirt/jacket/clothing` và trở thành hard filter. `under/below X` dùng `<X`; `at most X` dùng `≤X`. Filter-only query được xét toàn catalogue, score text=0 và tie-break id tăng dần. Price USD, không có currency conversion.

Ảnh: EXIF orientation → RGB → histogram 8 bins mỗi channel (24 chiều), thumbnail grayscale 8×8 (64 chiều). Hai block được L2-normalize riêng, ghép với trọng số bằng nhau rồi L2-normalize cuối. Product/query dùng cùng encoder `rgbhist-gray-thumbnail`, version `1.0`, dimension `88`. Cosine âm clamp về 0 để fusion; zero vector trả score 0; NaN/Infinity/dimension sai bị từ chối. Source fingerprint SHA-256 chứa cả catalogue và bytes ảnh; index cũ bị từ chối với yêu cầu rebuild. 12 ảnh là illustration gốc sinh bằng Pillow, không phải ảnh chụp; sample queries biến đổi brightness/resize, khác pixel nguồn.

Retrieval tạo candidates chưa sort/cắt top-k; fusion dùng union tất cả image candidates với text candidates, sau đó áp dụng filter chung. `RankingService` tính:

```text
raw_text_score = số token query duy nhất khớp
text_score = raw_text_score / số token query (hoặc 0 nếu filter-only)
image_score = max(0, cosine(query_embedding, product_embedding))
final_score = w_text × text_score + w_image × image_score
```

Text/voice weights=(1,0), image=(0,1), fusion mặc định=(0.5,0.5). `--text-weight` cho fusion trong [0,1]. Sort score giảm dần rồi product_id tăng dần, lấy top-k cuối tại RankingService. Stock được hiển thị, business_score=0; không có boost ẩn.

## Kiểm thử và đánh giá

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q --cov=application --cov=data --cov-report=term-missing --cov-report=json:artifacts/tests/coverage.json --cov-report=html:artifacts/tests/coverage --junitxml=artifacts/tests/junit.xml
.\.venv\Scripts\python.exe -m ruff check main.py application data presentation scripts/prepare_dataset.py scripts/build_index.py scripts/run_evaluation.py tests
.\.venv\Scripts\python.exe -m pyright
.\.venv\Scripts\python.exe -m compileall -q main.py presentation application data scripts
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/run_evaluation.py --queries evaluation/queries.json --output artifacts/evaluation
```

Ground truth được viết trước implementation/evaluation tại `evaluation/queries.json`. Primary retrieval: 12 cases (4 text, 4 voice, 4 image), thành công khi top-1 thuộc relevant_ids. Extension 2 cases, challenge 2 cases và robustness 5 cases có denominator riêng. Kết quả quan sát: primary **12/12 (100%)**, extension **2/2**, challenge **0/2**, robustness **5/5**. Tập nhỏ có ảnh synthetic, kết quả này không khẳng định generalization trên ảnh thật. Metrics/timing/scores đầy đủ và machine metadata ở `artifacts/evaluation/metrics.json`, rows ở `results.json`/`results.csv`. Thời gian query loại trừ startup; không phải benchmark production.

Failure quan sát: `sneakers` không trả kết quả vì không có alias/semantic embeddings; `shoes not black` trả black shoes vì negation chưa được hiểu. Expected labels giữ nguyên, không chuyển failure sang success. Pillow histogram/thumbnail có thể nhầm ảnh cùng màu/hình; voice transcript chỉ chứng minh kiến trúc, không đo độ chính xác STT. Không có vector database, semantic text model, real STT, authentication hoặc checkout. Ảnh >20 megapixels bị từ chối; top-k giới hạn 1–100, text 1–2000 ký tự.

## Cấu trúc và tài liệu

| Đường dẫn | Nội dung |
|---|---|
| `main.py`, `presentation/`, `application/`, `data/*.py` | Prototype ba tầng và CLI |
| `data/products.json`, `orders.json`, `embeddings.json` | 12 products, scoped orders, pixel vector index |
| `data/images/`, `data/queries/` | Original illustrations, query samples và fixture ảnh hỏng intentional |
| `models/Assignment_06_Multimodal_Search.vpp` | Project Visual Paradigm native |
| `docs/` | Requirements, use cases, architecture, traceability, discussion, report source và guide |
| `docs/testing/prototype.tdd.md` | RED/GREEN và test evidence |
| `tests/`, `evaluation/queries.json` | Automated acceptance/boundary tests và frozen ground truth |
| `scripts/` | Dataset/index/evaluation/report/validation/package helpers |
| `artifacts/diagrams/`, `screenshots/` | Export UML và screenshot thật |
| `artifacts/demo/`, `evaluation/`, `tests/` | Output chương trình, metric và check logs |
| `artifacts/report/Assignment_06_Report.pdf` | Báo cáo PDF |
| `submission/` | ZIP bàn giao và manifest |

Xem `docs/requirements.md` cho nguồn đề, `docs/architecture.md` cho component contracts, `docs/traceability.md` cho mapping yêu cầu–code–test–diagram, `docs/decisions_and_limitations.md` cho phạm vi. Đề gốc nằm trong `storage/`, không bị sửa. Việc chuẩn bị local không đồng nghĩa đã nộp LMS.

Mở native UML và tái tạo bằng VP API: xem `docs/VP_AUTOMATION.md`. Gate bàn giao/hash và clean extraction: xem `docs/FINAL_VERIFICATION.md`.

```powershell
.\.venv\Scripts\python.exe scripts/build_report.py --input docs/report.md --output artifacts/report/Assignment_06_Report.pdf
.\.venv\Scripts\python.exe scripts/validate_submission.py
.\.venv\Scripts\python.exe scripts/package_submission.py
```

Report builder cần artifacts/screenshot thật có sẵn; ZIP bàn giao chứa các evidence này. Không rebuild report trước khi hoàn tất dataset/demo/evaluation/test/screenshot stages. Report cover chưa có họ tên/MSSV/lớp; sửa đúng thông tin trong `docs/report.md` rồi build lại PDF và package nếu cần cá nhân hóa.
