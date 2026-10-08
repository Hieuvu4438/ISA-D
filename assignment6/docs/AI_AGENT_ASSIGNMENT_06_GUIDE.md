# Hướng dẫn AI Agent thực hiện Assignment 06 từ đầu đến khi bàn giao

**Bài tập:** Multimodal Search System for E-Commerce — Information System Analysis and Design.  
**Nguồn chuẩn:** `D:\PROJECTS\ISA-D\assignment6\storage\inf_sys_analysis_design_assignment_06_design_code.pdf` — 23 trang.  
**Workspace:** `D:\PROJECTS\ISA-D\assignment6`.  
**Ngày lập hướng dẫn:** 01/10/2026. **Múi giờ:** Asia/Saigon, UTC+7.  
**Ngôn ngữ:** giải thích và báo cáo bằng tiếng Việt; tên lớp, phương thức, use case và UML dùng tiếng Anh nhất quán.

> Đây là tài liệu giao nhiệm vụ cho Agent thực thi ở lượt tiếp theo. Việc tạo tài liệu này chưa đồng nghĩa với việc đã tạo code, sơ đồ, report hoặc sửa shortcut. Khi người dùng yêu cầu thực hiện theo guide, hãy thực hiện công việc và tạo các sản phẩm thật, kiểm tra được.

Điểm tra cứu nhanh: **phần 1–3** cho nguồn, quyền và task; **4–7** cho kế hoạch, cấu trúc và contract; **8–9** cho UML/Visual Paradigm; **10–12** cho Python, test và demo; **13–14** cho report/bài nộp; **15–17** cho recovery, nghiệm thu và bàn giao.

## 0. Lệnh giao việc có thể dùng ngay

Người dùng có thể giao cho Agent:

```text
Đọc docs/AI_AGENT_ASSIGNMENT_06_GUIDE.md và PDF nguồn. Thực hiện toàn bộ
Assignment 06 theo hướng dẫn, đến khi có Python prototype chạy được,
project Visual Paradigm .vpp với đủ 3 sơ đồ UML native, dataset, sample images,
demo thực tế, đánh giá, README, báo cáo LaTeX English đầy đủ không giới hạn trang và gói bàn giao.

Tôi cho phép bạn tự chủ đọc, tạo, sửa file; viết và chạy code; cài dependency
phục vụ bài tập; chụp/đọc màn hình; điều khiển chuột/bàn phím; trực tiếp
thao tác và chỉnh sửa project trong Visual Paradigm đã mở.
Tôi cũng cho phép đọc, sao lưu và sửa shortcut:
C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Visual Paradigm CE\Visual Paradigm 18.0.lnk
nếu việc sửa cần thiết cho thực hiện bài. Không cần hỏi lại cho các thao tác
local thuộc phạm vi này. Lưu checkpoint và bằng chứng sau mỗi mốc.
```

Agent phải đọc các phần tiếp theo trước khi triển khai. Các lệnh CLI, tên file và API được mô tả bên dưới là **hợp đồng cần triển khai**, không phải khẳng định chúng đã tồn tại.

## 1. Nguồn chuẩn, môi trường và cách xử lý điểm chưa thống nhất

### 1.1. Thứ tự ưu tiên

1. Chỉ dẫn hiện tại của người dùng và các giới hạn công cụ thực tế.
2. PDF nguồn, đặc biệt mục 20–26 về task, đánh giá, báo cáo và bài nộp.
3. Guide này để cụ thể hóa cách triển khai.
4. Ví dụ code trong đề và tài liệu công cụ để tham khảo.

Đọc toàn bộ PDF, gồm bảng và hình. Nếu trích xuất text thiếu bố cục, render trang thành ảnh và đọc ảnh. Ghi số trang nguồn vào `docs/requirements.md`; số trang PDF và số in trên trang trong tài liệu hiện trùng nhau.

### 1.2. Các điểm đã xác định trong đề

| Điểm trong PDF | Cách triển khai |
|---|---|
| Bìa ghi Assignment 06; một số đoạn và thư mục ví dụ ghi Assignment 05 | Dùng `Assignment 06` và workspace `assignment6`; ghi nhận đây là lỗi biên tập của ví dụ |
| Mục 16, trang 15 nói demo ít nhất hai chế độ; Task 6, trang 19 yêu cầu text, voice, image | Demo đủ **ba truy vấn thuộc ba chế độ** và hiển thị processing cùng score |
| Các mục mở rộng nêu order search là extension, nhưng Use Case Diagram bắt buộc có Search Order/View Order | Bắt buộc đưa hai use case vào UML; triển khai order lookup đơn giản trong bản hoàn chỉnh để mô hình và code phù hợp |
| Mục 17 nêu multimodal fusion là extension; rubric có 10 điểm Multimodal search | Hoàn thiện cả ba chế độ trước; sau đó thêm fusion text + image để hỗ trợ tốt phần rubric, không hứa trước số điểm |
| Sơ đồ thư mục ví dụ có hai nhánh `data/` | Dùng một package `data/` chứa repository, JSON, image storage và vector index |
| Cho phép artificial feature vectors và simulated speech-to-text | Có thể dùng baseline này; ghi rõ mô phỏng, không tuyên bố đã chạy mô hình AI hoặc nhận dạng âm thanh thật |

### 1.3. Thời hạn

- V01: PDF trang 1 ghi `TODAY`, trước 16:00 cho class 03 hoặc trước 19:00 cho class 04.
- PDF có metadata tạo ngày 01/10/2026; guide hiểu `TODAY` là **01/10/2026**, không đổi theo ngày Agent chạy lại.
- V02: trước 23:00 thứ Tư 07/10; theo năm của tài liệu là **07/10/2026**, UTC+7.
- Chưa biết người dùng thuộc class nào. Nếu lập lịch V01, ưu tiên chuẩn bị trước 16:00; không tự khai class.
- Nếu thời hạn đã qua khi thực thi, tiếp tục hoàn thiện bài, báo đúng thời điểm và tình trạng; không giả lập đã nộp đúng hạn.
- Đề không mô tả nội dung riêng cho V01/V02. Các mốc tại phần 4 là kế hoạch triển khai của guide.

### 1.4. Môi trường đã kiểm tra khi lập guide

| Thành phần | Trạng thái quan sát |
|---|---|
| Workspace | Ban đầu chỉ có `storage/` với PDF đề bài |
| Git | Workspace thuộc repository cha `D:\PROJECTS\ISA-D`; tránh thao tác lên các assignment khác |
| Python | Python 3.12.8 tại `C:\Program Files\Python312\python.exe` |
| Đọc PDF | Có PyMuPDF (`fitz`), `pypdf` và `pdftotext.exe` |
| Desktop automation | Có `pywinauto`, `pyautogui`, Pillow trong interpreter đã kiểm tra |
| Visual Paradigm | Visual Paradigm CE 18.0 đã chạy |
| Cửa sổ VP | Tiêu đề quan sát: `baikiemtra01 - Visual Paradigm Community Edition[Vu Dinh Hieu] (not for commercial use)` |
| Window class | `SunAwtFrame`; cần kiểm tra khả năng truy cập control của ứng dụng Java |
| Shortcut | `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Visual Paradigm CE\Visual Paradigm 18.0.lnk` |
| Shortcut target | `C:\Program Files\Visual Paradigm CE 18.0\bin\Visual Paradigm.exe` |
| Shortcut working directory | `C:\Program Files\Visual Paradigm CE 18.0\bin` |
| VP Open API | Có `C:\Program Files\Visual Paradigm CE 18.0\lib\openapi.jar` |

Agent phải kiểm tra lại trạng thái tại lúc thực thi; không hardcode PID, window handle hoặc tọa độ từ lần kiểm tra trước. Không suy ra thông tin sinh viên từ tên tài khoản hoặc license Visual Paradigm.

## 2. Quyền tự chủ được người dùng cho phép

### 2.1. Phạm vi thao tác local

Người dùng cho phép Agent thực hiện mọi tác vụ local cần thiết để hoàn thiện bài trong workspace, cụ thể:

- Đọc PDF, tài liệu, source code, dataset, project và trạng thái ứng dụng liên quan.
- Tạo folder; viết, sửa, refactor code; tạo tài liệu; sinh dữ liệu và ảnh minh họa; xuất báo cáo và ZIP.
- Chạy PowerShell, Python và script; tạo virtual environment; cài dependency phục vụ bài tập.
- Chụp màn hình, đọc screenshot, inspect window/control; dùng chuột, bàn phím, clipboard và OCR nếu có.
- Trực tiếp điều khiển Visual Paradigm đang mở: tạo/sửa/xóa phần tử do Agent tạo, chỉnh quan hệ, bố cục, tên và thuộc tính.
- Tạo project mới hoặc Save As bản riêng; save, reopen, export diagram, thu thập screenshot thật.
- Viết helper automation hoặc plugin local cho Visual Paradigm nếu phù hợp.
- **Đọc, backup và sửa trực tiếp shortcut `.lnk` chính xác ở phần 1.4**, khi cần sửa target, arguments hoặc working directory để khởi chạy đúng ứng dụng.
- Sửa lỗi, chạy lại kiểm tra và cải thiện đầu ra đến khi đạt tiêu chí nghiệm thu.

Không hỏi lại người dùng để xác nhận từng lần click, screenshot, save, sửa code hoặc cài dependency local đã thuộc phạm vi được giao. Tiếp tục công việc độc lập khi một chi tiết chưa rõ nhưng không ngăn các task khác.

### 2.2. Cách áp dụng quyền đúng vào Visual Paradigm

`Visual Paradigm 18.0.lnk` là **Windows shortcut**, không phải file project hay nội dung sơ đồ. Để sửa bài, điều khiển ứng dụng mà shortcut trỏ tới và lưu mô hình trong `.vpp`. Chỉ sửa shortcut khi có nhu cầu thực tế; shortcut đang đúng không cần bị thay đổi để chứng minh Agent có quyền.

Quyền người dùng cho phép không tự tạo quyền administrator, không thay thế UAC hoặc chính sách sandbox của phiên Agent. Dùng các quyền và cơ chế sẵn có; nếu gặp Access Denied, ghi lại lỗi và tiếp tục bằng executable/phiên VP đang mở. Chỉ yêu cầu người dùng can thiệp nếu quyền hệ điều hành thực sự chặn phần việc cần thiết và không còn đường thay thế.

### 2.3. Bảo toàn công việc hiện có

- Với project `baikiemtra01` đang mở: kiểm tra đường dẫn và trạng thái save; giữ bản gốc, ưu tiên project riêng cho Assignment 06.
- Trước khi sửa file có sẵn, lưu backup vào `artifacts/backups/` với timestamp và ghi đường dẫn gốc.
- Không ghi đè PDF đề bài. Không xóa project của bài khác, source của người dùng hoặc dữ liệu ngoài phạm vi.
- Không tự sửa cấu hình Codex toàn cục, quyền filesystem hoặc thông tin đăng nhập để mở rộng quyền.
- Các hành động bên ngoài như nộp LMS, gửi email, publish, push hoặc dùng dịch vụ trả phí cần chỉ dẫn cụ thể của người dùng. Chuẩn bị đầy đủ artifact local trước; việc hoàn thành bài local không đồng nghĩa đã nộp lên LMS.

## 3. Phạm vi bài tập và ma trận yêu cầu

### 3.1. Sáu task bắt buộc

| ID | Task và nguồn PDF | Sản phẩm cần tạo | Tiêu chí nghiệm thu |
|---|---|---|---|
| T1 | Requirements Analysis, trang 17–18 | `docs/requirements.md`, phần phân tích trong report | Mô tả hệ thống, actors, ít nhất 5 FR, NFR, modalities, outputs |
| T2 | Use Case Diagram, trang 18; hướng dẫn trang 7–8 | UML native trong `.vpp`, ảnh export và screenshot VP | Actor Customer và đủ 7 use case được liệt kê bên dưới; UML đúng |
| T3 | Three-Layer Architecture, trang 18; trang 8–9 | Component Diagram chứa package ba tầng | Đủ ba tầng; dependencies Presentation → Application → Data; không UI → Data |
| T4 | Voice Sequence Diagram, trang 18; trang 9 | Sequence Diagram native trong `.vpp` | Đủ 7 participants bắt buộc, thông điệp và return đúng luồng |
| T5 | Python Implementation, trang 19; ví dụ trang 9–15 | Source Python, dependency manifest, dataset và sample images | Product repository, text, simulated voice, image similarity, ranking chạy được |
| T6 | Demonstration, trang 19 | Demo log/JSON, screenshot chạy chương trình, mô tả trong report | Ba truy vấn text/voice/image; mỗi truy vấn có input, processing, products, score |

Use case bắt buộc: **Search Product, Search by Keyword, Search by Voice, Search by Image, Search Order, View Product, View Order**. Với actor Customer, diagram có ít nhất tám phần tử chính này.

Yêu cầu đi kèm:

- Ít nhất **10 products**: trang 11. Guide đề xuất 12 products có ảnh và metadata đầy đủ.
- Đánh giá thực nghiệm: trang 20; tổng query, query thành công, success rate, ví dụ kết quả sai.
- Report khoảng **10–12 trang** với 11 nội dung khuyến nghị: trang 20–21.
- Screenshot diagram trong Visual Paradigm và screenshot Python chạy thật: trang 21.
- Bảy nhóm bài nộp: report PDF, project VP, source Python, dataset, sample images, README, demonstration results: trang 21.
- Retrieval và ranking phải tách trách nhiệm: trang 22, kể cả ví dụ code ngắn trong đề đang sort tại hàm search.

### 3.2. Rubric để ưu tiên công việc

| Thành phần | Điểm |
|---|---:|
| Requirements analysis | 10 |
| Use Case Diagram | 15 |
| Three-Layer Architecture | 20 |
| Sequence Diagram | 10 |
| Python implementation | 20 |
| Multimodal search | 10 |
| Experimental evaluation | 5 |
| Report quality | 5 |
| Demonstration | 5 |
| **Tổng** | **100** |

Đây là rubric PDF trang 22; Agent tự kiểm tra mức đáp ứng bằng bằng chứng, không tự khẳng định được 100 điểm. Ưu tiên đúng kiến trúc, UML native, prototype và demo hoàn chỉnh trước các extension tốn tài nguyên.

## 4. Mốc thực hiện và checkpoint

| Mốc | Việc thực hiện | Điều kiện chuyển mốc |
|---|---|---|
| M0 — Khảo sát | Đọc PDF, inspect workspace/VP, kiểm tra công cụ, backup dữ liệu hiện có | Có ma trận yêu cầu và đường dẫn project riêng |
| M1 — Phân tích | T1, mô tả use case, định nghĩa data/query/result contract | FR/NFR đo được; có traceability |
| M2 — Mô hình | T2–T4 trong VP; save `.vpp`; export và chụp | Đủ ba diagram native; xem và mở lại được |
| M3 — Baseline | Python ba tầng, ≥10 products, text/voice/image, ranking, CLI | Ba chế độ chạy end to end; tests cốt lõi pass |
| M4 — Hoàn thiện | Fusion text+image, lọc giá/category, order lookup đơn giản | Extension có test, phù hợp UML/code và được mô tả đúng |
| M5 — Thực nghiệm | Evaluation set, chạy demo, đo số liệu, thu screenshot | Log và metrics được sinh từ chương trình thật |
| M6 — Báo cáo | Report LaTeX English chi tiết, README, traceability, discussion | PDF đủ ảnh/code, dễ đọc, số liệu khớp artifact |
| M7 — Bàn giao | Kiểm tra project, clean install/run, ZIP, manifest, final review | Mọi gate ở phần 16 đạt; nêu rõ phần chưa đạt nếu có |

Để có bản V01 sớm, hoàn tất M0–M3 và tạo bộ report/demo baseline có thể kiểm tra. Để có bản V02, hoàn thiện M4–M7. Dùng thư mục phiên bản khi cần, tránh ghi đè bản đã chuẩn bị.

Sau mỗi mốc cập nhật `docs/AGENT_PROGRESS.md`:

```text
Mốc hiện tại / thời gian / việc đã hoàn thành / file được tạo hoặc sửa
Lệnh đã chạy và exit code / bằng chứng / vấn đề còn lại / bước tiếp theo
```

Khi ngữ cảnh bị rút gọn hoặc phiên bị ngắt, đọc progress, inspect file thật và tiếp tục từ checkpoint. Trạng thái cần dựa trên artifact đã xác minh; không đánh dấu hoàn thành chỉ vì đã viết kế hoạch.

## 5. Cấu trúc sản phẩm mục tiêu

```text
assignment6/
├── storage/
│   └── inf_sys_analysis_design_assignment_06_design_code.pdf
├── docs/
│   ├── AI_AGENT_ASSIGNMENT_06_GUIDE.md       # Guide này
│   ├── AGENT_PROGRESS.md
│   ├── requirements.md
│   ├── architecture.md
│   ├── use_cases.md
│   ├── traceability.md
│   ├── report.md
│   └── decisions_and_limitations.md
├── main.py                                 # CLI và composition root
├── presentation/
│   ├── __init__.py
│   ├── search_ui.py
│   └── result_view.py
├── application/
│   ├── __init__.py
│   ├── query_service.py
│   ├── speech_service.py
│   ├── image_service.py
│   ├── search_service.py
│   ├── ranking_service.py
│   └── order_service.py
├── data/
│   ├── __init__.py
│   ├── product_repository.py
│   ├── order_repository.py
│   ├── vector_index.py
│   ├── products.json
│   ├── orders.json
│   ├── embeddings.json                        # Có encoder/version/dimension
│   ├── images/                                # ≥10 ảnh product thực sự tồn tại
│   └── queries/                               # Ảnh query/sample embedding
├── tests/
│   ├── test_query_service.py
│   ├── test_search_pipeline.py
│   ├── test_image_similarity.py
│   ├── test_ranking.py
│   ├── test_order_search.py
│   └── test_architecture.py
├── evaluation/
│   └── queries.json                            # Ground truth định nghĩa trước
├── scripts/
│   ├── prepare_dataset.py
│   ├── build_index.py
│   ├── run_evaluation.py
│   ├── build_report.py
│   ├── validate_submission.py
│   └── desktop/                               # Helper VP nếu cần
├── models/
│   └── Assignment_06_Multimodal_Search.vpp
├── artifacts/
│   ├── diagrams/                              # Export gọn từ VP
│   ├── screenshots/                           # VP và Python chạy thật
│   ├── demo/                                  # stdout + JSON thực tế
│   ├── evaluation/                            # CSV/JSON/metrics
│   ├── tests/                                 # Kết quả test/coverage
│   ├── report/
│   │   └── Assignment_06_Report.pdf
│   ├── backups/                               # Không đưa backup vào bài nộp
│   └── automation/                            # Logs và inspect UI
├── submission/
│   ├── Assignment_06_Submission.zip
│   └── manifest.json
├── requirements.txt                           # Dependency chạy prototype
├── requirements-dev.txt                       # Test/build/report
├── requirements-automation.txt                # Nếu cần helper desktop
├── README.md
└── .gitignore
```

Có thể gộp helper nhỏ nếu không cần file riêng. Bảo đảm model component ánh xạ được sang code/storage thật; không tạo service trống chỉ để khớp tên trên UML. `VoiceInput`/`ImageUpload` có thể là adapter/method trong `search_ui.py`, nhưng giải thích vị trí trong traceability.

Runtime tối thiểu đề xuất: NumPy và Pillow. Dev: pytest, pytest-cov và công cụ xuất PDF được chọn. Automation: pywinauto, pyautogui nếu cần. Chỉ thêm web framework hoặc model AI khi có lý do; tách chúng khỏi dependency baseline.

## 6. T1 — Phân tích yêu cầu

### 6.1. Nội dung cần viết

Trong `docs/requirements.md`, mô tả hệ thống tìm sản phẩm thương mại điện tử với text, voice transcript và ảnh; các dạng input đi qua representation chung, retrieval, ranking và kết quả. Dataset local đủ để chứng minh kiến trúc, không cần payment, checkout hay production account system.

Actor bắt buộc là **Customer**. SpeechService và ImageService nội bộ không phải actor. Chỉ thêm hệ thống ngoài làm actor nếu thực sự tích hợp và giải thích vai trò.

### 6.2. Danh sách FR đề xuất

| ID | Yêu cầu | Cách nghiệm thu |
|---|---|---|
| FR-01 | Customer tìm product bằng keyword/text | Query mẫu trả product có score; xử lý uppercase/whitespace |
| FR-02 | Customer tìm bằng voice transcript mô phỏng | Đi qua SpeechService rồi cùng text retrieval pipeline |
| FR-03 | Customer tìm product tương tự image | Input ảnh/vector được chuyển thành query; cosine scores và top-k |
| FR-04 | Ba modalities dùng cấu trúc query thống nhất | QueryService và test chứng minh cùng contract |
| FR-05 | Hệ thống rank candidate và hiển thị score | RankingService riêng; score giảm dần; tie-break ổn định |
| FR-06 | Customer xem thông tin product | Product id/name/category/color/price/stock và ảnh nếu UI hỗ trợ |
| FR-07 | Customer tìm và xem order | Lookup order id; thông tin status/total; not-found rõ ràng |
| FR-08 | Dữ liệu có ≥10 products và ảnh mẫu | Validate id duy nhất, fields, đường dẫn ảnh và index |
| FR-09 | Hệ thống xử lý input sai/không có kết quả | Không traceback cho lỗi nhập thông thường; message rõ |
| FR-10 | Kết hợp text + image trong một query | Fusion score có thành phần, weights hợp lệ, test so với từng modality |
| FR-11 | Lọc giá/category khi có yêu cầu | Ví dụ `under 100` áp dụng `< 100`; filter được in trong processing |
| FR-12 | Demo/evaluation tái lập | Có lệnh chạy và output máy đọc được |

FR-01–FR-06, FR-08–FR-09 là baseline; FR-07, FR-10–FR-11 là phạm vi bổ sung của bản hoàn chỉnh. Ghi riêng phần tối thiểu của đề và phần guide đề xuất.

### 6.3. NFR có thể đo được

- **Maintainability:** Presentation không import repository/storage/index; các thay đổi thuật toán nằm trong Application/Data.
- **Reproducibility:** dataset, encoder và tie-break cố định; cùng input/config cho cùng thứ tự và score trong sai số số thực.
- **Usability:** README có cài đặt và lệnh ví dụ; mỗi chế độ hiển thị rõ đang mô phỏng hay xử lý ảnh thật.
- **Robustness:** xử lý query rỗng, image hỏng, dimension sai, zero vector, order không tồn tại và dataset thiếu field.
- **Performance:** mục tiêu local đề xuất ≤1 giây/query trên dataset 12 products sau khi index đã tải; đo thực tế, ghi cấu hình và loại trừ startup khi phù hợp. Đây là mục tiêu của guide, không phải số liệu PDF.
- **Portability:** path dùng `pathlib`, relative với project root; không yêu cầu máy chấm có thư mục người dùng giống máy hiện tại.
- **Data ownership:** nếu có order search với customer context, không trả order của customer khác; context này là mô phỏng, không tuyên bố có authentication production.

### 6.4. Mô tả use case dạng văn bản

Tạo bảng ngắn cho cả 7 use case bắt buộc. Mỗi bảng có actor, goal, preconditions, trigger, main flow, alternate/error flow và postconditions. Với voice, ghi rõ transcript giả lập; với image, ghi rõ encoder; với order, ghi phạm vi customer context.

Tạo `docs/traceability.md` liên kết **FR → use case → component → Python method → test/demo → report section**. Dùng traceability để phát hiện chức năng chỉ tồn tại trên sơ đồ hoặc trong report.

## 7. Thiết kế chung trước khi viết code

### 7.1. Ba tầng và composition root

```text
Customer
  → Presentation: SearchUI / VoiceInput / ImageUpload / SearchResultView
  → Application: QueryService / SpeechService / ImageService / SearchService / RankingService
  → Data: ProductRepository / OrderRepository / VectorIndex / JSON / ImageStorage
```

`main.py` khởi tạo và inject dependency; đây là composition root nên có thể import cả ba tầng. `presentation/` chỉ gọi service, thu input và trình bày result; không tự load JSON, lấy products từ repository hoặc tính cosine. `application/` không phụ thuộc `presentation/`. `data/` không phụ thuộc các tầng trên.

CLI là Presentation Layer hợp lệ cho prototype. Không cần làm website để đáp ứng baseline. Nếu thêm web UI, giữ nguyên service contract và cập nhật sơ đồ, test và README.

### 7.2. Query contract thống nhất

Ví dụ schema mục tiêu, không phải kết quả đã chạy:

```json
{
  "type": "text",
  "raw_input": "find black running shoes",
  "query": "black running shoes",
  "tokens": ["black", "running", "shoes"],
  "embedding": null,
  "filters": {"category": null, "max_price_exclusive": null},
  "top_k": 5,
  "weights": {"text": 1.0, "image": 0.0},
  "customer_id": null
}
```

- `type`: `text`, `voice`, `image`, `multimodal`; xác định một tập giá trị được validate.
- Text/voice chứa text và tokens; image chứa embedding và metadata encoder; multimodal chứa cả hai.
- Voice vẫn có `type=voice` để truy vết nguồn input nhưng dùng text retrieval sau transcribe.
- `raw_input` của ảnh lưu path/metadata, không nhét toàn bộ binary vào JSON demo.
- `top_k` là số nguyên dương có giới hạn phù hợp; không âm, không boolean.
- Embedding phải là vector số hữu hạn, đúng dimension của index; không chứa NaN/Infinity.
- Filters và weights được validate một lần tại boundary/service; tổng weights của modalities sử dụng bằng 1.
- Một `dict`, `TypedDict` hoặc dataclass đều được; chọn một cách và dùng nhất quán. Với JSON output, phải serialize được.

Không cộng text token vector với image feature vector khi chúng khác không gian biểu diễn. Fusion ở mức score là cách đơn giản phù hợp cho prototype này.

### 7.3. Result contract

Mỗi lần search trả một envelope có `query`, `processing`, `results` và thông tin encoder/ranking. Mỗi result có:

```text
rank, product_id, name, category, color, price, stock,
raw_text_score, text_score, image_score, business_score,
final_score, matched_terms, image_path
```

`processing` ghi normalized query, modality, filters, encoder/dimension nếu có, số candidate trước/sau filter, ranking weights và top-k. In cả input, processing, product và final score trong demo. Result không được sửa trực tiếp object product gốc trong repository.

### 7.4. Interface cần hiện thực

| Component | Interface mục tiêu và trách nhiệm |
|---|---|
| QueryService | `text_query(text, ...)`, `voice_query(transcript, ...)`, `image_query(embedding, ...)`, `multimodal_query(text, embedding, ...)`; chuẩn hóa và validate |
| SpeechService | `transcribe(audio_input)`; baseline nhận chuỗi transcript và trả chuỗi, khai báo mô phỏng |
| ImageService | `encode(image_path)`; đọc/validate ảnh và tạo descriptor; hoặc baseline vector mô phỏng được chỉ rõ |
| SearchService | `search(query)` điều phối; `retrieve_candidates(query)` tạo candidate chưa xếp hạng; dùng repository/index rồi RankingService |
| RankingService | `rank(candidates, query)` tính final score, sort, tie-break, cắt top-k |
| ProductRepository | `all_products()`, `get_by_id(product_id)`; load/validate products JSON |
| OrderRepository | `find_order(order_id, customer_id=None)`; load orders JSON |
| VectorIndex | Load/build index, kiểm tra dimension, cosine scoring; trả candidate id + similarity |
| OrderService | Lookup và áp dụng customer scope; trả result/not-found; extension của bản hoàn chỉnh |
| SearchUI | Nhận input, gọi service đúng pipeline, chuyển result tới ResultView |
| SearchResultView | Format output CLI; không tính lại rank hoặc truy cập database |

Tham số chi tiết có thể thay đổi để code rõ hơn, nhưng phải đồng bộ UML, traceability và README. Không giữ API lỗi thời trong sơ đồ sau khi refactor.

## 8. T2–T4 — Nội dung UML bắt buộc trong Visual Paradigm

### 8.1. Use Case Diagram: `UC_Multimodal_Ecommerce_Search`

1. Tạo system boundary tên `Multimodal E-Commerce Search System`.
2. Đặt actor `Customer` ngoài boundary.
3. Tạo đủ 7 use case bên trong, đúng tên ở phần 3.1.
4. Dùng association actor–use case để thể hiện mục tiêu của Customer.
5. Dùng generalization cho ba dạng tìm kiếm: `Search by Keyword`, `Search by Voice`, `Search by Image` chuyên biệt hóa `Search Product`; đầu tam giác rỗng hướng về `Search Product`.
6. Customer có association với Search Product, Search Order, View Product, View Order; có thể nối thêm với các modality để diagram rõ ràng.
7. View Product/View Order là mục tiêu xem chi tiết; không tự biến chúng thành bước luôn bắt buộc trong mọi search.

Không dùng `Search Product <<include>> Search by Keyword/Voice/Image` theo cách khiến mọi lần search bắt buộc chạy cả ba modality. Không dùng use case diagram để vẽ flowchart. Nếu thêm `<<include>>`/`<<extend>>`, phải có ý nghĩa và hướng connector đúng, được giải thích trong `docs/use_cases.md`.

Nghiệm thu: actor là actor UML, use case là ellipse native, boundary đúng loại, generalization/association là model relationship thật và không có phần tử mồ côi.

### 8.2. Component Diagram: `CMP_Three_Layer_Architecture`

Tạo **Component Diagram có ba UML package**, thay vì chỉ vẽ ba hình chữ nhật:

| Package | Components bắt buộc theo thiết kế đề |
|---|---|
| Presentation Layer | SearchUI, VoiceInput, ImageUpload, SearchResultView |
| Application / Intelligence Layer | QueryService, SpeechService, ImageService, SearchService, RankingService |
| Data Layer | ProductRepository, OrderRepository, VectorIndex, ProductDatabase, OrderDatabase, ImageStorage |

Thêm `OrderService` trong Application khi triển khai extension; chú thích ProductDatabase/OrderDatabase là JSON storage trong prototype, VectorIndex là index in-memory hoặc JSON. Không gọi chúng là PostgreSQL/FAISS nếu không sử dụng thực tế.

Dependencies tối thiểu để mô hình phản ánh code:

```text
VoiceInput → SearchUI
ImageUpload → SearchUI
SearchUI → SearchResultView
SearchUI → SpeechService
SearchUI → QueryService
SearchUI → ImageService
SearchUI → SearchService
SearchService → ProductRepository
SearchService → VectorIndex
SearchService → RankingService
ImageService → ImageStorage
ProductRepository → ProductDatabase
OrderRepository → OrderDatabase
SearchUI → OrderService → OrderRepository        # Khi có order extension
```

Mũi tên dependency từ bên dùng đến bên được dùng, dùng đường nét đứt/đầu mũi tên đúng UML. Các dependency nội bộ một tầng hợp lệ; không được có dependency Presentation → Data. Thể hiện package ownership và vị trí components thật, không chỉ đặt shapes nhìn có vẻ nằm trong khung.

Ưu tiên bố cục ba hàng hoặc ba cột, font nhất quán. Giữ màu mặc định của Visual Paradigm đang cài cho mọi UML; không tự chọn palette, tô màu phân tầng hay đổi màu đường nối. Lấy style từ model element mới do VP tạo nếu cần khôi phục default. Nối ngang/dọc với góc vuông, chia điểm bám và hành lang riêng; tránh chồng nét, giao cắt hoặc đi xuyên qua node không liên quan. Kiểm tra ảnh xuất và mở lại file `.vpp` trong GUI để xác nhận đường nối vẫn hiện đầy đủ sau lưu.

### 8.3. Sequence Diagram: `SEQ_Voice_Product_Search`

Participants bắt buộc, sắp từ trái sang phải:

```text
Customer | SearchUI | SpeechService | QueryService |
SearchService | ProductRepository | RankingService
```

Lifeline dịch vụ có thể viết `speechService:SpeechService`, v.v. Customer là actor. Dùng main flow phù hợp với interface ở phần 7:

| Bước | Sender → Receiver | Message / return |
|---|---|---|
| 1 | Customer → SearchUI | `searchByVoice(transcriptInput)` |
| 2 | SearchUI → SpeechService | `transcribe(transcriptInput)` |
| 3 | SpeechService → SearchUI | Return `transcript` |
| 4 | SearchUI → QueryService | `voice_query(transcript)` |
| 5 | QueryService → SearchUI | Return `query` |
| 6 | SearchUI → SearchService | `search(query)` |
| 7 | SearchService → SearchService | `retrieve_candidates(query)` nếu cần thể hiện self-call |
| 8 | SearchService → ProductRepository | `all_products()` |
| 9 | ProductRepository → SearchService | Return `products` |
| 10 | SearchService → SearchService | Match terms và áp dụng filters thành `candidates` |
| 11 | SearchService → RankingService | `rank(candidates, query)` |
| 12 | RankingService → SearchService | Return `ranked_results` |
| 13 | SearchService → SearchUI | Return `search_result` gồm processing/results |
| 14 | SearchUI → Customer | Display products và ranking scores |

Thêm note cạnh SpeechService: **Simulated STT: input is already transcribed text**. Nếu biểu diễn audio ở mức thiết kế conceptual, ghi khác biệt prototype; không để diagram tuyên bố đã nhận microphone thật.

Dùng synchronous call, return nét đứt, activation hợp lý và thứ tự thời gian từ trên xuống. Có thể thêm `alt` cho input rỗng/không có candidate, nhưng main flow đủ bảy participants là điều kiện bắt buộc. RankingService nhận candidates, không đọc database qua UI.

### 8.4. Các điều kiện native và đồng bộ

- Project `.vpp` chứa ba diagram có thể chọn, mở và sửa từng model element/connector.
- Không chèn một ảnh PNG/PlantUML vào VP rồi gọi đó là project UML hoàn chỉnh.
- Mermaid/PlantUML chỉ dùng làm bản nháp nếu hữu ích; không thay cho project VP bắt buộc.
- Không tạo file text/ZIP tùy ý rồi đổi đuôi thành `.vpp`.
- Sau khi code ổn định, rà lại message/method/component của ba diagram và cập nhật cho khớp.

## 9. Thao tác và tự động hóa Visual Paradigm trên Windows

### 9.1. Kiểm tra và bảo toàn phiên đang mở

1. Inspect window/process, chụp trạng thái VP khi nhìn thấy đúng ứng dụng.
2. Xác định project đang mở có dữ liệu chưa save hay không. Không tự đóng hoặc bỏ changes.
3. Lưu bản dự phòng của project hiện có, nếu cần, bằng Save As hoặc bản sao file đã save. Ghi lại đường dẫn và file gốc.
4. Tạo project mới cho Assignment 06, hoặc Save As bản riêng nếu có model liên quan có thể tái sử dụng.
5. Lưu tại `models/Assignment_06_Multimodal_Search.vpp`. Nếu thư mục/file đã có, inspect và backup trước khi cập nhật.
6. Tạo lần lượt Use Case, Component, Sequence; save sau từng diagram và sau từng nhóm sửa đáng kể.

Visual Paradigm Community Edition có hỗ trợ UML cho mục đích phi thương mại; vẫn kiểm tra menu và tính năng trên bản cài hiện tại. [Tài liệu Visual Paradigm CE](https://s.visual-paradigm.com/solution/freeumldesigntool/).

### 9.2. Chiến lược automation

Ưu tiên control được inspect và chờ state thay vì click mù:

1. Nếu UIA đọc được control: dùng AutomationId, name/title và control type đã quan sát.
2. Nếu Java control tree không đầy đủ: dùng win32 để tìm window; kết hợp menu, keyboard, screenshot và clipboard.
3. Nếu cần thao tác tọa độ: focus VP, kiểm tra window rectangle, DPI và screenshot mới; click theo vị trí tương đối đã xác minh.
4. Nếu GUI lặp lại quá nhiều và Open API dùng được: cân nhắc plugin local ở phần 9.5.

Playwright dùng cho browser/web UI, không dùng để điều khiển trực tiếp canvas Java desktop. Không giả định mọi Swing control có AutomationId chỉ vì pywinauto được cài.

Helper inspect/capture tối thiểu có thể lưu thành `scripts/desktop/inspect_vp.py`:

```python
from pathlib import Path
from pywinauto import Desktop

artifact_dir = Path("artifacts/automation")
artifact_dir.mkdir(parents=True, exist_ok=True)

windows = [
    w for w in Desktop(backend="win32").windows()
    if "Visual Paradigm" in w.window_text()
    and w.class_name() == "SunAwtFrame"
]
if len(windows) != 1:
    raise RuntimeError("Inspect danh sách window và chọn đúng phiên VP trước.")

vp_window = windows[0]
print(vp_window.window_text(), vp_window.handle, vp_window.rectangle())
if vp_window.is_minimized():
    vp_window.restore()
vp_window.set_focus()
vp_window.capture_as_image().save(artifact_dir / "vp_current.png")

# UIA có thể thiếu controls; việc inspect này cần timeout trong helper thực tế.
uia_window = Desktop(backend="uia").window(handle=vp_window.handle)
uia_window.print_control_identifiers(depth=2)
```

Mở ảnh vừa chụp bằng công cụ đọc ảnh để xác nhận đúng VP. Capture theo rectangle có thể ghi hình ứng dụng khác đang che VP; ảnh như vậy không phải bằng chứng diagram. Helper thực tế cần timeout, xử lý lỗi focus và log; giữ screenshot scope ở cửa sổ/region liên quan.

### 9.3. Quy trình tạo và chỉnh diagram bằng GUI

- Mở chức năng tạo diagram từ menu/Diagram Navigator thực tế; chọn đúng loại UML, đặt tên theo phần 8.
- Tạo model element từ palette tương ứng, nhập tên và kiểm tra tên sau nhập.
- Tạo quan hệ bằng connector tool đúng loại, inspect hai endpoints và hướng connector.
- Với component package: kiểm tra owner/containment qua model tree hoặc properties.
- Với sequence: đặt lifeline, call và return đúng thứ tự; kiểm tra activation và message labels.
- Chỉnh alignment, khoảng cách, font và zoom. Xem toàn diagram, không chỉ vùng đang edit.
- Sau mỗi thay đổi quan trọng: observe → act → verify → save → checkpoint.
- Với văn bản tiếng Việt hoặc đường dẫn có khoảng trắng: ưu tiên paste clipboard nếu keyboard typing gây lỗi; kiểm tra nội dung đã dán.
- Chờ dialog/control xuất hiện hoặc thay đổi màn hình bằng polling có timeout. Chỉ dùng pause ngắn khi cần ổn định rendering.
- Nếu một thao tác không có hiệu quả, không lặp vô hạn. Sau tối đa ba lần thử cùng cách, inspect lại hoặc chuyển chiến lược; xem phần 15.

### 9.4. Đọc, backup và sửa shortcut được chỉ định

Đọc shortcut và backup trước; đoạn này không gọi `.Save()` nên chưa sửa shortcut:

```powershell
Set-Location -LiteralPath 'D:\PROJECTS\ISA-D\assignment6'
$vpShortcutPath = 'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Visual Paradigm CE\Visual Paradigm 18.0.lnk'
$vpBackupDir = Join-Path (Get-Location).Path 'artifacts\backups'
New-Item -ItemType Directory -Path $vpBackupDir -Force | Out-Null
$vpTimestamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
Copy-Item -LiteralPath $vpShortcutPath -Destination (Join-Path $vpBackupDir "Visual-Paradigm-18.0-$vpTimestamp.lnk")

$vpShell = New-Object -ComObject WScript.Shell
$vpLink = $vpShell.CreateShortcut($vpShortcutPath)
$vpOriginal = [ordered]@{
    ShortcutPath = $vpShortcutPath
    TargetPath = $vpLink.TargetPath
    Arguments = $vpLink.Arguments
    WorkingDirectory = $vpLink.WorkingDirectory
    IconLocation = $vpLink.IconLocation
    Description = $vpLink.Description
}
$vpOriginal | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $vpBackupDir "vp-shortcut-$vpTimestamp.json")
$vpOriginal
```

Chỉ khi target/working directory thực sự sai, có thể sửa chúng bằng COM. Đoạn dưới dùng các biến của đoạn trên và **thực sự ghi shortcut**:

```powershell
$vpVerifiedTarget = 'C:\Program Files\Visual Paradigm CE 18.0\bin\Visual Paradigm.exe'
if (-not (Test-Path -LiteralPath $vpVerifiedTarget -PathType Leaf)) {
    throw 'Executable chưa được xác minh; giữ nguyên shortcut.'
}
$vpLink.TargetPath = $vpVerifiedTarget
$vpLink.WorkingDirectory = Split-Path -Parent $vpVerifiedTarget
# Chỉ đổi Arguments nếu đã xác minh cú pháp và lý do cần đổi.
$vpLink.Save()

$vpCheck = $vpShell.CreateShortcut($vpShortcutPath)
$vpCheck | Select-Object TargetPath, Arguments, WorkingDirectory
```

Giữ các thuộc tính không cần đổi. Không ghi đè `.lnk` bằng text. Nếu sửa lỗi dẫn đến launcher không hoạt động, khôi phục bản backup bằng `Copy-Item -LiteralPath ... -Destination $vpShortcutPath` và kiểm tra lại. Ghi thay đổi vào progress.

Nếu cần khởi chạy và chưa có phiên VP phù hợp, dùng shortcut hoặc executable đã xác minh. Với `Start-Process` cho ứng dụng VP mà người dùng cần quan sát/thao tác, cửa sổ hiển thị là phù hợp; helper chạy nền dùng `-WindowStyle Hidden`. Không tạo thêm phiên VP khi phiên đang mở có thể dùng được.

### 9.5. Đường thay thế qua Java Open API

Open API là lựa chọn để tạo model/diagram native khi được bản cài hỗ trợ; sự tồn tại `openapi.jar` chưa chứng minh plugin đã chạy được. Không bắt đầu bằng cách đoán API hoặc chỉnh trực tiếp binary `.vpp`.

1. Inspect API cài local và đọc tài liệu chính thức.
2. Dùng `javap` xác minh chữ ký trước khi viết code; Java trên PATH và Java bundled của VP có thể khác version.
3. Tạo plugin nhỏ trong workspace, compile với `openapi.jar`, chọn bytecode tương thích với runtime VP.
4. Test tạo một diagram và một model element native trong project thử riêng.
5. Nếu smoke test đạt, mở rộng sang các actors, use cases, packages, components, lifelines và connectors.
6. Làm plugin chạy lại được: tìm phần tử theo định danh/tên thuộc project này, không tạo bản sao mỗi lần; không xóa phần tử ngoài phạm vi.
7. Save project qua API đã xác minh hoặc GUI; xem lại cả ba diagram trong VP.

Ví dụ inspect, không phải script hoàn thành diagram:

```powershell
$vpApiJar = 'C:\Program Files\Visual Paradigm CE 18.0\lib\openapi.jar'
javap -classpath $vpApiJar com.vp.plugin.VPPlugin
javap -classpath $vpApiJar com.vp.plugin.ApplicationManager
```

API nằm trong `lib/openapi.jar`; plugin cần descriptor và implementation phù hợp. [Hướng dẫn implement plugin](https://www.visual-paradigm.com/support/documents/pluginuserguide/2186/2188/57181_implementing.html).

Cài plugin qua chức năng `Help > Install Plugin` nếu có; ưu tiên folder/ZIP trong workspace và vị trí plugin mà VP chỉ định. Không đóng VP chưa save. Tài liệu hướng dẫn restart sau cài và không đóng gói `openapi.jar` vào thư mục `lib` của plugin. [Hướng dẫn cài plugin](https://circle.visual-paradigm.com/docs/open-api/installing-plug-in/installing-a-visual-paradigm-plug-in/).

Nếu menu/API không dùng được trong CE hiện tại, quay lại GUI automation. Ghi nguyên nhân thật; không dùng một project giả làm giải pháp thay thế.

### 9.6. Export và xác minh project

Với từng diagram, tạo:

- `artifacts/diagrams/use_case.png`
- `artifacts/diagrams/three_layer_architecture.png`
- `artifacts/diagrams/voice_sequence.png`
- Screenshot tương ứng trong `artifacts/screenshots/`, cho thấy VP và diagram đang mở.

Theo tài liệu, lệnh export có thể nằm ở `Project > Export > Active Diagram as Image…`; một số giao diện cũ dùng `File > Export`. Kiểm tra menu đang có trước thao tác. Ưu tiên PNG nền trắng, chất lượng đủ đọc trên report. [Tài liệu export diagram](https://circle.visual-paradigm.com/docs/export-and-import/export-as-images/exporting-active-diagram-as-image/).

Save project, kiểm tra file tồn tại và size hợp lý, rồi mở lại chính `.vpp` đã save để kiểm tra đủ ba diagram và native elements. Chỉ kiểm tra file tồn tại chưa đủ. Có thể mở lại project trong cùng phiên sau khi toàn bộ changes đã save; không cần đóng mọi ứng dụng của người dùng.

## 10. T5 — Triển khai Python end to end

### 10.1. Setup và dependency

Tạo virtual environment local; gọi interpreter trực tiếp để tránh lệ thuộc PowerShell activation policy:

```powershell
Set-Location -LiteralPath 'D:\PROJECTS\ISA-D\assignment6'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Viết manifest trước khi chạy install từ manifest. Chọn phiên bản dependency thực sự cài và chạy được; ghi Python version đã kiểm tra vào README. Không tự thay interpreter hệ thống. Helper desktop có thể dùng interpreter đã có công cụ hoặc cài riêng manifest automation, không bắt người chấm cài pywinauto để chạy search.

### 10.2. Product dataset

Schema mỗi product:

```json
{
  "product_id": 1,
  "name": "Nike Running Shoes",
  "brand": "Nike",
  "category": "shoes",
  "color": "black",
  "price": 120.0,
  "stock": 10,
  "description": "Black running shoes for everyday training.",
  "image": "data/images/p001.png"
}
```

Dùng một tên khóa `product_id` xuyên suốt; nếu giữ `id` theo ví dụ đề thì phải thống nhất mọi nơi. Giá không âm, stock là integer không âm, id duy nhất, image path tương đối với project root. Metadata embedding có thể lưu trong `embeddings.json` và liên kết bằng product_id thay vì nhét binary vào product JSON.

Dataset tham khảo có thể tạo như sau; các giá trị này là **đề xuất dữ liệu**, chưa phải kết quả thực nghiệm:

| ID | Name | Category | Color | Price USD | Stock |
|---|---|---|---|---:|---:|
| 1 | Nike Running Shoes | shoes | black | 120 | 10 |
| 2 | Adidas Running Shoes | shoes | white | 100 | 15 |
| 3 | Black Leather Bag | bag | black | 80 | 20 |
| 4 | Blue Sports Shoes | shoes | blue | 75 | 12 |
| 5 | Nike Budget Running Shoes | shoes | black | 95 | 8 |
| 6 | Red Canvas Shoes | shoes | red | 60 | 18 |
| 7 | White Casual Shoes | shoes | white | 45 | 20 |
| 8 | Brown Leather Bag | bag | brown | 90 | 6 |
| 9 | Black Backpack | bag | black | 55 | 10 |
| 10 | Blue Cotton T-Shirt | clothing | blue | 25 | 30 |
| 11 | Black Sports Jacket | clothing | black | 85 | 7 |
| 12 | Green Travel Backpack | bag | green | 65 | 0 |

Tạo description không chứa keyword sai category chỉ để tăng score. Với ảnh, ưu tiên sample có sẵn đúng quyền sử dụng; nếu không có, sinh ảnh minh họa riêng bằng Pillow với màu/hình dạng khác nhau và ghi chúng là synthetic illustrations. Không dùng một ảnh giống nhau cho mọi product hoặc gọi ảnh minh họa là ảnh chụp thật.

`prepare_dataset.py` phải idempotent: kiểm tra output hiện có và chỉ overwrite khi chủ động regenerate. Không hủy dataset người dùng đã sửa. Khi dùng random, cố định seed. `build_index.py` lưu encoder/version/dimension và dấu hiệu nhận biết ảnh nguồn; rebuild khi dataset/encoder thay đổi.

### 10.3. Text search

1. Validate input là chuỗi, giới hạn độ dài hợp lý, strip và normalize case.
2. Tokenize; bỏ dấu câu và các từ mang tính yêu cầu như `find`, `show`, `me` theo stopword list nhỏ được công bố.
3. Chuẩn hóa alias có kiểm soát, ví dụ `shoe` → `shoes`; không cố triển khai NLP ngoài phạm vi.
4. Extract filter giá/category khi extension này được bật. `under 100`/`below 100` là giá `< 100`, khác với `at most 100` là `≤ 100`.
5. Tạo query object qua QueryService.
6. SearchService lấy products qua ProductRepository, match token trên name/category/color/description.
7. Tính raw match count trên các token query duy nhất; tránh lỗi substring như `red` khớp một phần từ không liên quan.
8. Lấy candidates có match phù hợp, áp dụng filters rồi gửi RankingService. Query chỉ có filter có thể lấy toàn bộ products trước lọc nếu chính sách đã công bố.

Keyword search đơn giản có thể là OR matching như đề. Để query `black shoes` đỡ trả bag không liên quan, bản hoàn chỉnh có thể coi category rõ ràng là filter. Công bố chính sách và viết test tương ứng; không thay định nghĩa thành công sau khi xem kết quả.

### 10.4. Voice search mô phỏng

```text
SearchUI nhận transcript string
  → SpeechService.transcribe(transcript)
  → QueryService.voice_query(text)
  → SearchService.search(query)
  → Retrieval → RankingService → SearchResultView
```

`SpeechService.transcribe` baseline trả transcript sau validate. Demo phải ghi `Voice mode: simulated speech-to-text`. Với transcript và text query giống nhau, cùng filters/config phải trả cùng products và scores. Đừng chỉ đổi nhãn thành voice mà bỏ qua SpeechService.

Không bắt buộc microphone, audio recording, API key hoặc model speech. Nếu thêm real STT sau baseline, giữ adapter riêng, có cách demo offline và ghi model/version, dependency, thời gian xử lý thực tế.

### 10.5. Image-similarity search

Đề cho phép artificial vectors. Có hai mức hợp lệ; chọn và công bố rõ:

| Mức | Cách triển khai | Cách mô tả |
|---|---|---|
| Baseline nhanh | Gán vector số cố định cho ≥10 products; query có vector fixture; cosine retrieval | `Simulated image embeddings`; ảnh đi kèm chỉ minh họa, không tuyên bố đã encode pixels |
| Mức khuyến nghị | Query và product image qua cùng một pixel feature encoder nhẹ | `Handcrafted visual descriptors`; có xử lý ảnh thật nhưng không phải learned semantic embeddings |

Để bản hoàn chỉnh có lệnh `--image` hoạt động thực tế, ưu tiên mức thứ hai. Một encoder local không cần tải model có thể dùng RGB histogram 8 bins/channel (24 chiều) kết hợp grayscale thumbnail 8×8 (64 chiều), tổng 88 chiều; chuẩn hóa từng phần, công bố weights, rồi chuẩn hóa vector cuối. Đây là thiết kế đề xuất, Agent phải kiểm thử, không bảo đảm trước chất lượng semantic search.

Quy trình:

1. Product images được encode một lần và lưu/index bằng cùng encoder/version/dimension.
2. Query ảnh được mở, validate, chuyển RGB, xử lý orientation nếu cần, resize/encode cùng cách.
3. QueryService tạo image query có embedding và encoder metadata.
4. VectorIndex tính cosine với product vectors.
5. SearchService ghép product metadata, áp dụng filters.
6. RankingService sort theo score, tie-break và top-k.

Cosine:

```text
similarity(a, b) = dot(a, b) / (norm(a) * norm(b))
```

Dimension không khớp hoặc NaN/Infinity phải được từ chối rõ ràng. Với zero norm, trả 0.0 theo baseline đề và ghi lý do nếu cần. Chặn sai số số thực ra ngoài [-1, 1]. Nếu cần image score trong [0, 1] để fusion, chọn transformation nhất quán, ví dụ clamp âm về 0; không nhầm cosine 0 thành bằng chứng ảnh giống nhau.

Chỉ dùng phép cộng `0.5 * text_score + 0.5 * image_score` khi hai score đã chuẩn hóa phù hợp. Không giả lập ảnh bằng cách lấy product_id từ tên file rồi luôn trả product đó, trừ khi đây là vector fixture mô phỏng được khai báo rõ; cách này không phải pixel encoding.

### 10.6. Retrieval và ranking tách biệt

Với dataset nhỏ, retrieval có thể tính score cho toàn bộ products nhưng **chưa sort/cắt top-k cuối cùng**. RankingService sở hữu thứ tự trả về:

```text
raw_text_score = number of unique query terms matched
text_score = raw_text_score / term_count if term_count > 0 else 0.0
image_score = normalized cosine score
final_score = w_text * text_score + w_image * image_score
```

- Text/voice: weights `(1.0, 0.0)`.
- Image: weights `(0.0, 1.0)`.
- Text + image: weights `(0.5, 0.5)` mặc định, có thể cấu hình và validate.
- Business/stock signal là extension; nếu dùng, công bố công thức và ảnh hưởng, test stock=0.
- Modality không có input nhận component score 0.0 và weight 0.0; query rỗng ở mọi modality bị từ chối thay vì chia cho 0.
- Tie-break cố định bằng product_id tăng dần sau final_score giảm dần.
- Với fusion, lấy union candidates của modalities, không intersection mặc định hoặc top-1 mỗi nhánh; với 12 products có thể xét toàn dataset.
- Không boost score bằng giá/stock một cách bí mật khiến result sai nội dung query.

### 10.7. Order search và extension

Tạo orders local có `order_id`, `customer_id`, `date`, `status`, `total`; có thể thêm OrderItem nếu phục vụ minh họa. Dùng O001/C001 và ít nhất một order của C002 để kiểm tra customer scope.

Presentation → OrderService → OrderRepository → orders JSON. Order lookup không đưa order vào product ranking. Hỗ trợ id chính xác trước; `latest order` chỉ thêm nếu có date, sorting và test phù hợp.

Sau baseline, ưu tiên fusion, price/category filter và order lookup vì dễ demo, không cần remote API. Vector database, semantic model lớn, real STT và web UI chỉ thêm khi có đủ thời gian để cập nhật toàn bộ deliverables và kiểm tra lại.

### 10.8. CLI contract và lệnh demo

Implement argparse hoặc cơ chế tương đương. `python main.py` không tham số nên chạy demo tổng hợp có cả ba chế độ để người chấm dễ kiểm tra. Cung cấp `--help`; lỗi input có message rõ và exit code khác 0, query hợp lệ không có result vẫn là trạng thái thành công.

Ví dụ dưới đây là interface mục tiêu sau khi đã tạo code/dataset:

```powershell
.\.venv\Scripts\python.exe main.py --help
.\.venv\Scripts\python.exe main.py --demo
.\.venv\Scripts\python.exe main.py --mode text --query "black shoes" --top-k 5
.\.venv\Scripts\python.exe main.py --mode voice --query "find black running shoes" --top-k 5
.\.venv\Scripts\python.exe main.py --mode image --image data/queries/black_shoe_query.png --top-k 5
.\.venv\Scripts\python.exe main.py --mode multimodal --query "black shoes" --image data/queries/black_shoe_query.png --top-k 5
.\.venv\Scripts\python.exe main.py --mode text --query "find Nike shoes under 100 dollars" --top-k 5
.\.venv\Scripts\python.exe main.py --mode order --order-id O001 --customer-id C001
```

Nếu V01 chỉ dùng artificial vectors, thêm `--embedding-file data/queries/shoe_vector.json` và điều chỉnh lệnh image demo cho trung thực. Để bản V02 dùng `--image` như trên, phải có pixel encoder thực sự. README chỉ chứa lệnh tương ứng với phiên bản đã bàn giao.

Thêm `--json` và `--output` nếu hữu ích để lưu result/demo có thể kiểm tra. Các sample path phải thực sự có trong package, không chỉ xuất hiện trong hướng dẫn.

## 11. Kiểm thử và đánh giá thực nghiệm

### 11.1. Test logic có ý nghĩa

Với logic mới, viết test cho hành vi trước hoặc cùng triển khai; chạy test thất bại, implement rồi refactor. Không viết test cho một tên file đơn thuần thay cho kiểm tra pipeline.

| Nhóm | Trường hợp cần kiểm tra |
|---|---|
| Dataset/repository | ≥10 products, id duy nhất, fields hợp lệ, ảnh có thật, không mutate product khi search |
| Query | Whitespace/case, punctuation, input rỗng, type không hỗ trợ, top-k không hợp lệ |
| Text | Relevant product lên trước; alias/token policy; no-match; giá dưới 100 loại product giá 100 và 120 |
| Voice | Thực sự gọi SpeechService; text/voice cùng transcript có cùng result/score |
| Image | Cùng vector cosine≈1; orthogonal≈0; zero vector=0; dimension mismatch; NaN; ảnh hỏng/không tồn tại |
| Ranking | Sort giảm dần, tie-break ổn định, top-k đúng, weights hợp lệ, score components khớp công thức |
| Fusion | Cả text và image ảnh hưởng kết quả; không cộng vector khác không gian; candidate union |
| Order | Lookup đúng, not-found, customer C001 không xem order C002 |
| Architecture | Presentation không import data/repository; data không import application/presentation |
| CLI integration | Ba mode bắt buộc chạy subprocess thành công, output có input/processing/products/scores |

Đặt mục tiêu coverage ≥80% cho logic application/data; coverage là chỉ báo bổ sung, không thay quality của assertion. Có thể kiểm tra boundary imports qua AST, nhưng vẫn review luồng thật để tránh UI truy cập storage bằng cách khác.

Lệnh mục tiêu:

```powershell
New-Item -ItemType Directory -Path artifacts/tests -Force | Out-Null
.\.venv\Scripts\python.exe -m pytest -q --cov=application --cov=data --cov-report=term-missing --cov-report=html:artifacts/tests/coverage --junitxml=artifacts/tests/junit.xml
.\.venv\Scripts\python.exe -m compileall -q main.py presentation application data scripts
.\.venv\Scripts\python.exe -m pip check
```

Chạy checks đúng phiên bản source được bàn giao. Nếu project đã có lint/typecheck thì chạy phù hợp. Chỉ broaden test khi có thay đổi hoặc rủi ro chưa giải quyết; không lặp toàn bộ suite vô ích sau khi pass.

### 11.2. Evaluation set độc lập với unit tests

Tạo `evaluation/queries.json` **trước khi ghi kết quả**, với ít nhất 12 query, ví dụ 4 text + 4 voice + 4 image; thêm multimodal/order cases khi extension được triển khai. Mỗi case có id, input, modality, expected product ids hoặc relevant set, criterion và chú thích.

Các nhóm query nên có:

- `black shoes`, `blue shoes`, `black bag`, `find Nike shoes under 100 dollars`.
- Voice transcript như `find running shoes`, `show me a white shoe`, và một query tương đương text để đối chiếu.
- Image query gồm một ảnh product giống hệt để sanity check, ảnh biến đổi nhẹ, và ảnh khác product/category; không chỉ test exact duplicates.
- Negative/robustness cases riêng: query vô nghĩa, image hỏng, no-match, zero vector. Không gọi no-result đúng của negative case là sai thuật toán.
- Fusion và order cases riêng nếu có; không trộn denominator mà không giải thích.

Định nghĩa trước metric retrieval, ví dụ `top_1_product_id ∈ relevant_ids`. Nếu dùng top-k success, ghi rõ khác top-1. Báo success rate cho retrieval queries và robustness pass rate riêng để không tăng tỷ lệ thành công bằng nhiều input lỗi dễ xử lý.

Script `run_evaluation.py` gọi chính service pipeline; không hardcode top-1 hoặc score vào output. Xuất ít nhất:

```text
artifacts/evaluation/results.csv
artifacts/evaluation/results.json
artifacts/evaluation/metrics.json
```

Mỗi row ghi query id, mode/input, expected, actual top-1/top-k, scores, success và processing time. Metrics ghi `total_queries`, `successful_queries`, `success_rate`, breakdown theo mode và cấu hình encoder/ranking.

```text
Success Rate = Number of Successful Queries / Total Number of Queries
```

Lệnh mục tiêu:

```powershell
.\.venv\Scripts\python.exe scripts/run_evaluation.py --queries evaluation/queries.json --output artifacts/evaluation
```

### 11.3. Kết quả sai và giới hạn

Report phải có phân tích kết quả sai theo mục 22 PDF. Nếu evaluation set không có failure, ghi đúng là chưa quan sát failure trên tập đó rồi thử thêm challenge queries có ground truth hợp lý; không bịa một thất bại.

Phân biệt failure quan sát được và hạn chế dự kiến. Pixel histogram có thể nhầm cùng màu nhưng khác loại; keyword có thể không hiểu synonym hoặc phủ định. Chỉ nêu case cụ thể là kết quả thực nghiệm khi có row/log tương ứng.

Không chọn lại expected labels hoặc chỉ giữ query dễ sau khi nhìn output để tạo success rate đẹp. Nếu điều chỉnh thuật toán, lưu version/config và chạy lại toàn bộ evaluation set liên quan.

## 12. T6 — Demo và bằng chứng chạy thật

### 12.1. Nội dung demo bắt buộc

Chạy tối thiểu ba query trong cùng phiên bản prototype:

| Demo | Input đề xuất | Bằng chứng cần hiển thị |
|---|---|---|
| D1 — Text | `black shoes` | Text gốc, normalized tokens, retrieval/filter, products, score và rank |
| D2 — Voice | `find black running shoes` | Nhãn simulated STT, transcript, common query, products và score |
| D3 — Image | Ảnh sample hoặc vector mô phỏng đã công bố | Encoder hoặc simulation, dimension, cosine, products và score |

Thêm D4 text+image fusion và D5 order lookup ở bản hoàn chỉnh. Nếu query trả no-result ngoài dự kiến, sửa nguyên nhân hoặc báo đúng hạn chế; không thay terminal output bằng văn bản tự viết.

### 12.2. Thu thập artifact

1. Chạy demo thật, lưu stdout vào `artifacts/demo/demo_output.txt` bằng UTF-8.
2. Lưu JSON theo result contract nếu CLI có hỗ trợ.
3. Mở terminal hiển thị lệnh và output thật; chụp các vùng cần thiết có thể đọc score.
4. Có ít nhất screenshot cho text, voice và image; với ảnh nên hiển thị input ảnh gần kết quả nếu phù hợp.
5. Chụp ba diagram trong cửa sổ VP thật, có tên diagram/model đang mở.
6. Đối chiếu screenshot với logs/JSON và report. Không dùng screenshot của phiên bản code cũ cho result mới.

Screenshot terminal/VP không được vẽ giả bằng Pillow hay HTML. Có thể crop ảnh chụp để dễ đọc nhưng giữ bản gốc; không chỉnh sửa nội dung kết quả. Export diagram gọn và screenshot VP là hai loại bằng chứng khác nhau, cần cả hai.

Tên file đề xuất:

```text
artifacts/screenshots/vp_use_case.png
artifacts/screenshots/vp_architecture.png
artifacts/screenshots/vp_sequence.png
artifacts/screenshots/demo_text.png
artifacts/screenshots/demo_voice.png
artifacts/screenshots/demo_image.png
artifacts/screenshots/demo_multimodal.png         # Nếu có extension
```

## 13. Báo cáo PDF LaTeX English chi tiết

### 13.1. Nội dung và phân bổ trang

Cập nhật theo yêu cầu mới của người dùng: source hiện tại là `docs/report.tex`, output là `artifacts/report/Assignment_06_Report.pdf`, toàn bộ nội dung giải thích bằng tiếng Anh, chữ đen trên nền trắng, không giới hạn số trang. Giữ nguyên UML và mọi ảnh đã duyệt. Phần chính giải thích Python; phụ lục chứa đầy đủ mọi file Python, fixtures và cấu hình. `docs/report.md` chỉ hướng dẫn build. Bảng phân bổ trang cũ dưới đây giữ làm tham khảo cấu trúc của đề; không áp đặt page count cho bản hiện tại. Giữ đúng thứ tự 11 phần đề khuyến nghị.

| Trang mục tiêu | Nội dung |
|---|---|
| 1 | Cover: Assignment 06, tên môn, tên đề, thông tin sinh viên được cung cấp, phiên bản |
| 2 | Introduction + Problem Description: mục tiêu, queries, scope prototype |
| 3 | Requirements Analysis: actor, FR/NFR, modalities và outputs |
| 4 | Use Case Model: diagram, quan hệ, mô tả use case chính |
| 5 | Three-Layer Architecture: component diagram và trách nhiệm/dependencies |
| 6 | UML Sequence Diagram: voice flow và note simulated STT |
| 7 | Python Implementation: directory, interfaces, query/result contract, dataset |
| 8 | Multimodal Search Method: keyword score, image encoder, cosine, fusion và ranking |
| 9 | Experimental Results: test set, criterion, bảng result, success rate theo mode |
| 10 | Demonstration: screenshots text/voice/image, input và processing |
| 11 | Discussion: failure quan sát, limitations, khác biệt simulated và real AI |
| 12 | Conclusion, hướng phát triển và references |

Giữ đủ 11 nội dung khuyến nghị của đề: Introduction, Problem Description, Requirements Analysis, Use Case Model, Three-Layer Architecture, UML Sequence Diagram, Python Implementation, Multimodal Search Method, Experimental Results, Discussion, Conclusion.

Thiếu tên/MSSV/class không được bịa. Đọc dữ liệu người dùng đã cung cấp; nếu chưa có, dùng nhãn `Chưa cung cấp` và báo là mục cần bổ sung, vẫn hoàn thiện nội dung kỹ thuật.

### 13.2. Xuất PDF local

Pipeline hiện tại: `scripts/build_report.py` tạo tables từ saved evidence và snapshot nguyên file code, sau đó compile bằng XeLaTeX ba passes. Cần MiKTeX/TeX Live, các packages của source và font Times New Roman/Arial/Consolas. Kiểm tra `build_audit.json`, hash input, 25 ảnh nhúng nguyên pixels, full source inventory, references, text màu đen/fonts/bounds và visual review. Không rerun evaluation hoặc chỉnh UML để build report. Các pipeline khác dưới đây là tham khảo cũ và không thay yêu cầu LaTeX hiện tại.

Agent lựa chọn một pipeline có thể chạy và kiểm chứng, ví dụ:

- Markdown → HTML có print CSS → Chromium/Playwright print PDF local.
- Python ReportLab với Unicode font, image/table layout và page numbering.
- Công cụ Markdown/Pandoc/LaTeX có sẵn nếu kiểm tra được dependency và fonts.

Nếu dùng ReportLab, đăng ký và embed font Unicode hỗ trợ tiếng Việt từ font đã có/quyền dùng phù hợp; không dùng font mặc định thiếu dấu. Nếu dùng HTML, dùng A4 print styles, page breaks có kiểm soát và chờ fonts/images load trước export. Không đưa report/private project lên dịch vụ bên ngoài chỉ để chuyển PDF.

Interface builder mục tiêu:

```powershell
.\.venv\Scripts\python.exe scripts/build_report.py --input docs/report.tex --output artifacts/report/Assignment_06_Report.pdf
```

Builder phải đọc nguồn và artifact thật; không sinh bảng số liệu riêng trái với evaluation CSV. Có thể tạo bảng report tự động từ metrics/results để tránh lệch số liệu.

### 13.3. Review PDF

- Mở PDF bằng trình đọc; đếm trang để kiểm chứng output, không áp đặt giới hạn trang; xác minh 11 phần, mọi ảnh/code và bố cục.
- Render toàn bộ trang để inspect bố cục, đặc biệt trang chứa UML, bảng và screenshot.
- Kiểm tra dấu tiếng Việt, font embedding, clipping, overflow, ảnh mờ và dòng bị cắt.
- Có caption và dẫn chiếu Figure/Table; diagram đủ lớn để đọc tên/mũi tên ở zoom thông thường.
- Công thức cosine và success rate đúng; denominator không bằng 0; số trong report khớp `metrics.json`.
- Giải thích simulation và limitations; không gọi histogram là CLIP hoặc vector index in-memory là vector database.
- Tên Assignment 06 nhất quán; không còn tên Assignment 05 từ ví dụ.
- Screenshot Python và VP có thật, không chỉ dùng diagram export.
- Chỉ dẫn run, dataset và kết quả khớp cùng phiên bản được đóng gói.

## 14. README và đóng gói bài nộp

### 14.1. README bắt buộc

README cung cấp đủ:

1. Tên bài, mục tiêu, ba chế độ và extension thực sự có.
2. Python version đã test, runtime/dev/automation packages được phân biệt.
3. Cài đặt trên Windows từ bản giải nén, dùng `.venv` và dependency manifest.
4. Lệnh chạy `main.py`, ba query mẫu và fusion/order nếu có.
5. Cấu trúc thư mục, dataset schema, nguồn hoặc cách tạo sample images.
6. Cách mở `.vpp` và đường dẫn report.
7. Cách chạy tests/evaluation và vị trí kết quả.
8. Các giới hạn: simulated STT, loại image encoder, không production auth, dataset nhỏ, các modality chưa thực hiện nếu có.

README có thể mô tả output đã kiểm chứng, nhưng không thay thế demo logs. Không yêu cầu người chấm có shortcut Start Menu hoặc đường dẫn cài giống máy này để chạy Python.

### 14.2. Bảy nhóm sản phẩm nộp

| Yêu cầu PDF trang 21 | Artifact trong gói |
|---|---|
| PDF report | `report/Assignment_06_Report.pdf` |
| Visual Paradigm project | `models/Assignment_06_Multimodal_Search.vpp` |
| Python source code | `main.py`, `presentation/`, `application/`, `data/*.py`, scripts cần chạy |
| Product dataset | `data/products.json`, embeddings/index metadata, orders nếu có |
| Sample images | `data/images/` và `data/queries/` |
| README file | `README.md`, requirements manifests |
| Demonstration results | `artifacts/demo/`, screenshots và evaluation results |

Có thể thêm tests và tài liệu thiết kế vào package. Không đưa `.venv`, cache, `.git`, shortcut backup, private settings, plugin API JAR, launcher/executable VP hoặc project bài khác vào ZIP. Không đưa ZIP đầu ra vào chính ZIP đang tạo.

### 14.3. Manifest và validation

Viết `scripts/validate_submission.py` kiểm tra bằng file thật:

- Tồn tại đủ bảy nhóm artifact, các file không rỗng.
- Product count ≥10, unique ids, paths tồn tại, vectors/index khớp encoder/dimension/product ids.
- README/CLI examples trỏ tới sample files có thật.
- Report PDF LaTeX English mở được, không giới hạn trang, đủ ảnh/code; PDF parser không chứng minh bố cục tốt nên vẫn cần inspect ảnh.
- `.vpp` có thật; bước mở lại trong VP được ghi bằng screenshot/progress, không tự suy ra nội dung native từ file size.
- Demo ba modes có inputs/processing/result/scores; evaluation metrics nhất quán với results.
- Tests đã chạy sau lần sửa logic cuối; log/exit code được lưu.
- Kiểm tra manifest SHA-256 cho các file bàn giao; không ghi pass bằng cách hardcode kết quả.

Sau đó tạo ZIP từ staging có danh sách file rõ, ví dụ `submission/staging/Assignment_06/`. Lưu manifest ngoài ZIP và/hoặc một bản bên trong tùy cách kiểm tra, không tạo vòng hash tự tham chiếu.

Lệnh validation mục tiêu:

```powershell
.\.venv\Scripts\python.exe scripts/validate_submission.py --root .
```

### 14.4. Kiểm tra từ bản giải nén

1. Giải nén ZIP vào thư mục kiểm tra riêng trong workspace.
2. Tạo venv mới trong thư mục đó; cài runtime manifest và chạy các lệnh README.
3. Chạy demo đủ ba modes, fusion/order nếu đã công bố. Tránh dùng import path hoặc dataset tuyệt đối của bản source gốc.
4. Xác nhận report, images và `.vpp` có trong ZIP; mở report và kiểm tra model từ bản đã đóng gói.
5. Ghi kết quả smoke test bản giải nén. Nếu phải sửa source, rebuild artifact/ZIP/manifest và kiểm tra phần bị ảnh hưởng.

Không tự push repository cha hoặc nộp LMS. Bàn giao local hoàn chỉnh với đường dẫn cụ thể; chỉ thực hiện việc nộp khi người dùng giao riêng.

## 15. Xử lý lỗi và tiếp tục tự chủ

| Vấn đề | Cách tiếp tục |
|---|---|
| PDF text mất bảng/hình | Render trang, đọc ảnh, ghi trang tham chiếu |
| VP chưa hiện/đang minimized | Tìm lại window, restore/focus đúng phiên, inspect screenshot mới |
| UIA không thấy Java controls | Dùng win32 tìm window, keyboard/menu và screenshot; cân nhắc Open API đã smoke test |
| Screenshot thấy app khác | Loại ảnh khỏi evidence, focus VP rồi chụp lại đúng region |
| Shortcut Access Denied | Giữ backup; dùng executable đã xác minh/phiên đang mở; ghi rõ thay đổi shortcut chưa thực hiện |
| Plugin không load/bytecode sai | Đọc log/runtime/API signatures, sửa một nguyên nhân; nếu không khả thi dùng GUI |
| Save dialog/path sai | Cancel thao tác chưa xác minh, inspect dialog; paste absolute path; kiểm tra file sau save |
| VP bị treo | Save nếu còn đáp ứng; giữ backup; khôi phục checkpoint. Không kill ứng dụng chỉ vì thao tác chậm |
| Image/index không khớp | Validate encoder/version/hash/dimension, rebuild đúng index rồi chạy lại tests |
| Search trả sai product | Đối chiếu query tokens, filters, candidate set và score components; sửa pipeline, không sửa output giả |
| Report lỗi font/bố cục | Đổi font Unicode/layout, render lại những trang bị ảnh hưởng và kiểm tra PDF cuối |
| Dependency/model ngoài chưa có | Hoàn thiện baseline offline; extension chỉ triển khai khi khả thi và được mô tả đúng |

Giới hạn ba lần thử cùng một thao tác GUI không có tiến triển; sau đó thay locator, inspect trạng thái hoặc đổi phương pháp. Mỗi retry phải có giả thuyết và bằng chứng mới. Thời gian chờ có timeout; không treo phiên vô hạn hoặc tự lặp tới khi hết budget.

Nếu một deliverable bắt buộc vẫn bị chặn, tiếp tục hoàn thiện các phần độc lập, lưu `BLOCKED` với lỗi chính xác và bước cần người dùng can thiệp. Không đánh dấu toàn bộ bài hoàn thành khi `.vpp`, một modality hoặc report còn thiếu.

Trong lượt thực thi, cập nhật ngắn bằng tiếng Việt ở mỗi mốc hoặc sau khoảng một phút làm việc dài: điều đã xác minh, việc đang làm và điểm còn thiếu. Khi người dùng hỏi trạng thái hoặc điều chỉnh phạm vi, phản hồi và cập nhật công việc, giữ mục tiêu ban đầu trừ khi họ yêu cầu dừng/thay thế.

## 16. Definition of Done — chỉ kết thúc khi kiểm tra đủ

### 16.1. Analysis và UML

- [ ] Đã đọc đủ 23 trang PDF; các điểm chưa thống nhất được xử lý có dẫn trang.
- [ ] T1 có actors, ≥5 FR, NFR, input modalities và outputs.
- [ ] Use Case có Customer và đủ 7 use cases; relationship đúng ý nghĩa.
- [ ] Component Diagram có ba package và các component/storage cần thiết.
- [ ] Dependencies không có Presentation → Data.
- [ ] Sequence voice có đủ 7 participants, transcribe/query/retrieve/rank/display.
- [ ] `.vpp` đã save và mở lại; diagram/model elements sửa được native.
- [ ] Có ba diagram exports và screenshot VP thật.
- [ ] UML, method names và code cuối thống nhất qua traceability.

### 16.2. Prototype và đánh giá

- [ ] Source theo ba tầng; `main.py` làm composition root.
- [ ] Dataset ≥10 products, images/metadata/index hợp lệ.
- [ ] Text search chạy được và có xử lý input không hợp lệ/no-match.
- [ ] Voice mô phỏng chạy qua SpeechService và được công bố rõ.
- [ ] Image cosine search chạy được; phân biệt artificial vector và pixel encoder.
- [ ] Query contract chung và RankingService riêng thực sự được sử dụng.
- [ ] Final scores giảm dần, top-k đúng, tie-break ổn định.
- [ ] Demo text/voice/image có input, processing, products và ranking scores.
- [ ] Bản hoàn chỉnh có fusion, filter/order nếu được công bố; hoặc ghi rõ extension chưa thực hiện.
- [ ] Tests quan trọng pass; lỗi không bị che bằng skip hoặc fake assertion.
- [ ] Evaluation có total/success/success rate và breakdown, ground truth định nghĩa trước.
- [ ] Có phân tích failure quan sát hoặc ghi rõ chưa có failure trong tập đã test.

### 16.3. Báo cáo và bàn giao

- [ ] Report PDF LaTeX English chữ đen/trắng, không giới hạn trang, đủ 11 phần/ảnh/full Python code và font/ảnh/bảng đọc được.
- [ ] Report có screenshot VP và Python chạy thật; số liệu khớp logs/metrics.
- [ ] README có Python/packages/run/structure/examples/limitations.
- [ ] Có đủ bảy nhóm sản phẩm bài nộp.
- [ ] ZIP không chứa môi trường, backup hoặc file riêng ngoài phạm vi.
- [ ] Manifest/validation kiểm tra artifact thật; smoke test bản giải nén đạt.
- [ ] Nêu rõ các thông tin sinh viên chưa cung cấp; không khai đã nộp LMS.

Nếu chỉ hoàn tất V01 baseline, ghi rõ mốc và phần còn lại, không đánh đồng với Definition of Done cho bản hoàn chỉnh. Trạng thái cuối dựa trên tiêu chí đạt được, không dựa trên thời gian/token còn lại.

## 17. Cách Agent báo kết quả cuối

Trả lời ngắn, dễ kiểm tra, gồm:

1. Các task đã hoàn thành và extension đã thực hiện.
2. Link local đến PDF report, `.vpp`, ZIP và README.
3. Kết quả test/evaluation **thực tế** với số lượng, success criterion và tỷ lệ.
4. Shortcut có được sửa hay không; nếu sửa, nêu fields và backup path. Không mô tả quyền sửa như một thay đổi đã làm.
5. Phần chưa hoàn thành hoặc thông tin cần bổ sung, nếu có.

Ví dụ cấu trúc câu, các chỗ trong ngoặc phải lấy từ artifact đã kiểm chứng:

```text
Đã hoàn thành [tasks]. Sản phẩm: [report], [project VP], [ZIP], [README].
Kiểm tra: [số tests pass], [query thành công]/[tổng query],
[success rate theo criterion đã công bố].
Visual Paradigm: đã mở lại project và kiểm tra ba diagram native.
Shortcut: [giữ nguyên vì hợp lệ / đã sửa fields cụ thể và có backup].
Còn thiếu: [nếu có]; trạng thái nộp LMS: chưa nộp hoặc trạng thái đã được xác minh.
```

Trước báo cuối, tự rà soát accuracy, completeness, clarity, actionability và conciseness bằng bằng chứng cụ thể. Nếu còn gap sửa được, sửa và kiểm tra lại thay vì chỉ viết khuyến nghị. Không tự chấm tất cả 5/5 khi chưa kiểm chứng file, code, diagram và report.

## 18. Nguồn tham khảo của guide

- [PDF đề bài trong workspace](../storage/inf_sys_analysis_design_assignment_06_design_code.pdf): nguồn yêu cầu, task, report, bài nộp và rubric.
- [Visual Paradigm CE — Free UML Design Tool](https://s.visual-paradigm.com/solution/freeumldesigntool/): phạm vi UML của Community Edition.
- [Implementing Visual Paradigm Plugin](https://www.visual-paradigm.com/support/documents/pluginuserguide/2186/2188/57181_implementing.html): vị trí API JAR và cấu trúc plugin.
- [Installing Visual Paradigm Plugin](https://circle.visual-paradigm.com/docs/open-api/installing-plug-in/installing-a-visual-paradigm-plug-in/): cài folder/ZIP, restart và dependency API.
- [Exporting Active Diagram as Image](https://circle.visual-paradigm.com/docs/export-and-import/export-as-images/exporting-active-diagram-as-image/): export diagram để đưa vào report.

Các kế hoạch dataset, interface, test, encoder, extension và phân bổ trang trong guide là đề xuất triển khai dựa trên PDF; chúng chưa phải số liệu chạy thử hoặc artifact bài tập đã hoàn thành.
