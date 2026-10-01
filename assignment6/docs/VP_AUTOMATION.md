# Visual Paradigm native — tái lập và kiểm chứng

Project chính: `models/Assignment_06_Multimodal_Search.vpp`, tạo bằng Visual Paradigm CE 18 Open API, gồm use case, component và voice sequence. Actor/use cases/packages/components/generalizations/dependencies/lifelines/activations/messages là model object native có thể sửa trong VP; các PNG là export của project, không phải ảnh thay thế model.

## Mở và chỉnh sửa

Mở Visual Paradigm → Project → Open → chọn `.vpp` trên. View → Project Browser hiển thị ba diagram; double-click thumbnail để mở. Nếu VP báo Diagram Patched khi mở lần đầu, ứng dụng điều chỉnh caption/layout; lưu bằng Ctrl+S. View → Zoom Out và scrollbar giúp nhìn đủ sơ đồ. GUI đã mở đủ ba sơ đồ, chụp các file `artifacts/screenshots/vp_*.png`, lưu project và đóng project trước khi kiểm tra lại bằng API.

Shortcut hiện có `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Visual Paradigm CE\Visual Paradigm 18.0.lnk` trỏ đúng ứng dụng đã cài; không cần sửa shortcut để tạo model. Không thay đổi shortcut, credentials hay license. Project đang mở trước nhiệm vụ được Save As vào `artifacts/backups/baikiemtra01-unsaved-snapshot-20261001.vpp`; bản này giữ tại máy, không đưa vào ZIP.

## Chỉnh màu và đường nối trên project hiện có

Theo yêu cầu cập nhật của người dùng, giữ màu mặc định VP đang dùng. Refiner tạo model element tạm bằng factory của VP để lấy fill/outline/font style, áp dụng cho đúng loại shape rồi xóa các probe. Default quan sát tại máy này là nền `#7ACFF5`, chữ và nét `#000000`; đây là màu lấy từ VP, không phải palette tự chọn. Không đổi loại quan hệ, hướng generalization/dependency hoặc nội dung message.

Đóng project trong GUI rồi chạy:

```powershell
.\.venv\Scripts\python.exe scripts/desktop/run_vp_plugin.py refine --project models/Assignment_06_Multimodal_Search.vpp
.\.venv\Scripts\python.exe scripts/desktop/run_vp_plugin.py verify --project models/Assignment_06_Multimodal_Search.vpp
.\.venv\Scripts\python.exe scripts/verify_uml_layout.py
```

`refine` chỉnh native project hiện có; lưu bản sao trước khi dùng với chỉnh sửa riêng. Use case/component có đường nối góc vuông, điểm bám và hành lang riêng. Sequence giữ thứ tự 14 message, đường ngang và self-call góc vuông. Rendering phải chạy **trước lần lưu cuối** để VP materialize connector bounds; nếu lưu trước rendering, arrow có thể bị clipping khi mở lại dù connector tồn tại trong inventory. Vì vậy luôn kiểm tra trong một process `verify` độc lập và mở lại GUI sau refinement.

`artifacts/tests/uml_layout_audit.json` kiểm tra màu, hướng ngang/dọc, số object và giao cắt/chồng nét/đi xuyên node ở use case và component. Lifeline giao message trong sequence là notation hợp lệ, không tính là lỗi. Bản review lần này đối chiếu IDs/nội dung với inventory trước refinement và xác nhận UML semantics giữ nguyên.

## Tái tạo toàn bộ model

Windows prerequisites: Python 3.12+, JDK có `javac` trên PATH, VP CE 18 tại `C:\Program Files\Visual Paradigm CE 18.0`; plugin compile với `lib/openapi.jar` của chính phần mềm. Script dùng Java bundled của VP. Cài dependencies automation nếu muốn chụp demo:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-automation.txt
.\.venv\Scripts\python.exe scripts/desktop/run_vp_plugin.py build
```

Lệnh build **ghi lại project Assignment 06 và ba PNG**; lưu bản sửa của bạn trước khi rebuild. Launcher copy seed local vào `artifacts/automation/launch_seed.vpp`, dùng workspace riêng và chỉ cài plugin riêng `assignment06-multimodal-builder` dưới `%APPDATA%\VisualParadigm\plugins`. Không sửa các plugin khác. Plugin chỉ chạy khi command-line invocation yêu cầu; `loaded()` không tự sửa GUI. Source Java/XML có trong `scripts/desktop/vp_plugin/`; không phân phối thư viện VP hay seed của phần mềm.

Đóng project Assignment 06 trong GUI bằng Project → Close trước khi chạy verification để giải phóng file lock (không cần đóng ứng dụng):

```powershell
.\.venv\Scripts\python.exe scripts/desktop/run_vp_plugin.py verify --project models/Assignment_06_Multimodal_Search.vpp
```

Verifier thực sự mở native project trong process riêng, kiểm tra ba diagrams, xuất lại PNG từ model đã mở và ghi `artifacts/automation/reopened_inventory.json`, `verify_result.txt`. Launcher yêu cầu marker được ghi mới, không dùng marker cũ để tuyên bố PASS. VP startup có thể mất khoảng một phút và có warnings Java preferences/reflective access; marker và exit code mới là bằng chứng. Không chạy nhiều API process trên cùng workspace/project và không chạy verify khi GUI đang khóa file.

## Minh chứng Python

```powershell
.\.venv\Scripts\python.exe scripts/desktop/capture_demo.py text
.\.venv\Scripts\python.exe scripts/desktop/capture_demo.py voice
.\.venv\Scripts\python.exe scripts/desktop/capture_demo.py image
.\.venv\Scripts\python.exe scripts/desktop/capture_demo.py multimodal
```

Mỗi lệnh thực thi `main.py --mode ... --top-k 3 --json`, đưa **JSON vừa trả về** vào viewer Tkinter rồi chụp cửa sổ thật. Viewer chỉ định dạng input, processing và score để đọc rõ trong báo cáo; không thay thuật toán hoặc kết quả. Đường dẫn input ảnh hiển thị tương đối workspace. `demo_*_payload.json` giữ output gốc để đối chiếu. GUI screenshot cần desktop interactive không bị màn hình khác che; các lệnh capture phải chạy tuần tự.
