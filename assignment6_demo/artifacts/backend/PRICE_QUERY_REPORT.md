# Price query verification

Date2026-10-15, base8435660. Scope: explicit VND budget/range interpretation, manual filter intersection, visible conditions and opt-out. Contract/UML/grammar/limits: docs/25_PRICE_QUERY.md. This is not complete natural language understanding or STT.

## Commands/results

- `python -m pytest backend/tests/test_price_query.py backend/tests/test_catalog_search.py -q --junitxml=artifacts/backend/price-query-targeted-tests.xml`: initial90 pass/1 fail on old OpenAPI parameter set; updated contract assertion to include interpret_price. Next98 passed in2.52s, exit0, before spoken-number extension.
- `python -m pytest backend/tests -q --junitxml=artifacts/backend/price-query-full-tests.xml`: exit0,308 passed in269.61s. This run preceded the final spoken-number extension.
- `python -m pytest backend/tests/test_price_query.py backend/tests/test_catalog_search.py backend/tests/test_api_search.py backend/tests/test_search_core.py -q --junitxml=artifacts/backend/price-query-final-tests.xml`: final exit0,144 passed in45.73s, after spoken-number changes. One upstream Starlette/httpx warning. Other account/order modules were not changed by the final parser extension.
- `python scripts/verify_price_queries.py`: final exit0,39 real local HTTP/CPU encoder checks,0 speech calls. Raw price-query-real-encoder.json includes response IDs, products/prices/scores, model/index/catalog fingerprints, query-photo hash and fixture hash. Checks compare semantic/hybrid bounds and unchanged cosine for enabled/disabled price parsing across text/voice/manual-transcript/multimodal/image. This is exploratory constraint/property evaluation, not frozen independent relevance quality.
- `python scripts/verify_architecture.py`: exit0,38 source files/2 negative fixtures; AST only. `python -m ruff check backend/app backend/tests/test_price_query.py backend/tests/test_catalog_search.py scripts/verify_price_queries.py`: exit0.
- Frontend build/TypeScript, lint and17unit tests passed. Build/lint rerun after catalog checkbox navigation synchronization fix.
- With PLAYWRIGHT_BROWSERS_PATH=<workspace>/runtime/browsers, `npx playwright test e2e/price-query.spec.ts`: initial2 pass/1 fail on checkbox state during asynchronous URL navigation. Changed catalog checkbox to urgent local state synced with URL; added stock toggle regression. Final3 passed in6.5s, exit0, including real AI API and both surfaces at360/768/1440 with axe0/no overflow. Initial and final JSON retained. Inspected mobile/catalog and desktop/search screenshots; no further visual edits.
- After spoken-number extension, `npx playwright test e2e/price-query.spec.ts --grep 'manual transcript'`: exit0,1 passed in1.2s. Uses edited transcript/real voice search mode; no STT request. No final combined4-test suite claim.
- `npx playwright test e2e/browse-recovery.spec.ts e2e/browse.spec.ts --grep-invert 'responsive screenshots'`: exit0,13 passed in7.5s. URL/history, sorting/facets, lexical aliases/SKU/typo, stale responses, price validation and real hybrid encoder regression.

## What is established

Numeric/localized/spoken VND amounts and strict/inclusive boundaries; overlapping budgets intersect; range clauses/SQL and markup remain literals; ambiguous/grouping/unsupported-currency/OR/conflicting inputs fail explicitly; disabled mode preserves literal text; SKU cannot bypass inferred budget; facets/suggestions apply price before pagination; original cosine remains separate from RRF. Logic tests use explicit doubles where appropriate, while the39-check script and browser search use actual CPU encoder/index.

All modifications remain within assignment6_demo. No supplied credential is written; runtime/models/env/dependencies/build/traces stay ignored. No paid API, Azure resource modification, public deployment or STT provider call. Overall goal remains active; docs25 lists pending modules/gates and deliberately does not extrapolate these tests to all query intents or catalog correctness.
