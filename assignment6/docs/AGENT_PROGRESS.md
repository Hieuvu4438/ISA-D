# Tiến độ thực hiện Assignment 06

Ngày thực hiện: 01/10/2026. Phạm vi: guide → 6 task → native UML → Python prototype → thực nghiệm → báo cáo → ZIP.

## Phân công

Tối đa 3 agent: root tích hợp/desktop/VP/nghiệm thu; prototype phụ trách code/dataset/tests/evaluation và package; report phụ trách tài liệu/báo cáo. Không push, không nộp LMS, không sửa bài khác.

## Các mốc đã kiểm chứng

- M0: đọc PDF đề 23 trang; đối chiếu guide. Workspace nằm trong repo cha ISA-D. Shortcut VP target hợp lệ, không cần sửa.
- M1: frozen ground truth được định nghĩa trước implementation. RED ban đầu 9 failed, 1 passed, 32 errors; checkpoint local git 575e3c9. GREEN ban đầu 74 tests checkpoint 45bfc4e; các boundary/percentile tests bổ sung theo RED/GREEN riêng.
- M2: giữ project VP ban đầu có unsaved changes; Save As snapshot thành công sau dialog trì hoãn tại artifacts/backups/baikiemtra01-unsaved-snapshot-20261001.vpp. Không overwrite original. Thông báo local repository version mới hơn đã được xử lý; không discard phiên gốc.
- M3: prototype có 12 sản phẩm, 12 ảnh Pillow original, 3 query images biến đổi, text/voice/image/fusion, filter giá/category, order customer scope. Retrieval và ranking tách riêng, common query; pixel encoder88D và cosine thật.
- M4: tạo native VP CE18 project models/Assignment_06_Multimodal_Search.vpp bằng Open API. 7 use cases, 3 generalizations, 4 actor associations; 3 packages với 16 components; voice sequence 7participants/14messages. Đã sửa hướng generalization theo API và đường nối để hình đúng nghĩa. GUI mở cả3diagram, lưu caption/layout patch; chụp screenshots thật. Project đóng để giải phóng lock rồi API mở lại file đã lưu thành công,3diagrams, export lại PNG. model_inventory/reopened_inventory/verify_result là evidence cuối. Một verify thử khi GUI đang giữ file đã bị VP từ chối; chỉ process API riêng bị dừng, verification sau khi đóng GUI PASS.
- M5: root final pytest78PASS (2.62s), application/data coverage100%264statements. RuffPASS, pyright0errors, compileallPASS, pipcheckPASS, pip-audit no known vulnerabilities sau khi nâng pip trong .venv. Không thay systemPython.
- M6: evaluation primary12/12, extension2/2, challenge0/2, robustness5/5; denominator riêng, groundtruthSHA256 đối chiếu. Giữ failures synonyms/negation thật. Không suy diễn100% trên ảnh thực.
- M7: demo screenshots được chụp từ cửa sổ Python đọc outputCLIJSON vừa chạy; payload lưu kèm. Reportbuilder đọc metrics/tests/demo thật, báo cáo12trang, có 3 UMLexports+3VPscreenshots+3Python screenshots. Renderreview do reportworker và root thực hiện trước bàn giao.

## Nghiệm thu và bàn giao

Kết quả gate cuối và clean ZIP extraction được ghi bởi scripts/package_submission.py trong docs/FINAL_VERIFICATION.md, artifacts/tests/submission_validation.json và clean_extraction.json. ZIP/manifest được tạo sau khi PDF và tài liệu đã freeze; chỉ file Assignment06, không kèm .venv/backup/VPseed/workspace/ảnh bài khác. Goal chỉ complete sau khi ZIP/hash/review cuối đạt.

Sinh viên/MSSV/lớp: Chưa cung cấp. Voice mô phỏng STT; synthetic images/pixel descriptor; order context không phải production authentication. Chưa nộp LMS.
