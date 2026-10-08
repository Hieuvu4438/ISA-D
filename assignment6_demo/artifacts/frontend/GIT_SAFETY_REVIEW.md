# Kiểm tra inventory trước khi commit

Kiểm tra read-only ngày 2026-10-08, phạm vi `assignment6_demo`. Không stage, commit, push; không đọc nội dung `.env`, không thay đổi ảnh ngoài phạm vi dự án.

## Bằng chứng hiện tại

- Inventory có 747 paths chưa track tại thời điểm kiểm tra. `.agent` và `.agents` chứa hai bản tooling skills: 310 files và khoảng 4.51 MiB mỗi bản. Đây là source tooling, không phải model/runtime hoặc dữ liệu sản phẩm.
- Quét 729 files UTF-8 ngoài các file env; không có match của các mẫu credential rõ ràng: Azure Speech key assignment dài, GitHub token, private key, OpenAI secret và URL chứa username/password. Chỉ báo kết quả và filenames, không in giá trị credential.
- File chưa track lớn nhất là `data/queries/Q001.jpg`, khoảng 1.08 MiB; đây là ảnh query fixture.
- `git check-ignore -v` xác nhận `.env`, `backend/.venv/`, `runtime/`, `frontend/node_modules/` và `frontend/dist/index.html` được ignore.
- `runtime/` chứa 657 files, khoảng 1814.88 MiB tại thời điểm kiểm tra. Model/runtime artifacts cần tiếp tục nằm ngoài Git.

## Các files sinh ra cần loại khỏi commit

Tại thời điểm kiểm tra, các paths sau chưa có rule ignore:

```gitignore
frontend/test-results/
frontend/playwright-report/
artifacts/backend/coverage.sqlite
```

`coverage.sqlite` là database coverage sinh tự động, chứa 16 đường dẫn tuyệt đối của môi trường local. Nên giữ báo cáo coverage JSON/tóm tắt cần bàn giao thay vì database này. Playwright test-results và report có thể chứa video, trace, screenshot và request capture; giữ chúng local, chỉ chọn evidence đã kiểm tra để đưa vào `artifacts/` nếu cần bàn giao.

Kiểm tra pattern không chứng minh mọi loại secret đều vắng mặt. Nội dung env không nằm trong phép quét; `.env.example` cần giữ các credential values trống khi người phụ trách staging kiểm tra template. Hai thư mục skills chưa được coi là bí mật hoặc bắt buộc loại bỏ; người phụ trách commit quyết định giữ source tooling theo phạm vi người dùng đã yêu cầu.
