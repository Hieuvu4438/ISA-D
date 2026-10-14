# E3 shopping — cart and wishlist evidence

Contract/module/sequence: [18_CART_WISHLIST.md](../../docs/18_CART_WISHLIST.md). Account-scoped persistent cart/wishlist, quantity/current catalog price and stock validation, optimistic cart concurrency, product/list UI. This milestone is not checkout/full ecommerce acceptance.

## Evidence actually run

Working directory assignment6_demo; npm/Playwright in frontend. All final commands below exit0; full backend result separately in shopping-full-tests.xml and shopping-verification.json.

| Command | Scope/result |
| --- | --- |
| `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_shopping.py -q --junitxml=artifacts/backend/shopping-tests.xml` | **17 passed**, 52.46s, real SQLite/password/session and concurrency checks; catalog-change fixture uses explicit double |
| `backend/.venv/Scripts/python.exe -m pytest backend/tests -q --junitxml=artifacts/backend/shopping-full-tests.xml` | **191 passed**, 206.40s, exit0; one upstream Starlette/httpx deprecation warning |
| `backend/.venv/Scripts/python.exe -m ruff check backend/app backend/tests/test_shopping.py` | Passed |
| `backend/.venv/Scripts/python.exe scripts/verify_architecture.py` | 29 files passed AST direction check; no full conformance/.vpp claim |
| `npm run build`, `npm run lint`, `npm run typecheck`, `npm test` | Production build/typecheck/lint passed; **17 frontend unit tests passed** |
| `npx playwright test e2e/shopping.spec.ts` | **4/4 passed**, 13.3s, production preview + real HTTP API, no mocked responses |
| `npx playwright test e2e/shopping.spec.ts --grep 'product save\|anonymous recovery\|stale cart\|late wishlist'` | **4/4 passed**, 7.7s; adds late-read/expired-session behavior after minor title/aria-busy changes |

Playwright browser stored under ignored runtime with workspace PLAYWRIGHT_BROWSERS_PATH. Current backend restarted from verified prior process, production Vite preview launched locally. No public deployment. Historical e2e-results.json preserved; [shopping-e2e-results.json](../frontend/shopping-e2e-results.json) and [shopping-functional-results.json](../frontend/shopping-functional-results.json) contain milestone results.

Initial frontend test run had one failure: old detail-page test asserted every API read was product detail, while new saved-state control reads wishlist. Updated the double to return an empty list and assert the two authorized read endpoints; the late product-response cancellation assertion is preserved. Final 17 tests passed. No quality labels changed.

## Behavior covered

- Backend: cart total from catalog, stock unchanged/no reservation; quantity and version strict validation; desired-state no-op and stale conflict; zero removal; missing/out-of-stock/quantity beyond stock; wishlist idempotency/capacity; per-user isolation and session rotation; auth/logout/CSRF/origin/query forgery; concurrent same-version mutation has one winner; persisted cart accessible after app restart; read recomputes changed catalog price and flags missing/insufficient-stock items; discontinued line remains removable.
- Real Chromium/API: register → product wishlist save → wishlist add cart → quantity update → correct subtotal → reload persists → cart remove → wishlist persists separately → unsave/empty. Anonymous login recovery and sold-out disabled. External same-session update simulates another tab; stale form gets409, reloads other-tab quantity, does not overwrite. Delayed initial wishlist GET uses real route.fetch response delayed for race timing, not mocked payload; save remains active. Logout then mutation clears private wishlist state and offers login.
- UI: 360/768/1440 cart/wishlist/product screenshots, all three pages zero axe violations/no horizontal overflow; inspected cart mobile, wishlist desktop and product mobile with view_image. Only one visual inspection pass; no synthetic catalog assets introduced.

## Limits/pending

Full dataset visual gate remains failed/pending under17. Shopping uses current validated JSON process snapshot, not live warehouse stock; cart does not reserve, checkout is not implemented and no successful paid order is claimed. Variant/size-level inventory, checkout/COD/idempotency/stock+order atomicity, order history/cancel/returns, full admin/audit, independent quality/OOD benchmarks, `.vpp`, and provider-specific real voice regression remain required. New tables are ignored runtime SQLite; test/demo account details and session tokens are not committed. No live STT/model quality calls in this milestone; encoder tests elsewhere do not prove shopping/voice live functionality. Goal remains active.
