# Kiểm thử và điều kiện nghiệm thu

**Trạng thái hiện tại:** backend CPU và frontend Cortis chạy với 60 sản phẩm/12 danh mục và 30 đơn. Backend có 103 tests đạt, HTTP verification 271/271 và benchmark 90 requests không lỗi; frontend clean install/typecheck/lint/17 tests/build đạt, browser production confirmation đang thực hiện. Coverage statements và branches phải đọc riêng trong `coverage.json`, không xem 87,3% statements là branch coverage. Các acceptance case dưới đây vẫn cần evidence đúng phạm vi; Azure live và frozen quality split chưa đạt.

## Nguyên tắc và evidence

P0 = bắt buộc để website được nghiệm thu. P1 = mục tiêu chất lượng/khả dụng đã đặt; phải đo và công khai, không bỏ qua bằng cách không chạy. Unit tests có thể inject deterministic vectors/SDK fake để kiểm tra toán và lỗi; đó không chứng minh pretrained retrieval hoặc Azure thật.

Mỗi report ghi command, timestamp, commit code/lock, model revisions, dataset/index/policy hashes, môi trường và kết quả. Evidence HTTP/browser cần request/response không chứa key, token, audio cá nhân hoặc đường dẫn máy người dùng. Screenshots không thay assertion API. Mock evidence phải gắn `mock`; model/live evidence phải gắn đúng dependency thật.

Coverage đề xuất ≥80% nhánh mã Application/Data/validation sau triển khai; coverage không thay các test boundary và real model/live gates dưới đây. Không viết test chỉ lặp lại công thức triển khai mà thiếu fixture phản ví dụ.

## Acceptance cases

| AC / mức | Kịch bản và hành động | Kết quả phải có | Không được xảy ra | Evidence tối thiểu |
| --- | --- | --- | --- | --- |
| AC-001 P0 | POST text tiếng Việt có dấu “giày chạy bộ màu đen”, nearest top_k=5 | 200; mode/input giữ đúng; ≤5 product unique; score hữu hạn; trace thật | Trả product hardcoded hoặc gọi model Anh đơn lẻ cho text Việt | HTTP integration + real encoder smoke |
| AC-002 P0 | Cùng text sau trim/NFC/gộp whitespace; thêm câu gần nghĩa có label | Normalize ổn định; dấu được giữ; near-meaning đánh giá trên split | Bỏ dấu/dictionary translation làm pipeline chính; hứa rank cố định chưa đo | Unit normalization + raw evaluation |
| AC-003 P0 | Text rỗng, >500 ký tự, >128 tokens, input type sai; Unicode hợp lệ có dấu | Input sai→422 có field/code, không inference; Unicode hợp lệ không bị bỏ dấu; sửa và submit lại được | Silent truncation hoặc trả 200 giả | Spies encoder + API boundary table |
| AC-004 P0 | Upload JPEG/PNG/WebP hợp lệ có EXIF/alpha | Decode/RGB theo 05; preview đúng; /search/image trả finite ranks | Dùng filename/path/URL client để đọc file server | Unit decode + browser/API |
| AC-005 P0 | Ảnh sai MIME/magic, bytes hỏng, >5MiB, >16MP, chiều >8192, decompression bomb | Reject theo 06 trước encoder; temp bytes được dọn | Chỉ tin content-type hoặc bị OOM/crash worker | Multipart tests từng boundary + spy |
| AC-006 P0 | WAV PCM16 mono 16k 1–15s, rồi stereo/rate/encoding sai, >1MiB, 0.9s/15.1s | Đúng format mới đi SDK; sai có validation message | Gửi WebM lên Azure như WAV; cần FFmpeg không được khai báo | Header parser tests + SDK call count |
| AC-007 P0 | Mic allow/deny/unavailable; record và stop; đóng tab/đổi mode | Capture WAV thật; 15s tự dừng; deny hướng dẫn upload; tracks/resources dọn | Mic tiếp tục ghi hoặc permission loop | Browser real mic smoke + denied test |
| AC-008 P0 | Transcribe tiếng Việt qua Azure resource được cấu hình | Language vi-VN; transcript thật; source=azure; user sửa được | Response demo/mock gắn nhãn Azure | Live bounded gate + network/backend evidence |
| AC-009 P0 | STT trả transcript; sửa lời rồi nhấn Tìm theo lời nói | Trước xác nhận không /search; search voice dùng bản sửa và cùng text pipeline | Auto search transcript chưa được xác nhận; tìm theo bản cũ | E2E interception + payload assertions |
| AC-010 P0 | SDK NoMatch, auth/region fail, 429, network timeout | Lỗi mapped theo 08; input/preview còn; retry thủ công; text/order dùng được | Retry vô hạn, key/log leak, silent mock fallback | Fake SDK failure matrix + API/UI |
| AC-011 P0 | Chọn transcript nhập tay khi offline | Nhãn “Transcript nhập tay · mô phỏng”; provenance rõ; tìm được qua text pipeline | Đánh dấu FR-03/live gate đạt | E2E + source assertions |
| AC-012 P0 | Deterministic unit vectors cho product và multimodal; query norm gần 0 | Product normalize(.5T+.5I); query normalize(λqt+(1−λ)qi); final q·V; component qt·V/qi·V; zero norm lỗi | Lấy λ score_text+(1−λ)score_image làm final mà bỏ chuẩn hóa; NaN/divide 0 | Unit independent expected arithmetic |
| AC-013 P0 | Multimodal thiếu text/ảnh; weights .1,.5,.9 và ngoài range; relevant custom weight | Valid default .5; range .1–.9; thiếu input 422; relevant custom weight chưa calibrated trả 503 | Reuse threshold .5 cho weight khác; text/image fake fusion | Boundary API + policy checks |
| AC-014 P0 | Catalog adversarial: điểm cao không đạt brand/price, điểm thấp đạt; filter category/brand/min/max/in_stock kết hợp | Hard filters inclusive VND; lọc trên toàn catalog; lấy đủ K nếu còn ứng viên | Top-k trước filter; infer giá/tồn kho từ embedding | Deterministic integration fixture + exact expected IDs |
| AC-015 P0 | top_k=1,20,0,21,fraction; options unknown/duplicate invalid | Valid 1–20; reject sai theo API; count≤eligible count; không duplicate | Coerce tùy ý hoặc ignore options sai | Validation + integration |
| AC-016 P0 | Scores bằng nhau/khác ít hơn UI rounding; repeated requests | Sort full precision desc, tie product_id theo 05; UI không thay rank | Sort rounded score hoặc set order không ổn định | Unit rank fixtures + repeats |
| AC-017 P0 | nearest với input OOD và catalog còn ứng viên | Vẫn trả closest; UI ghi rõ không bảo đảm liên quan | Label xác suất/tỉ lệ độ chính xác hoặc tự empty theo threshold | API/UI OOD case |
| AC-018 P0 | relevant có calibration; threshold equality và tất cả dưới threshold | Equality theo policy 05; no results 200 reason threshold; filter-empty reason filters | Thiếu policy trả empty; nâng score hoặc đổi threshold để có kết quả | Controlled score API cases |
| AC-019 P0 | Model/index/policy unavailable; order/detail/health live cùng lúc | Search 503 dependency code; relevant policy capability riêng; lookup và live vẫn hoạt động | Startup crash mọi route hoặc online tự tải model | Integration startup failure matrix |
| AC-020 P0 | Đổi description/image bytes/model rev/preprocess/fusion/schema; index cũ | Fingerprint mismatch; stale không serve; builder mới + restart phục hồi | Chỉ dùng mtime hoặc bỏ ảnh/model khỏi fingerprint | Cache invalidation matrix |
| AC-021 P0 | Hai builders; kill một builder trước publish; loader đọc khi write | Một builder; publish atomic; index trước nguyên vẹn; loader không đọc temp | NPZ partial hoặc JSON/index nửa cũ nửa mới | Integration process/atomic failure injection |
| AC-022 P0 | 1 inference chạy +2 chờ; request thứ tư; cancel/deadline request native hoặc request trong queue | Bounded semaphore/executor; 429 SEARCH_BUSY Retry-After2; backend10s/browser15s kết thúc pending với504 SEARCH_TIMEOUT; queue timeout không chạy encoder; active slot giữ đến native kết thúc | Native thread vô hạn, response muộn ghi UI hoặc slot release sớm | Barrier-controlled concurrency/deadline test + E2E |
| AC-023 P0 | Search A chậm; B nhanh; đổi mode/ảnh/filter rồi response A về | B giữ kết quả; draft đánh dấu cần tìm lại; request ID/abort guard | A ghi đè B hoặc hiển thị input khác results | Browser delayed HTTP race tests |
| AC-024 P0 | Card→product detail→Back; direct URL và refresh; ID sai | Metadata/ảnh/source/giá demo; back giữ query, options/results; 404 rõ | Mất state mỗi lần back, checkout ngoài scope, model bắt buộc cho detail | E2E navigation + detail API |
| AC-025 P0 | Tra cứu O001 của C001 và mở detail/reload | Đúng mã/date/status/items/total; lookup exact; customer scope từ server | Client tự chọn owner, order fuzzy embedding | Repository + API + E2E |
| AC-026 P0 | O002 của C002 và O999; direct route; client thêm customer_id | Foreign/missing cùng 404/message; client scope bị reject | Leak existence/owner/items của C002 hoặc chỉ filter frontend | Isolation tests + response equality |
| AC-027 P0 | Duyệt tất cả ≥12 product images và source manifest | Mỗi ảnh là chụp thật từ mạng, SHA/source/license/credit khớp; detail/credits hiển thị nguồn | Generated/synthetic/illustration trá hình; ảnh mạng hotlink bắt buộc lúc chạy | Manual visual audit + manifest validator + browser |
| AC-028 P0 | Inspect bundle/network/log/error/env/artifacts; gửi text/audio có marker | Không key browser/log; không audio/query cá nhân persistent; upload không public; CORS allowlist | Secret trong VITE_* hoặc lỗi SDK raw chứa credentials; public temp/audio URL | Secret scan + devtools + filesystem/log checks |
| AC-029 P1 | 360/768/1440px; tab keyboard, file/filter/details, loading/empty/error | UI tiếng Việt; controls có labels/focus; không overflow ngang; error recovery rõ | Chỉ happy path desktop hoặc loading bị kẹt | E2E screenshots/assertions + manual a11y |
| AC-030 P0 | So trace các mode thành công và lỗi/empty | Stage/timing thực đo, input/mode/weight/options đúng; finite nonnegative ms | Timing fabricated hoặc full embedding/secrets trả browser | Schema integration + UI inspection |
| AC-031 P0 | Restart hai lần cùng locks/model/data/policy; chạy same queries | IDs/rank giống, scores tolerance 1e-5; model revision báo đúng | Download main/latest hoặc đổi thứ tự JSON làm sai alignment | Reproducibility reports |
| AC-032 P1 | Warm mỗi mode text/image/multimodal 30 requests tuần tự trên máy đã mô tả | p95≤5s mục tiêu; report từng mode, errors, cold start riêng | Cộng thời gian ghi âm vào inference; bỏ outliers/lỗi | benchmark JSON + hardware metadata |
| AC-033 P0 | Review imports/module boundaries và UML↔code | Presentation→Application→Data; domain độc lập; DI composition root; Data không ranking/model load | Circular dependency hoặc routes tự tạo model mỗi call | Architecture tests + mapping ở 12 |
| AC-034 P0 | Inject encoder/STT adapter khác; model revision thay đổi | Interface compatible; fingerprint/policy invalidate; errors typed | “512D giống nhau” được xem là aligned hoặc cache vẫn dùng cũ | Protocol tests + invalidation |
| AC-035 P1 | Frozen test tiếng Việt text/image/multimodal positive/OOD | Hit@3≥.80 và OOD rejection≥.60 từng mode; report counts/raw ranks | Tune trên test, sửa label/rank để pass, gộp trung bình che mode fail | evaluate real model report |
| AC-036 P0 | 5 WAV vi-VN fixture thật qua Azure; người dùng xác nhận transcript rồi search | Gate live ở dưới đạt; mọi request bounded/không leak; workflow end to end | Dùng transcript tay thay audio hoặc dùng SDK fake làm live | speech live report + browser demo |
| AC-037 P0 | Install sạch locks; validate mọi data/schema/order totals/asset paths | Repeatable Windows setup; script exit/report đúng; phụ thuộc khóa | Lock tên có nhưng không dùng hoặc totals tính sai | Clean-install log + validate_dataset report |
| AC-038 P0 | NPZ dimension/ID order sai, NaN, zero norm, truncated/ZIP bomb; policy khác fingerprint | Refuse invalid index/policy; 503 scoped; lookup vẫn hoạt động | Deserialize pickle hoặc silent repair/random vectors | Loader corruption tests |
| AC-039 P0 | Browser refresh /products/P001 và /orders/O001; frontend HTTP unavailable/reconnect | SPA fallback + same API ownership; lỗi retry rõ; route khôi phục | Dev server trả 404 route hoặc frontend tự fabricate detail | Real browser HTTP test |
| AC-040 P0 | JSON và multipart endpoints đúng; malformed options JSON/content type/body | Schema 06 nhất quán; status/error envelope ổn định; frontend hiểu đúng | Endpoint alternate không được tài liệu hóa hoặc raw stacktrace | OpenAPI/contract + frontend integration |
| AC-041 P0 | SDK treo/native call vượt deadline backend 25s; browser30s; user cancel | Reply timeout đúng, pending UI kết thúc; slot native không reuse sớm; retry thủ công | 200 transcript giả hoặc startup retry tính phí | Controllable SDK delay + E2E |
| AC-042 P0 | Product asset route ID/path lạ, traversal, remote URL; missing local image | Chỉ allowlisted catalog image; unknown404; UI alt; safe error | Đọc filesystem bất kỳ, SSRF hoặc serve upload audio | Static route security tests |
| AC-043 P0 | Empty catalog hợp lệ, filter loại hết, threshold loại hết | 200 với reason catalog_empty/filters/threshold đúng ưu tiên 05/06 | Đồng nhất dependency failure với empty hoặc UI crash | Integration response matrix |
| AC-044 P0 | Native Speech đang active; request audio thứ hai; timeout/cancel request đầu | Một native Speech active, không queue; 429 SPEECH_BUSY Retry-After5; slot giữ đến completion; search executor riêng | Azure treo khóa search/order hoặc sinh thêm SDK threads | Barrier-controlled SDK integration + simultaneous text/order |
| AC-045 P0 | /meta, /products pagination, /credits, media ETag304; headers/error envelope | Fields/status/counts theo06; JSON no-store, X-Request-ID UUID; media nosniff/ETag; missing image503; credits chính xác | Health bị đặt trong prefix, hash/path private leak, browser cache audio/search | Contract integration toàn endpoint + network headers |
| AC-046 P1 | Axe và console happy flows; links/transcript có text XSS | Serious/critical axe issues=0, console errors=0; text render escaped, links HTTPS allowlist | dangerouslySetInnerHTML dữ liệu user/source hoặc mở script URL | Browser axe/XSS tests + manual keyboard |

## Traceability đầy đủ

| Requirement | UC | Acceptance evidence |
| --- | --- | --- |
| FR-01 | UC-01 | AC-001, 014–019, 030, 040, 043 |
| FR-02 | UC-02 | AC-001–003, 035 |
| FR-03 | UC-03 | AC-006–011, 028, 036, 041 |
| FR-04 | UC-04 | AC-004–005, 027, 035 |
| FR-05 | UC-05 | AC-025–026 |
| FR-06 | UC-06 | AC-024, 027, 039, 042, 045 |
| FR-07 | UC-07 | AC-025–026, 039 |
| FR-08 | UC-01 | AC-012, 014–018, 020–022, 031, 038, 043 |
| FR-09 | UC-08 | AC-012–013, 023, 030, 035 |
| FR-10 | UC-01 | AC-014–015, 023 |
| FR-11 | UC-01/03/08 | AC-009, 011, 023, 030, 045 |
| FR-12 | UC-01–08 | AC-003, 005–007, 010, 013, 019–023, 026, 028–029, 038–045 |
| FR-13 | UC-06 | AC-027, 028, 037, 042, 045 |
| NFR-01 | Performance | AC-022, 032, 041, 044 |
| NFR-02 | Usability | AC-007, 009, 023–024, 029, 039, 046 |
| NFR-03 | Reliability | AC-003, 005–006, 010, 019–023, 038, 041, 043–045 |
| NFR-04 | Maintainability | AC-033, 037, 040 |
| NFR-05 | Extensibility | AC-020, 034 |
| NFR-06 | Privacy | AC-025–028, 042, 045–046 |
| NFR-07 | Reproducibility | AC-016, 020–021, 031, 037 |
| NFR-08 | Relevance | AC-002, 017–018, 035–036 |

## Frozen quality protocol

Schema/threshold selection thực hiện theo [05](05_AI_SEARCH.md), trong `evaluation/queries.json`. Tối thiểu **mỗi split calibration và test** có 5 positive +5 OOD cho mỗi mode text/image/multimodal: 30 cases/split, 60 total. Split theo `family_id`, nguồn/góc ảnh và cụm diễn đạt để tránh leakage; IDs/query/ảnh/labels của test độc lập calibration; labels chốt trước inference. Image fixtures ở `data/queries` là ảnh chụp thật trên mạng, có nguồn trong manifest; không dùng bản sao ảnh index để tuyên bố quality thực tế. Cùng ảnh index chỉ được dùng smoke decode/alignment có nhãn riêng.

- Positive ghi `expected_product_ids` do người review xác nhận từ nội dung/ảnh, không lấy từ top-k của model. Hit@3 của một case là có ít nhất một expected ID trong ba kết quả đầu theo protocol 05. Report tử số/mẫu số từng mode; với 5 cases, ≥.80 nghĩa là ≥4/5.
- OOD có label “không có sản phẩm liên quan trong catalog”; report fraction trả empty ở relevant. Với 5 cases/mode, ≥.60 nghĩa là ≥3/5. Nearest được kiểm thử riêng và không được tính vào OOD rejection.
- Calibration chỉ dùng calibration split, chọn thresholds và lưu dataset/model/index/policy fingerprint. Test script không ghi lại policy. Multimodal calibration ở weight .5; relevant weight khác không có policy tương ứng phải unavailable.
- Voice đã được xác nhận transcript dùng text retrieval policy. Bộ 5 live WAV là gate STT + workflow riêng, không làm tăng mẫu số text quality bằng cách lặp transcript của test.
- Nếu fail: công bố cases/scores, kiểm tra dữ liệu/preprocessing/model pairing, tối ưu có lý do; khi thay đổi model/data phải tạo calibration/policy mới. Nếu test được dùng để tune, phiên bản đó trở thành development set; phải chốt một test độc lập mới trước khi tuyên bố quality đạt.

Không ghi expected CLIP rank/accuracy trước khi chạy thật. Cosine là score tương đồng, không phải phần trăm xác suất. Các mục tiêu này là đề xuất chất lượng trong 02, evidence cần nêu giới hạn do catalog/số mẫu nhỏ.

## Gate Azure thật

Chuẩn bị 5 WAV PCM16 mono16k 1–15s ghi tiếng Việt về catalog và manifest `evaluation/voice_cases.json`, phrase labels/expected product IDs do người review xác nhận, không chứa dữ liệu cá nhân. Kiểm thử chỉ được chạy khi dịch vụ và quyền dùng Azure đã sẵn sàng; command thủ công có `--confirm-live`, tối đa 5 SDK requests toàn lượt, không auto retry tăng chi phí. Report số calls và tổng thời lượng audio; không bịa giá Azure hoặc chi phí thực tế khi chưa có billing evidence.

Điều kiện: 5/5 calls kết thúc trong deadline hoặc có lỗi typed; ít nhất 4/5 nhận dạng được transcript non-empty và giữ ý sản phẩm theo phrase labels; ít nhất 4/5 luồng transcript xác nhận→voice search đưa một expected product vào Top3. Ngoài 5 calls này, test errors dùng fake SDK. Khả năng tự sửa transcript không được dùng để tăng điểm STT: report riêng **bản STT gốc** và **bản user đã sửa**, cùng retrieval trước/sau nếu cần. Deadline timeout được tính là fail recognition cho case đó.

Thiếu key, không xác nhận được region, network fail hoặc chưa được phép dùng dịch vụ: gate ghi pending/blocked dependency, website chưa nghiệm thu FR-03. Có thể demo manual transcript với nhãn rõ, không đánh dấu live gate passed.

## Lệnh gate sau triển khai

Working directory `assignment6_demo`, xem env/setup ở [11](11_RUNBOOK.md). Các lệnh dưới đây đã triển khai; smoke/verify/benchmark cần backend đang chạy. `evaluate.py` hiện chỉ đánh giá lại 15 demo calibration cases, **không nhận `--split test` và không thay frozen test độc lập**.

```powershell
& .\backend\.venv\Scripts\python.exe scripts\validate_dataset.py
& .\backend\.venv\Scripts\python.exe scripts\smoke_backend.py
& .\backend\.venv\Scripts\python.exe scripts\verify_expanded_demo.py
Push-Location backend
& .\.venv\Scripts\python.exe -m pytest tests --cov=app --cov-branch --cov-report=term-missing
Pop-Location
& .\backend\.venv\Scripts\python.exe scripts\calibrate_thresholds.py
& .\backend\.venv\Scripts\python.exe scripts\evaluate.py
& .\backend\.venv\Scripts\python.exe scripts\benchmark_backend.py --requests-per-mode 30
```

Frontend commands chạy trong `frontend`: `npm ci`, `npm run typecheck`, `npm run lint`, `npm test`, `npm run build`, `npm run test:e2e`. E2E chạy server thật local; intercept chỉ dùng các error/race scenarios có nhãn và không thay full live happy path.

## Tracker website

| Gate | Trạng thái hiện tại | Evidence / phần còn thiếu |
| --- | --- | --- |
| G1 | Partial | Dataset và 271 API checks đạt; frontend `npm ci` sạch đạt, npm audit 0. Backend lock/pip check đạt; pip-audit không audit được torch `+cpu` qua PyPI. Secret/runtime/env được ignore; clean-install tổng thể cần hồ sơ tái hiện riêng. |
| G2 | Partial | 103 unit/integration tests đạt; coverage report có statements/branches riêng. Branch coverage chưa đạt mục tiêu đề xuất 80%; architecture mapping được kiểm tra riêng. |
| G3 | Partial | CPU models/index và 3 policy mới khớp catalog 60 sản phẩm; demo calibration đạt mục tiêu nhỏ. Chưa freeze bộ 60 cases độc lập theo protocol trên. |
| G4 | Partial / quality regression | Text demo Hit@3 5/6, category probes 7/12; một số Top1 baseline cũ không đạt. Không coi self-match ảnh là quality test. [reproducibility.json](../artifacts/backend/reproducibility.json) xác nhận rank/score ba mode ổn định qua hai restart, tolerance1e-5. |
| G5 | Passed wiring / quality failed riêng | Clean install/typecheck/lint/17 unit/build và 19/19 production wiring tests đạt. Hai quality tests vẫn fail; xem `FRONTEND_VERIFICATION.md`. Visual reviewer xác nhận một fix resolved, không nghiệm thu model/Azure. |
| G6 | Passed trong phạm vi tests hiện có | Boundary, owner isolation, cache/corruption và native concurrency được kiểm tra bằng tests; chưa thay các tình huống Azure thật hoặc audit production có danh tính. |
| G7 | Passed warm CPU | [performance.json](../artifacts/backend/performance.json): 90 measured requests, 0 errors, p95 text81,69 / image380,78 / multimodal455,44ms. Cold start chưa đo. |
| G8 | Pending dependency | Quyền tối đa5 lượt đã được người dùng xác nhận. Shared ledger còn0 lượt dùng, thiếu5 WAV giọng người thật, mic evidence và Azure config/live results; xem [AZURE_LIVE_CHECK.md](AZURE_LIVE_CHECK.md). |
| G9 | Partial | Runbook đã cập nhật commands thực; UML↔code mapping ở12 cần nêu rõ những class đích chưa tách. Chưa có file Visual Paradigm `.vpp` và frozen quality/live speech artifacts. |

Tracker mô tả evidence hiện có, không tuyên bố website được nghiệm thu toàn bộ. Mỗi lần chạy mới phải đọc report/hash thực tế; không nâng failed/pending thành passed từ việc có code hoặc screenshot.
