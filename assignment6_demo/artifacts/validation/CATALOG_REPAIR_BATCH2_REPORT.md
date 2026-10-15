# Catalog repair batch 2 evidence

Date: 2026-10-15. Scope: P121–P130 actual backpack photos, descriptive metadata, seed and existing live release. No application behavior changes. No Speech calls or paid API calls.

## Executed checks

| Command/action | Exit/result | Evidence |
| --- | --- | --- |
| Commons imageinfo and selected photo downloads | 11/16 candidates accepted by existing acquisition metadata checks; 5 skipped, not claimed reviewed | `catalog-visual-audit/batch2-candidates.jpg`, selected provenance in `data/catalog_repair_candidates.json` |
| Human visual inspection using view_image | 11 candidates inspected; R201 rejected as ambiguous bag/backpack; 10 selected | `data/catalog_repair_batch2_review.json` |
| `python scripts/apply_catalog_repair.py` and `--apply` | Both exit 0; canonical 26 reviews, 18 replacements across both batches | `catalog-repair-preview.json`, `catalog-repair-applied.json`; old reports preserved as `catalog-repair-batch1-*` |
| `python scripts/validate_dataset.py` | Exit 0, 180 products, 30 orders, one query photo | `../backend/dataset-validation.json` |
| `python scripts/update_image_credits.py` | Exit 0 | `docs/IMAGE_CREDITS.md` |
| `python scripts/build_index.py` | Exit 0, actual local CPU model | `../backend/index-build.json` |
| Ephemeral local helper `runtime/catalog-repair/publish_batch2.py` | Exit 0, ten actual authenticated draft/photo/publish cycles; real CPU builds | `catalog-repair-batch2-live.json` |
| `python -m pytest backend/tests/test_data.py backend/tests/test_catalog_repair.py backend/tests/test_catalog_search.py backend/tests/test_scope_query.py backend/tests/test_exclusion_query.py backend/tests/test_categories.py -q --basetemp=runtime/tests/catalog-batch2 --junitxml=artifacts/validation/catalog-repair-batch2-tests.xml` | Exit 0, 127 passed in 3.96s | `catalog-repair-batch2-tests.xml` |
| `npx playwright test e2e/catalog-repair-batch2.spec.ts` against running local API and frontend | Initial exit 1, zero tests, test regex syntax error; corrected test to startsWith. Final exit 0, 1 passed, runner 3.53s | `../frontend/catalog-repair-batch2-initial.json`, `../frontend/catalog-repair-batch2-results.json` |
| Backend process restart and actual HTTP verification | Exit 0, ready; all ten exact photo hashes/metadata and live stock/price preserved; 181 products including P181 | `catalog-repair-batch2-restart.json` |
| `python scripts/verify_search_expansion.py` after restart | Exit 0, 50 actual CPU HTTP requests; hybrid 24/24, semantic 23/24 Hit@3 | `catalog-repair-batch2-search-regression.json` |

Python commands use `backend/.venv/Scripts/python.exe`; Playwright runs from `frontend` with the existing local-server configuration. Runtime acquisition/publish helpers and credentials are ignored, not application files. Existing upstream Starlette/httpx deprecation warning does not fail these tests. The full 441-test suite passed at the preceding application-code milestone; it was not rerun for this data-only change.

Browser evidence: `catalog-repair-batch2-browser-model.json` contains ten public product checks and five actual CPU Vietnamese descriptive queries. Targets P129, P124, P121, P130, P128 each ranked first. Fixture `evaluation/catalog_repair_batch2.json` was written before executing those descriptive queries, but labels derive from the repaired catalog. Both screenshots in `../frontend/screenshots/catalog-repair-batch2/` were visually inspected; browser checks found zero axe violations or horizontal overflow at widths 360 and 1440.

Seed IDs/category/price/stock and order bytes were compared to the saved pre-apply snapshot and remained unchanged. Runtime publication preserved live stock and price separately; seed and live differ by previously published P181. Reserved test-admin privileges and sessions are both zero after retirement, verified after restart.

Fingerprints and artifact hashes are recorded in `catalog-repair-batch2-verification.json`; seed has 180 products, live has 181. Actual local CPU encoder fingerprint is `8079066fd176407685d890a0d3ecf86c795ab8256019c955ad70e1cbea986ab2`. Live index is `2c9298c7992e02758bfd8e1df0da00d4b9c33e7e1619ba2d9470451f37c465c2`.

## Acceptance limits

This milestone repairs ten specific products. It does not establish whole-catalog visual quality or independent multimodal relevance/OOD acceptance. Image/multimodal regression uses a catalog self-image and establishes mechanics only. Old independent-quality flags remain false. No STT/Azure verification was performed; restarted backend reports Azure unconfigured. Relevant mode has no calibrated policy for this new index; nearest remains available. Remaining photo groups are tracked in docs17/docs32. Payment remains COD/demo. Full-system completion is not claimed.
