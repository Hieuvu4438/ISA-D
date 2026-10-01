# Prototype TDD và bằng chứng kiểm tra

Nguồn acceptance: `docs/AI_AGENT_ASSIGNMENT_06_GUIDE.md`, PDF trang 9–15 và 19–22. Test runner là pytest cho Python, không có package.json hoặc npm runner. Journeys: Customer tìm sản phẩm bằng keyword, voice transcript qua adapter, pixel image, fusion; lọc category/price; xem product/order theo customer scope; input sai được báo rõ; reviewer chạy lại demo/evaluation offline và kiểm tra boundaries ba tầng.

## RED → GREEN thực tế

| Cycle | RED đã chạy trước production change | GREEN đã chạy sau implementation | Bằng chứng |
|---|---|---|---|
| Prototype mới | `python -m pytest tests/test_prototype.py -q`: **9 failed, 1 passed, 32 errors**; các API `main/application/data` chưa tồn tại | `.venv/Scripts/python.exe -m pytest tests/test_prototype.py -q`: **42 passed in 2.11s** | `artifacts/tests/red.txt`, `green-initial.txt` |
| p95 nearest-rank | `pytest tests/test_evaluation.py -q`: **1 failed** vì helper percentile chưa có | Cùng target: **1 passed in 0.10s** | `red-percentile.txt`, `green-percentile.txt` |
| Boundary price/path | `pytest tests/test_data_boundaries.py -q -k "extracted_price_overflow or generator_rejects"`: **2 failed**, không reject float overflow và path ngoài dataset root | Cùng target: **2 passed, 32 deselected in 0.14s** | `red-final-boundaries.txt`, `green-final-boundaries.txt` |

RED đầu tiên là missing implementation signal: Python đã parse/execute acceptance tests, numpy/Pillow/pytest đã có; failures xuất phát từ modules/APIs chưa hiện thực, không phải syntax lỗi hay dependency thiếu. Ground truth `evaluation/queries.json` được viết trước production implementation và trước chạy evaluation. Một assertion fusion được làm rõ trước implementation: query `blue` cho candidate union qua các category; query `blue shoes` có category filter cố ý loại bag. Expected evaluation labels không đổi.

Console logs do PowerShell redirect được chuẩn hóa encoding UTF-8 và line ending LF để đọc/đóng gói nhất quán; nội dung kết quả thực giữ nguyên, không tuyên bố byte-exact so với stdout encoding ban đầu. RED/GREEN assertions và số đếm không bị chỉnh sửa.

Checkpoint Git do root điều phối vì repo cha có nhiều assignment và nhiều worker dùng chung; worker không tự commit source của người khác. Xem `docs/AGENT_PROGRESS.md` và git history cho hashes checkpoint do root tạo. RED/GREEN logs trên bảo tồn evidence dù checkpoint được gom/squash.

## Guarantees đã kiểm tra

| Hành vi | Test bằng chứng | Loại |
|---|---|---|
| 12 product IDs duy nhất, image tồn tại, kết quả/repository không bị mutate | `test_dataset_and_repository_are_immutable`, schema cases tại `test_data_boundaries.py` | integration/boundary |
| Case/whitespace/punctuation/alias, unique whole-word terms | `test_text_normalizes_alias_punctuation_and_unique_terms` | unit |
| Input length/type/top-k/filters/weights/vector được validate | parametric query/vector tests, `test_extracted_price_overflow_is_rejected` | unit/boundary |
| Strict `<100` khác inclusive `≤100`; category hard filter; filter-only hợp lệ | `test_price_strict_vs_inclusive`, `test_filter_only_and_inclusive_price` | unit/integration |
| Voice gọi SpeechService rồi dùng query/retrieval/rank chung; kết quả bằng text | `test_voice_calls_speech_adapter_and_matches_text`, speech adapter test | integration |
| Pixel encoder 88 chiều, L2 norm 1, không phụ thuộc tên file; khác pixel thì descriptor khác | `test_pixel_encoder_is_path_independent_and_dimension_88` | integration |
| Exact product image cosine≈1, transformed query vẫn relevant | `test_image_exact_and_transformed_samples` | integration |
| Cosine identical/orthogonal/opposite/zero và invalid dimension/NaN | `test_cosine_boundaries`, `test_invalid_cosine_and_index_query` | unit |
| Missing/corrupt/over-limit image không traceback pipeline | image error/pixel-limit tests | boundary |
| Retrieval không sort/top-k, rank có tie-break id, không boost stock ẩn | `test_retrieval_separate_from_ranking_and_tie_break`, ranking boundary test | unit/integration |
| Fusion dùng union; hai modalities ảnh hưởng top-1; final score đúng formula | `test_fusion_has_union_candidates_and_component_formula` | integration |
| Customer C001 không xem order C002; invalid ID/not-found rõ | `test_order_customer_scope`, order data boundary tests | integration/boundary |
| Index reject encoder/dimension/ID/fingerprint mismatch | `test_index_consistency_and_stale_detection` | boundary |
| Dataset generator preserve customized files, reject path ngoài root | dataset regeneration/path tests | integration/boundary |
| CLI demo/text/voice/image/fusion/order chạy ở cwd khác, stdout/output JSON cùng content | subprocess `test_cli_end_to_end_json` cases | E2E CLI |
| Presentation không import data; data không import application/presentation | `test_architecture_import_boundaries` AST | structural |
| p95 theo nearest-rank `ceil(p*n)` | `test_p95_uses_nearest_rank` | unit |

## Final checks

Lệnh đã chạy trên source sau format và boundary fixes:

```powershell
.venv/Scripts/python.exe -m pytest -q --cov=application --cov=data --cov-fail-under=80 --cov-report=term-missing --cov-report=json:artifacts/tests/coverage.json --cov-report=html:artifacts/tests/coverage --junitxml=artifacts/tests/junit.xml
.venv/Scripts/python.exe -m ruff check main.py application data presentation scripts/prepare_dataset.py scripts/build_index.py scripts/run_evaluation.py tests
.venv/Scripts/python.exe -m pyright
.venv/Scripts/python.exe -m compileall -q main.py presentation application data scripts
.venv/Scripts/python.exe -m pip check
```

Kết quả **78 passed in 2.84s**, **100% application/data line coverage (264 statements)**, không skip. Ruff **All checks passed!**, Pyright **0 errors, 0 warnings**, compileall exit 0, pip check **No broken requirements found**. Logs/JUnit/coverage ở `artifacts/tests/`. Coverage là statement/line coverage, không tuyên bố branch coverage hoặc proof cho mọi tình huống có thể.

## Evaluation và giới hạn của bằng chứng

Actual pipeline được chạy bởi `scripts/run_evaluation.py`, xuất `artifacts/evaluation/{metrics.json,results.json,results.csv}`. Primary top-1: **12/12**, extension: **2/2**, challenge: **0/2**, robustness: **5/5**, denominator tách riêng. Ground truth SHA-256 trong metrics cho phép đối chiếu labels. Hai failure thực: `sneakers` không có alias; `shoes not black` chưa hiểu negation và trả black shoes. Không đổi expected sau khi xem output.

Tests chưa chứng minh STT audio thật, semantic text/vision generalization, concurrency/production scale, authentication hoặc UI web, vì prototype không hiện thực những phần này. Screenshot terminal và native UML do root thu riêng; CLI E2E tests không thay thế bằng chứng Visual Paradigm. Timing n=12 loại trừ startup và có nhiễu máy local; p95 nearest-rank với n=12 chính là max.
