# Kế hoạch bàn giao cho AI Agent implement

**Trạng thái triển khai Cortis:** M0 backend, M1 data, M2 model/index CPU thật, M3 API và M5 Azure adapter đã triển khai và kiểm tra. Backend đạt 85 tests, coverage 87,3% và 45 HTTP checks; evidence ở `artifacts/backend/RUN_REPORT.md`. Người dùng đã yêu cầu frontend đầy đủ: M4 đã có giao diện showroom bằng code, build/typecheck và 17 tests đạt; browser verification đang chạy. M6 cần công khai từng gate đã đo và còn thiếu. Azure live cần key trong environment và kiểm tra riêng, chưa nghiệm thu bằng stub. Lệnh backend ở [BACKEND_QUICKSTART.md](BACKEND_QUICKSTART.md), frontend ở [README](../README.md).

## Hợp đồng của Agent

1. Chỉ đọc/ghi sản phẩm triển khai trong `assignment6_demo/`. Không sửa prototype `assignment6/`, cấu hình người dùng hoặc thư mục khác để làm demo mới chạy.
2. Đọc [README](README.md), 01–08 rồi đọc 09–12. Các hợp đồng dữ liệu, toán, API, UI và bảo mật là acceptance criteria, không phải gợi ý tùy chọn.
3. Dùng ảnh chụp sản phẩm thật đã lấy từ mạng, có nguồn và giấy phép trong manifest. Không dùng image generation, hình placeholder làm sản phẩm thật, hoặc ảnh synthetic từ prototype cũ.
4. Không đưa Azure key vào code, Markdown, fixture, Git, URL hoặc bundle frontend. Dùng environment phía backend; `southeastasia`, `vi-VN`. Region đã được chuẩn hóa từ câu trả lời của người dùng; live smoke mới xác nhận resource thực tế.
5. Semantic search phải chạy model CPU thật. Mock chỉ dùng unit/integration để cô lập dependency, ghi rõ trong evidence. Transcript nhập tay có nhãn mô phỏng và không thay gate Azure thật.
6. Không gọi Azure trong startup, build index, CI hoặc test mặc định. Gate live chỉ chạy thủ công với quyền sử dụng dịch vụ đã được xác nhận và giới hạn số lượt rõ ràng.
7. Thay đổi hợp đồng phải cập nhật đồng thời đặc tả liên quan và test. Không âm thầm giảm scope order, multimodal, relevant hoặc ảnh thật vì khó implement.
8. Kết thúc mỗi milestone bằng artifact có thể review: diff, lệnh đã chạy, kết quả thực tế, pending và cách tái hiện. Không ghi “passed” nếu mới chỉ mô tả test.

## Cây file đích

Đây là **cấu trúc cần xây dựng**, không phải danh sách file đã tồn tại. Có thể tách thêm module khi trách nhiệm rõ; giữ tên CLI và entrypoint để runbook còn dùng được.

```text
assignment6_demo/
  README.md                       # Quickstart + trạng thái thực tế
  .gitignore                      # .venv, node_modules, .env, uploads, artifacts nhạy cảm
  .env.example                    # Chỉ tên biến và giá trị không nhạy cảm
  docs/                           # Bộ đặc tả hiện tại
  data/
    products.json
    orders.json
    image_sources.json
    images/P001.jpg ... P012.jpg   # Ảnh thật, ID khớp seed
    queries/                      # Query image thật, nguồn riêng theo 05
  evaluation/
    queries.json                  # 60 cases calibration/test frozen theo 05
    voice_cases.json              # 5 live WAV cases, ngoài offline60
  backend/
    pyproject.toml
    requirements.lock             # Versions chính xác, CPU torch, kiểm tra Windows
    app/
      main.py                     # Composition root, lifespan, FastAPI
      settings.py
      domain/                     # DTO/protocol/lỗi; không import framework/SDK
      presentation/               # API adapters, validation, error handlers
      application/
        query_service.py
        embedding_service.py
        image_service.py
        speech_service.py
        search_service.py
        ranking_service.py
        order_service.py
      data/
        product_repository.py
        order_repository.py
        vector_index.py
        image_storage.py
    tests/
      unit/
      integration/
      architecture/
  frontend/
    package.json
    package-lock.json
    src/
      api/                        # Một API client, AbortController/request ID
      pages/                      # Search, ProductDetail, OrderLookup, OrderDetail, Credits
      components/                 # Query forms, filters, result grid, trace, states
      hooks/                      # Search lifecycle, mic capture, transcript state
      types/                      # Wire DTO theo 06
    tests/
    playwright.config.ts
  scripts/
    download_models.py
    validate_dataset.py
    build_index.py
    calibrate_thresholds.py
    evaluate.py
    verify_contracts.py
    benchmark.py
    verify_speech_live.py
  runtime/
    models/                       # Snapshots model pinned; không frontend public
    index/                        # NPZ + manifest/policy validated
    policies/                     # Threshold policies gắn fingerprint
  artifacts/
    validation/
    evaluation/
    performance/
    e2e/
    demo/
```

Không dùng `.env.example` chứa key đã được người dùng gửi. Dữ liệu upload request không được lưu vào `data/images` hoặc một route public. `artifacts` chỉ chứa evidence đã được loại secrets và nội dung cá nhân.

## Milestones và gate

| Mốc | Việc phải xây dựng | Hợp đồng/đầu ra | Gate trước mốc tiếp theo |
| --- | --- | --- | --- |
| M0 — Foundation | Kiểm tra Python 3.12, Node 22 ≥22.12; scaffold; dependency lock; env example; cấu hình CORS/proxy; error DTO | Backend entrypoint, frontend shell tiếng Việt, scripts có help và exit code | Install sạch bằng lock; health live; frontend build/typecheck; không chứa key |
| M1 — Dataset và Data | Validate product/order/source schema, ảnh local, giá VND, ownership C001/C002; repository immutable; static image route allowlist | 04; seed ≥12 sản phẩm thật; lookup không cần encoder | AC-024–028, 037, 042; mọi asset decode và SHA khớp manifest |
| M2 — AI/index | Download đúng hai commit; CPU text/image unit vectors 512D; product fusion; fingerprint; builder lock + atomic publish; loader corruption/stale checks | 05; index thật + manifest; không network khi request/startup | AC-012, 016, 019–022, 031, 038; model smoke thật, không dùng vector random để pass |
| M3 — Search API | Text/image/multimodal, hard filters, rank stable, Top-k cuối, nearest/relevant, trace/error/readiness | 06; OpenAPI và sample payload thống nhất | AC-001–005, 013–018, 030, 040, 043; integration dùng adversarial candidates |
| M4 — Web core | Modes, filter, results/detail/back, orders, credits, loading/empty/error; pending changes và stale-response guard | 07; browser 360/768/1440, giữ query state | AC-023–029, 040; E2E thật qua HTTP, kể cả direct reload |
| M5 — Voice | WebAudio WAV PCM16 mono 16k; upload; Azure adapter; deadline/no-match mapping; transcript sửa/xác nhận; manual mode có nhãn | 08; tách STT khỏi search; thiếu key chỉ làm voice unavailable | AC-006–011, 028, 041; SDK fake cho test lỗi, live gate để cuối |
| M6 — Quality và handoff | Frozen splits; calibration; test evaluation; benchmark; full E2E; live Speech có giới hạn; UML mapping; README/runbook | 10–12; reports có revisions và dataset hashes | Tất cả gate bắt buộc ở 10; bất kỳ gate thật pending thì website chưa nghiệm thu |

M1 và frontend skeleton có thể làm song song sau M0. M2 và UI components có thể song song nếu DTO ở 06 đã khóa. Không để frontend tự invent response hoặc fallback kết quả hardcoded. Khi dùng workers, phân quyền file rõ, không revert thay đổi của worker khác.

## Hợp đồng CLI cần implement

Tất cả script chạy với Python của `backend/.venv`, working directory là `assignment6_demo`, paths resolve từ project root, không phụ thuộc shell hiện tại. `--help` không download model hay gọi Azure. Thành công exit `0`; input/config/gate fail exit khác `0` kèm thông báo hữu ích.

| Script | Chức năng/đầu ra bắt buộc |
| --- | --- |
| `download_models.py` | Download text `sentence-transformers/clip-ViT-B-32-multilingual-v1@58edf8cada9e398793dca955574a48cbb7f18be2`, image `sentence-transformers/clip-ViT-B-32@327ab6726d33c0e22f920c83f2ff9e4bd38ca37f`; snapshots local, không dùng `main/latest` |
| `validate_dataset.py` | Parse 04; ảnh decode/hash/provenance; order refs/tổng tiền; tạo report ở `artifacts/validation`; không inference |
| `build_index.py` | Dùng model local và snapshot data; encode sản phẩm, write temp, validate, atomic publish; một builder; failure giữ index trước |
| `calibrate_thresholds.py --split calibration` | Chỉ đọc calibration và model/index fingerprint; chọn policy theo 05; lưu threshold report + policy hợp lệ hoặc fail |
| `evaluate.py --split test` | Read-only frozen test; Hit@3/OOD từng mode, raw ranks/scores và IDs; không tự sửa policy/nhãn; exit fail nếu gate không đạt |
| `verify_contracts.py` | Kiểm tra schema/traceability/API examples/index-policy fingerprints theo 04–06; không giả lập bằng cách chỉ tìm tên file |
| `benchmark.py --requests-per-mode 30` | Chạy HTTP warm text/image/multimodal, ghi p50/p95, cold start riêng, machine metadata; lỗi API được tính/report, không bỏ mẫu xấu |
| `verify_speech_live.py --max-calls 5 --confirm-live` | Chỉ chạy khi cờ xác nhận có mặt; fixture vi-VN theo 08/10; không retry tự động vượt 5 lời gọi; report loại secrets. Thiếu key/network thì fail rõ, không chuyển sang mock |

`benchmark.py` và `verify_speech_live.py` cần thêm `--base-url` default `http://127.0.0.1:8000`. Fixtures: `evaluation/queries.json` và `evaluation/voice_cases.json`; ảnh query nằm ở `data/queries` có nguồn trong manifest. `runtime/models/model_manifest.json` ghi model snapshots đã dùng. Cài package backend editable để scripts import `app`; không sửa `sys.path` ad hoc theo cwd. Không tạo bộ label khác cho mỗi script.

## Prompt triển khai có thể dùng sau review

> Implement website trong `assignment6_demo` theo docs/01–12. Đọc hợp đồng 04–08 trước khi viết code. Dùng Python 3.12/FastAPI, React TypeScript/Vite, CPU CLIP aligned 512D theo revisions ở 05, Azure Speech vi-VN region southeastasia từ backend environment. Catalog phải giữ ảnh chụp thật trên mạng và attribution. Thực hiện M0→M6, giữ Search Order/View Order scoped C001 và text/image/voice/multimodal. Không dùng dữ liệu fake để pass integration live/model gate. Chạy verification thích hợp, ghi evidence và pending vào báo cáo. Live Azure cần quyền sử dụng và giới hạn 5 calls; không gọi trong CI/startup. Khi thiếu dependency, UI báo capability unavailable và report website chưa đạt gate đó. Không sửa ngoài assignment6_demo.

## Checklist của bước triển khai

- [ ] M0: scaffold, dependency locks và smoke install sạch.
- [ ] M1: seed/provenance/repositories/static route đạt gate.
- [ ] M2: model pair CPU/index/calibration infrastructure thật.
- [ ] M3: API đúng DTO, ranking/errors/concurrency.
- [ ] M4: UI tiếng Việt/E2E cả search và order.
- [ ] M5: capture/transcription/confirm flow không lẫn mock với Azure.
- [ ] M6: quality, latency, live voice, bảo mật và artifacts demo đạt [10](10_TESTING_ACCEPTANCE.md).

Các checkbox cố ý để trống: bộ đặc tả hiện tại chưa phải bằng chứng implement.
