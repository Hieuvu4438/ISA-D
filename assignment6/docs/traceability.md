# Traceability — Requirement → UML → Code → Evidence

Nguồn yêu cầu: PDF trang 17–19 (T1–T6), 20–21 (evaluation/report/submission), 22 (principles). Các links tới methods và tests dưới đây cần kiểm tra trên source cuối; green test không thay bằng chứng native `.vpp` hoặc visual review PDF.

| FR | Use case / UML | Component và method | Evidence | Report |
|---|---|---|---|---|
| FR-01 | Search by Keyword → Search Product | QueryService.text_query; SearchService.search / retrieve_candidates | Text demo JSON/log + query normalization/matching tests | Trang 3, 7–10 |
| FR-02 | Search by Voice; voice sequence 7 participants | SpeechService.transcribe → QueryService.voice_query → SearchService.search | Voice demo; text/voice equivalence và empty transcript tests | Trang 3, 6, 8, 10 |
| FR-03 | Search by Image | ImageService.encode → QueryService.image_query; VectorIndex cosine; RankingService.rank | Image demo; descriptor dimension/cosine/self/variant/corrupt image tests | Trang 3, 7–10 |
| FR-04 | Search Product và modalities | QueryService common schema/type/filters/top_k/weights | Contract/invalid config tests; processing envelope trong demos | Trang 3, 7–8 |
| FR-05 | Search Product / View Product | RankingService.rank; SearchResultView | Descending order/tie-break/top-k/no-mutation tests; scores demo | Trang 3, 5, 7–10 |
| FR-06 | View Product | SearchUI.view_product → SearchService.view_product → ProductRepository.get_by_id | Product detail CLI + test_product_detail | Trang 3, 4, 7 |
| FR-07 | Search Order / View Order | OrderService.find_order → OrderRepository.find_order | Order O001/C001 demo; unknown id/wrong customer scope tests | Trang 3–5, 7, 11 |
| FR-08 | Data package architecture | ProductRepository validation; VectorIndex validation; generator/index scripts | ≥10 unique products + image paths + metadata/hash/dimension checks | Trang 3, 5, 7 |
| FR-09 | Alternate/error flows | Boundary/QueryService/ImageService/repositories | Empty/no-match/top_k/type/weights/dimension/corrupt image tests; CLI error exit | Trang 3, 6–8 |
| FR-10 | Search Product extension | QueryService.multimodal_query; SearchService candidates union; RankingService | Fusion demo; weight/union/scores tests; evaluation multimodal group | Trang 3, 8–11 |
| FR-11 | Search Product filter behavior | QueryService filters; SearchService filtering | Strict under100 boundary/category and filter-only tests | Trang 3, 8–9 |
| FR-12 | T6 / evaluation | Demo/evaluate scripts; ResultView; build_report.py | logs/JSON/CSV/metrics with ground truth; README reproducibility | Trang 9–12 |

## Cross-cutting mappings

Cột Report trong bảng FR trên ghi trang bản Markdown 12 trang trước đây. Bản hiện tại dùng Sections 1–11 và Appendix A–D: Section 7 implementation, Section 8 method, Section 9 evaluation/demo; Appendix B toàn bộ Python, Appendix C images/data và Appendix D full fixtures/config. Dùng TOC PDF hoặc `build_audit.json::section_pages` để tra cứu trang hiện tại.

| Requirement / gate | Evidence phải có |
|---|---|
| Native UML | `models/Assignment_06_Multimodal_Search.vpp`; reopen/select/edit qua VP; `vp_use_case`, `vp_architecture`, `vp_sequence` screenshots và ba diagram exports |
| Layer dependencies | Source imports: Presentation → Application → Data; composition root riêng; architecture test; native package ownership/dependency review |
| Retrieval khác ranking | `retrieve_candidates` chưa sort/cắt top-k cuối; `RankingService.rank` owns final order; code review + tests |
| Simulation trung thực | SpeechService nhận transcript; descriptor encode pixels 88 chiều; README/report/UI nhãn đúng; không CLIP/vectorDB/realASR claims |
| Report LaTeX English / 11 nội dung | `docs/report.tex` → XeLaTeX, không giới hạn trang, đủ 25 ảnh và mọi file Python; input hashes, build audit và visual review |
| Bảy nhóm bài nộp | Report, .vpp, source, dataset, sample images, README, demo results; submission validation + ZIP manifest + extracted smoke test |
| Thiếu student identity | Cover `Not supplied`; không suy ra từ license/tài khoản |

## Nguồn số liệu và cách diễn giải

`artifacts/evaluation/metrics.json` phải khớp `results.json`/`results.csv`, tổng success/tổng rows. Ground truth không được sửa theo outputs. `artifacts/demo/demo_results.json` chứa input/query/processing/results và scores thật. Report builder đọc các artifacts, từ chối metrics không khớp, và không tự tạo số liệu đánh giá.

Metrics tổng baseline là **primary** 12 queries; results có thêm extension/challenge/robustness, nên đối chiếu theo group chứ không nhầm 12 là toàn bộ 21 rows. Demo screenshots được chụp Python result viewer nhận JSON từ fresh CLI process; raw screenshot payload được lưu `artifacts/screenshots/demo_*_payload.json`. Viewer dùng values trả về, không tự tính lại search/rank. Report lấy summary từ demo_results.json, screenshot có thể dùng top-k nhỏ hơn để đọc rõ.

Root giữ `docs/AGENT_PROGRESS.md` với các gate runtime/nativeVP/package; tài liệu này liên kết requirement đến nguồn bằng chứng, không tự chứng nhận mọi gate đã pass.

## Test anchors trên source hiện tại

Các tests nằm trong `tests/test_prototype.py`:

| Hành vi | Test function |
|---|---|
| FR-01 normalize/alias/filter/no-match | test_text_normalizes_alias_punctuation_and_unique_terms; test_text_filters_relevance_and_no_matches |
| FR-02 speech adapter/equivalence | test_voice_calls_speech_adapter_and_matches_text; test_speech_rejects_real_audio_and_empty |
| FR-03 pixel encoding/cosine | test_pixel_encoder_is_path_independent_and_dimension_88; test_cosine_boundaries; test_image_exact_and_transformed_samples |
| FR-04/09 invalid boundary | test_top_k_boundary; test_embedding_validation; test_fusion_weight_validation; test_image_missing_and_corrupt_are_clear_errors |
| FR-05 retrieval/rank/top-k/immutability | test_retrieval_separate_from_ranking_and_tie_break; test_dataset_and_repository_are_immutable |
| FR-06 product details | test_product_detail |
| FR-07 order isolation | test_order_customer_scope |
| FR-08 dataset consistency | test_dataset_and_repository_are_immutable; index/manifest validation scripts |
| FR-10 union and score formula | test_fusion_has_union_candidates_and_component_formula |
| FR-11 strict/inclusive/filter-only | test_price_strict_vs_inclusive; test_filter_only_and_inclusive_price |
| FR-12 CLI from other CWD | test_cli_end_to_end_json; test_cli_invalid_input_without_traceback |
| NFR-01 layer boundary | test_architecture_import_boundaries |

Data boundary regression trong `tests/test_data_boundaries.py` kiểm tra product/order invalid schema, stale/index ids/dimension/metadata, source load errors, price/filter boundaries, stock signal không boost ẩn và dataset generator giữ files đã chỉnh. `tests/test_evaluation.py::test_p95_uses_nearest_rank` kiểm tra convention percentile. Bằng chứng test count/coverage là `artifacts/tests/junit.xml`, `test_output.txt` và `coverage.json`: coverage phạm vi Application/Data, không phải toàn bộ UI/scripts/native VP.
