# E4 checkout/order/inventory verification

Implementation contract: [19_CHECKOUT_ORDERS.md](../../docs/19_CHECKOUT_ORDERS.md). Real local SQLite order placement/stock ledger/cart transaction/COD demo, quote, history/detail/cancel and browser recovery. No payment or logistics provider call, no live speech recognition performed. Goal remains active.

## Executed commands and results

Root assignment6_demo, frontend commands in frontend. Successful commands exit0. Versions/source fingerprints/results in checkout-verification.json; runtime DB/model/dependencies/browser/build output excluded from Git.

| Command | Result/scope |
| --- | --- |
| `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_purchases.py backend/tests/test_shopping.py -q --junitxml=artifacts/backend/checkout-tests.xml` | **28 passed**, JUnit time92.295s, no failures/errors. Original process handle disappeared after continuation; terminal result revalidated from existing authoritative JUnit, not restarted based on timeout |
| `backend/.venv/Scripts/python.exe -m pytest backend/tests -q --junitxml=artifacts/backend/checkout-full-tests.xml` | **202 passed**, 170.84s, one upstream Starlette/httpx deprecation warning |
| `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_purchases.py -q --junitxml=artifacts/backend/checkout-adversarial-tests.xml` | **12 passed**,22.05s, including newly added concurrent same-key checkout/cancellation and foreign quote ownership. Overlaps full suite, do not add counts |
| `backend/.venv/Scripts/python.exe -m ruff check backend/app backend/tests/test_purchases.py` | Passed |
| `backend/.venv/Scripts/python.exe scripts/verify_architecture.py` | AST direction check32 files passed; full architecture/.vpp pending |
| `npm run typecheck`, `npm run lint`, `npm test`, `npm run build` | Passed,17 frontend unit tests, production assets built |
| `npx playwright test e2e/checkout.spec.ts` | **4 passed**,10.3s, real API, including responsive/axe |
| `npx playwright test e2e/checkout.spec.ts --grep 'quote, COD placement'` | **1 passed**,2.2s after adding ORD lookup/title; functional addition |
| `npx playwright test e2e/checkout.spec.ts --grep 'real inventory ledger'` | **1 passed**,1.8s, real CPU encoder + real stock ledger |
| `npx playwright test e2e/checkout.spec.ts --grep-invert 'responsive/accessibility'` | **4 passed**,8.1s, final functional batch including lost response/address recovery/lookup/inventory |

Raw browser reports [checkout-e2e-results.json](../frontend/checkout-e2e-results.json), [checkout-functional-results.json](../frontend/checkout-functional-results.json), [checkout-inventory-results.json](../frontend/checkout-inventory-results.json); historical e2e-results.json preserved. Screenshots `../frontend/screenshots/checkout/checkout-{360,768,1440}.png` zero axe violations/no document overflow. Mobile/desktop inspected with view_image, no additional visual polish loop. A PowerShell stdin edit initially corrupted new page-title text to question marks; restored using UTF-8 apply_patch and rebuilt/typechecked before final functional checks.

After adding explicit OpenAPI pagination parameters, an actual in-process API smoke checked limit/offset schema, extra-forbid purchase body and anonymous quote401; report checkout-schema-smoke.json, exit0, no model/provider. Full202 suite ran before the additional concurrency test/schema-only amendment; targeted12 and schema smoke cover those additions. Do not claim203 full-suite execution.

## Behavior actually covered

- Real SQLite: current-price quote with shipping total, cart empty/changed, quote expiry/supersession, price drift, idempotency replay/conflict, persistent stock/keys across app restart, owner privacy and strict authority/schema/CSRF, last-item concurrent checkout one winner, mid-line failure rollback, forced SQL INSERT abort rollback of stock/cart/order, cancel state/version conflict and restock once. Additional targeted test submits same idempotency key concurrently and cancels concurrently; both replay paths must leave one order/one decrement/one restoration. Direct SQL status fixture only tests rejection of shipped state, not a working admin fulfillment UI.
- Real browser/API: cart→explicit quote→address→COD confirm→persisted detail reload→history→lookup ORD→cancel. All addresses used reserved demo strings/phone fixture, no real customer data. Result COD unpaid/demo, not charged or delivered.
- Lost response test uses `route.fetch()` to actually commit on server, then aborts only delivery to browser. Explicit retry reuses frozen body/key, returns same order and history total1; stock decremented once. Not a mocked success payload.
- Stale quote after cart version change produces409, re-quote keeps submitted address and recalculates fee/total. Successful cancel restores original quantity.
- Real model/inventory integration: purchase every remaining P001 unit, run actual CPU hybrid exact-SKU + in_stock query→results empty; browse in_stock excludes SKU and product detail marks sold out; index fingerprint unchanged. Cancel in finally restores quantity. This proves stock-filter integration on that SKU, not broad independent AI quality or OOD calibration.

## Limits and remaining work

Full catalog visual/metadata gate still pending17; variants/size ledger, admin inventory reconciliation/product/user/fulfillment/audit, return/refund flows, real payment/logistics, independent frozen model/OOD/calibrations, editable .vpp and provider-specific live Vietnamese fashion voice regression remain required. COD demo is actual local persistence, no external commerce transaction. Existing O001… JSON histories remain separate demo ownership; new account history is persisted ORD orders. Inventory seed is imported once and intentionally not reset by JSON changes; controlled inventory reconciliation is an upcoming admin requirement. Full ecommerce not marked complete.
