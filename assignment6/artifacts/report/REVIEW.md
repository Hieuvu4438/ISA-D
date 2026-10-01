# Kiểm tra báo cáo PDF — hoàn tất

Artifact: `artifacts/report/Assignment_06_Report.pdf`. Nguồn: `docs/report.md`; builder: `scripts/build_report.py`. Lệnh build đã chạy exit 0:

```powershell
.\.venv\Scripts\python.exe scripts/build_report.py --input docs/report.md --output artifacts/report/Assignment_06_Report.pdf
```

## Bằng chứng và kết quả

- PDF mở được và có đúng **12 trang A4**: cover + đủ 11 nội dung khuyến nghị, thêm demonstration riêng ở trang 10.
- Đã xem trực quan tất cả 12 ảnh render `review_pages/page_01.png`–`page_12.png`. Sau tăng kích thước UML, spacing evaluation và sửa image path/captions, xem lại các trang 5, 6, 8, 9, 10 của bản final. Không thấy clipping/overflow, thiếu dấu tiếng Việt, captions tách sai hoặc ảnh bị cắt.
- Arial regular/bold/italic được nhúng. Fonts thực sự dùng trong text spans đều là Arial; Helvetica chỉ là resource mặc định không dùng để vẽ nội dung. Text geometry không ra ngoài safe bounds; footer còn nằm trong trang.
- Component/sequence exports được mở rộng tới full available width; những diagram nhiều participants vẫn cần zoom để xem notation nhỏ. File PNG gốc và project native được bàn giao để kiểm tra chi tiết. VP screenshots chứng minh ứng dụng; diagram exports cung cấp hình lớn để đọc nội dung.
- Trang 7 đọc JUnit/coverage thật: **78/78 tests**, failures/errors/skipped = 0; line coverage **100% / 264 statements Application và Data**. Không claim branch coverage hay coverage UI/VP.
- Trang 9 đọc metrics/results thật: primary **12/12**, từng text/voice/image **4/4**; extension **2/2**, challenge **0/2**, robustness **5/5**. Metrics đối chiếu theo group/mode, không nhầm baseline 12 với toàn bộ 21 result rows.
- Timing final: mean **1.289 ms**, p95/max **6.615 ms**, services/index startup excluded. P95 dùng nearest-rank trong evaluation; đây là sample local nhỏ, không load benchmark.
- Trang 10 dùng screenshots thật của **Python result viewer nhận JSON từ fresh CLI process**; captions mô tả đúng viewer, không gọi là terminal. Top-2 summary lấy từ demo JSON; viewer hiển thị top-k=3 cho dễ đọc. Image path chỉ rút gọn khi hiển thị report, không sửa artifacts gốc.
- Trang 11 phân tích failures thật C01 `sneakers` → no-match; C02 `shoes not black` → black product id 1. Simulation/handcrafted descriptors/synthetic data/context privacy được ghi rõ.
- Builder lint và py_compile pass; artifacts/dependencies thiếu bị từ chối, không tạo fake metrics/images. `build_audit.json` ghi hashes đầu vào/PDF, page sizes, fonts, data checks và bounds để kiểm tra trạng thái đã review.

## Tự đánh giá theo agent-self-evaluation

Skill sử dụng: `C:/Users/Hieu Vu/.codex/skills/agent-self-evaluation/SKILL.md`.

| Trục | Điểm | Bằng chứng và điều có thể cải thiện |
|---|---:|---|
| Accuracy | 4/5 | Metrics/JUnit/coverage đọc và đối chiếu từ artifacts, captions viewer chính xác; benchmark local nhỏ nên không suy rộng chất lượng production |
| Completeness | 4/5 | Đủ 12 trang/11 nội dung, UML/screenshots/demos/results/limitations; thông tin sinh viên vẫn Chưa cung cấp vì chưa có dữ liệu hợp lệ |
| Clarity | 4/5 | Tables, captions, font tiếng Việt và full-page review rõ; sequence nhiều participants cần zoom để đọc nhỏ |
| Actionability | 5/5 | Command build hoạt động, PDF final có thật, markdown/scripts/evidence sẵn bàn giao |
| Conciseness | 4/5 | Duy trì 12 trang theo đề, không đưa full logs vào report; vài thuật ngữ English được giữ để khớp UML/source |

Trung bình: **4.2/5**. Đánh giá này phù hợp đầu ra người dùng có thể kiểm tra; không phải điểm rubric của giảng viên.

Cải thiện ưu tiên: (1) điền họ tên/MSSV/lớp sau khi người dùng cung cấp; (2) khi cần đọc notation nhỏ, mở original exports hoặc native VP; (3) mở rộng independent query dataset cho nghiên cứu tiếp, không phải blocker bài prototype hiện tại. Không có lỗi layout còn cần sửa trong phạm vi report worker.

Trạng thái: **report/docs frozen để đóng gói**. Nếu source, metrics, images hoặc report thay đổi, rebuild PDF và review các trang bị ảnh hưởng trước cập nhật package/hash.
# Review sau chỉnh UML theo người dùng — 2026-10-01

Root đã rebuild báo cáo 12 trang với diagram exports và screenshots mới từ native VP đã lưu/mở lại. Đã xem trực tiếp các trang bị ảnh hưởng 4, 5, 6: đủ actors/use cases, ba tầng/16 components/15 dependencies và 14 sequence messages; default cyan của VP cùng chữ/nét đen, đường ngang/dọc tách biệt, không bị cắt hình hay tràn trang. Screenshot VP xác nhận connector hiện đủ sau reopen. Nội dung report, số liệu, demo và các trang còn lại giữ nguyên nguồn.

`build_audit.json` đã kiểm tra lại SHA-256 của toàn bộ đầu vào/PDF, 12 trang A4, font Arial tiếng Việt nhúng, text bounds và các số liệu trong PDF. Notation nhỏ ở component/sequence vẫn nên xem trong PNG gốc hoặc zoom native VP.
