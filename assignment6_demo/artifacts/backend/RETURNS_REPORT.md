# Returns verification

Date2026-10-15, basec9c6a1d. Contracts/rules/UML sequence: docs/23_RETURNS.md. Scope: operational demo returns, owned cumulative quantities/30-day window, approvals/rejection/withdrawal, inspection/restock/quarantine, immutable demo value and atomic audit.

## Executed commands

- `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_returns.py backend/tests/test_admin_operations.py -q --junitxml=artifacts/backend/returns-targeted-tests.xml`: exit0,21 passed in84.79s. Before fixture-import cleanup; full run below covers final backend/test sources.
- `backend/.venv/Scripts/python.exe -m pytest backend/tests -q --junitxml=artifacts/backend/returns-full-tests.xml`: exit0,224 passed in199.08s. One upstream Starlette/httpx deprecation warning. No backend changes afterward.
- `python -m ruff check backend/app backend/tests/test_returns.py`: final exit0. Initial fixture import shadowing was replaced with explicit isolated fixture; semicolon lint removed.
- `python scripts/verify_architecture.py`: exit0,37 sources/2 negative fixtures; AST only, not full conformance/editable UML.
- Frontend `npm run build`, `npm run lint`, `npm test`: exit0,17 unit tests. Build includes TypeScript and was rerun after final CSS.
- With PLAYWRIGHT_BROWSERS_PATH=<workspace>/runtime/browsers, `npx playwright test e2e/returns.spec.ts`: initial1 pass/1 fail (status selector matched filter option); next1 pass/1 fail (admin heading-order). Fixed selector scope and list h2. Subsequent2 passed, including transport-loss replay, axe0 and no overflow on admin/customer at360/768/1440.
- Screenshot inspection then found collapsed mobile admin text columns. Fixed flex basis/empty column; with CORTIS_RETURNS_FUNCTIONAL_ONLY=1 same command: exit0,2 passed in4.9s, including min260px admin content-width and no overflow at all3 sizes. No more visual/axe loop after final CSS; final visual confirmation remains pending. Pre-fix images are not staged as final evidence.

## Evidence scope

SQLite/HTTP tests cover deadline/fallback delivery, owned privacy, strict inputs/query/intent, partial quantities, replay after expired window, concurrent requests/receipt, no duplicate restock, conflicting receipt denial, audit-trigger rollback, commit-time role check, stale transitions, withdrawn/rejected quantity release, original order/payment/snapshot preservation.

Browser actually commits a return then drops the response; UI reuses the same body/key and one case exists. This controlled network failure uses real persistence; it is not provider/model evidence. Fixtures have random ephemeral credentials; stock restored and reserved roles/sessions retired. returns-fixture-retirement.json confirms0 active privileged fixture accounts and0 sessions.

Raw final/browser chronology and source SHA256: returns-verification.json and artifacts/frontend/returns-browser-*.json. No speech/model-quality run, real payment transfer, exchange shipment, public deployment or Azure change. Overall objective remains active; docs23 lists remaining modules/gates.
