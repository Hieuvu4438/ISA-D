# E2 — real hybrid search and browsing evidence

Code/contract: [docs/16_SEARCH_BROWSE.md](../../docs/16_SEARCH_BROWSE.md). Goal remains active. Verified behaviors below do not establish full ecommerce readiness.

## Results and exact scope

- Full backend: **170 passed**, 150.25s, exit0; [e2-search-full-tests.xml](e2-search-full-tests.xml). One upstream Starlette/httpx deprecation warning. Subsequent OpenAPI-only amendment: catalog suite **36 passed**, 2.20s, exit0; [catalog-openapi-tests.xml](catalog-openapi-tests.xml). Earlier focused search/catalog suite: **55 passed**, 74.40s, exit0; [search-browse-tests.xml](search-browse-tests.xml). Counts overlap, do not add them together. Encoder doubles prove logic/errors, not AI quality.
- Frontend typecheck/build/lint: exit0. Unit tests: **17 passed**. UI extends established Cortis styles, original product assets, Vietnamese keyboard semantics.
- Real production-preview browser: **8/8 passed**, 16.6s: [browse-e2e-final.json](../frontend/browse-e2e-final.json), including account regression, browser lifecycle, facets/sort/pagination/URL reload+Back, alias/typo/SKU, autocomplete, request race, real hybrid encoder, responsive/axe. Initial failures **2 passed/4 failed** retained in [browse-e2e-initial.json](../frontend/browse-e2e-initial.json): label included select option text, missing h2, two incorrect test locators/count assumptions. Fixed label/heading and corrected mechanics expectations against authoritative catalog; relevance labels never changed.
- Final functional checks after avoiding full catalog fetch on browse/product/account routes and preserving product return URL: **5/5 passed**, 4.6s, [browse-functional-final.json](../frontend/browse-functional-final.json). Checks explicitly assert no `/products` list request on browsing, correct detail breadcrumb URL and ArrowUp/Down autocomplete wrap. Interim functional failure retained in browse-functional-initial.json: option locator accidentally selected a native sort option; narrowed to suggestion listbox. No extra visual polish iteration.
- Desktop/mobile visual pass inspected existing screenshots, fixed header/category density and heading/label, confirmed 360/768/1440 with **zero axe violations/no document overflow**. Screenshots under `artifacts/frontend/screenshots/browse/`; offscreen lazy images are not proof every image decoded/was reviewed.
- Real CPU model: pinned downloads and index built for 180 products, exit0. [index-build.json](index-build.json) records array/image/model hashes. [search-expansion-real-model.json](search-expansion-real-model.json): **50 real HTTP requests**, no mocked encoder, no STT/provider calls. 24 text shopping intent cases tested twice with semantic/hybrid; 2 image/multimodal real-photo upload mechanics checks.
- Semantic text category Hit@3: standard **9/12**, variant **7/12**. Hybrid: standard **12/12**, variant **12/12**. Fixtures written before execution, sha256 `0c2190b4c6685880720a5143e8933b656da7534daa43ba9d494f827c71826e27`; unchanged labels. This small synonym/category smoke is **not** an independent frozen60 multimodal quality/OOD evaluation. Catalog-image self-match mechanics do not prove independent image relevance.

Model fingerprint: `8079066fd176407685d890a0d3ecf86c795ab8256019c955ad70e1cbea986ab2`. Index fingerprint: `8f0419c620ae62b207ee7a4ddce6706d42c885b09b2c74ea31dfdba45710d373`. Real models CPU ViT-B-32 + multilingual DistilBERT pinned per docs05, scrypt account DB separate. Runtime/model/NPZ/env/browser/dependencies excluded from Git.

## Commands actually run

Root `assignment6_demo`, frontend commands run in `frontend/`:

```powershell
./backend/.venv/Scripts/python.exe scripts/download_models.py
./backend/.venv/Scripts/python.exe scripts/build_index.py
./backend/.venv/Scripts/python.exe -m pytest backend/tests/test_catalog_search.py backend/tests/test_api_search.py -q --junitxml=artifacts/backend/search-browse-tests.xml
./backend/.venv/Scripts/python.exe scripts/verify_search_expansion.py
./backend/.venv/Scripts/python.exe -m pytest backend/tests -q --junitxml=artifacts/backend/e2-search-full-tests.xml
./backend/.venv/Scripts/python.exe -m pytest backend/tests/test_catalog_search.py -q --junitxml=artifacts/backend/catalog-openapi-tests.xml
./backend/.venv/Scripts/python.exe -m ruff check backend/app backend/tests/test_catalog_search.py scripts/verify_search_expansion.py
npm run typecheck
npm run lint
npm run build
npm test
$env:PLAYWRIGHT_BROWSERS_PATH = 'D:/PROJECTS/ISA-D/assignment6_demo/runtime/browsers'
npx playwright test e2e/browse.spec.ts e2e/accounts.spec.ts
npx playwright test e2e/browse.spec.ts --grep 'catalog API|lexical retrieval|suggestions|bad price|real encoder'
```

Backend restarted from verified previous local process into current app with real model/index. Existing Vite production preview reused, serving rebuilt dist. No public deployment/Azure resource mutation. Historical e2e-results.json retained; milestone reports stored separately.

## Current-state audit findings and pending

**Dataset gate fails independently of API tests.** Visual inspection found P147 academic infographic and P141/P143–146 inaccurate product metadata. [catalog-review-findings.json](catalog-review-findings.json) records observable mismatches and identical byte-image groups. Previous import marks real_photo_review=passed automatically from plan, so that marker alone cannot establish provenance/visual correctness. Catalog metadata needs full audit and replacement/correction using real sourced photos before overall acceptance. Existing photos were used in this milestone, no generated/synthetic catalog assets added. The 24-category improvement does not prove color/brand accuracy.

Pending scope: natural-language price/brand/negation/size interpretation, ambiguous/multiple typos, independent image/multimodal/OOD evaluation/calibrated policies, variants/size facets, dataset correction, concurrency/cold performance, old anonymous-C001 browser fixture migration, cart/checkout/order mutations/full admin, editable .vpp and live-provider regression. New sorting/reranking is not proof baseline thresholds are calibrated for hybrid Hit@3. No Azure/Groq/local live STT evidence produced here.
