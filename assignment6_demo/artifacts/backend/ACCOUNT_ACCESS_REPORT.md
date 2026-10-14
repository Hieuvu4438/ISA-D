# Account access verification

Date2026-10-15, basea820ebd. Contracts/UML/limits: docs/24_ACCOUNT_ACCESS.md. Scope: admin lock/unlock, shared account version, atomic audit/session revocation, private authentication epoch guards for protected writes, compatible persistence upgrade.

## Executed checks

- `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_accounts.py backend/tests/test_admin_operations.py backend/tests/test_shopping.py backend/tests/test_purchases.py backend/tests/test_returns.py -q --junitxml=artifacts/backend/account-access-regression-tests.xml`: initial exit1,57 passed/1 failed in148.24s. Only failure was the exact admin-users DTO field set still expecting the previous schema. Updated assertion to include access_state alongside updated API/data docs. Raw preserved as account-access-regression-initial.xml.
- `python -m pytest backend/tests/test_account_access.py -q --junitxml=artifacts/backend/account-access-tests.xml`: exit0,21 passed in69.53s. Subsequently added the old-seven-column DB upgrade case; full run below includes22 new access cases.
- `python -m pytest backend/tests -q --junitxml=artifacts/backend/account-access-full-tests.xml`: exit0,246 passed in269.31s. One upstream Starlette/httpx deprecation warning. Final backend/test sources, including upgrade and amended DTO assertion.
- `python -m ruff check backend/app backend/tests/test_account_access.py backend/tests/test_admin_operations.py scripts/admin_browser_fixture.py`: exit0. `python scripts/verify_architecture.py`: exit0,37 source files/2 negative fixtures; AST only, no editable UML/full conformance claim.
- Frontend `npm run build`, `npm run lint`, `npm test`: exit0; TypeScript included in build,17 unit tests passed.
- With PLAYWRIGHT_BROWSERS_PATH=<workspace>/runtime/browsers, `npx playwright test e2e/account-access.spec.ts`: exit0,2 passed in9.9s. Actual local application API/SQLite, independent buyer sessions. One batched screenshot/axe/no-overflow/content-width check at360/768/1440; zero axe violations, min260px content width. Inspected mobile/desktop screenshots and made no subsequent UI edits.
- `npx playwright test e2e/accounts.spec.ts e2e/admin.spec.ts e2e/checkout.spec.ts --grep-invert 'accessibility|responsive'`: exit0,8 passed in17.5s. Covers profile/password/session rotation, role promotion, stock/fulfillment, COD checkout/cancel/history, lost-response replay, stale quote and final-stock encoder agreement. This is functional regression, not a full-system visual run.

## Evidence scope

Tests establish private generic login failure for locked/wrong/missing accounts; all session revocation, fresh auth after unlock, unchanged cart; no self lock; shared version prevents role/access lost writes; no-op semantics; audit failure rolls back state/version/epoch/session deletion; active-admin guard; concurrent role/access conflict; nine customer and five admin HTTP mutations reject identity snapshots captured before lock-unlock; password/login snapshots cannot issue sessions after revocation; explicit legacy-schema upgrade and persisted locked state across restart.

HTTP interleaving tests use a controlled identity hook to perform real SQLite lock/unlock between identity capture and the actual route mutation. Concurrency tests use threads and actual SQLite write locks. No model/provider quality claim derives from these business tests. Existing checkout E2E invokes real CPU encoder for an integration smoke check only; no independent quality evaluation or speech provider call in this milestone.

Browser fixtures use random ephemeral credentials. Reserved role/session retirement uses the same epoch invalidation helper; account-access-fixture-retirement.json confirms zero privileged reserved accounts, zero reserved sessions and zero locked access fixtures after all runs. Data/DB/models/env/node_modules/build and traces stay ignored. Source fingerprints and raw test statistics are in account-access-verification.json.

Overall objective is incomplete: product variants, metadata/assets CRUD/index publication, account deletion/anonymization, exchange/refund integration, data/photo repair, independent quality/provider-specific live speech, editable .vpp, clean checkout acceptance and the separate returns final visual confirmation remain pending. No public deployment or Azure resource change.
