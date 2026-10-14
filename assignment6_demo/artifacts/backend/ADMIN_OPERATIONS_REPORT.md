# Admin operations verification

Date: 2026-10-15. Base commit: `31e7470`. Scope: local Cortis operational administration, real SQLite persistence and browser/API integration; COD demo only.

## Implemented

Admin-only stock adjustments, paginated order/account/audit views, private shipping detail, fulfillment transitions and account role updates. Mutations recheck actor role under the SQLite write lock. Stock revision/account version/order version protect competing writes. State changes and append-only application audit commit or roll back together. Role changes revoke target sessions. Cancellation restores inventory once; shipped/delivered orders cannot be cancelled. Delivery does not assert payment collection.

## Commands and results

Commands use `backend/.venv/Scripts/python.exe`; frontend commands run in `frontend`.

- `python -m pytest backend/tests/test_admin_operations.py backend/tests/test_accounts.py -q --junitxml=artifacts/backend/admin-operations-tests.xml`: exit0, 19 passed.
- `python -m pytest backend/tests -q --junitxml=artifacts/backend/admin-full-tests.xml`: exit0, 214 passed. This full run preceded the final OpenAPI/dependency-error and stricter reason/version validation changes; the final targeted suite covers those amendments.
- `python -m pytest backend/tests/test_admin_operations.py -q --junitxml=artifacts/backend/admin-final-targeted-tests.xml`: exit0, 12 passed in 38.98s, including final schema/dependency amendments; adjacent XML and admin-verification.json retain results.
- `python -m ruff check backend/app backend/tests/test_admin_operations.py scripts/admin_browser_fixture.py`: exit0. Architecture AST: 35 source files, passed; not editable UML verification.
- `npm run typecheck`, `npm run lint`, `npm run build`, `npm test`: exit0; 17 unit tests passed.
- `npx playwright test e2e/admin.spec.ts`: first round 3 passed/1 failed (role select accessible label); fixed explicit label association. Second round 3 passed/1 failed (reused audit reason matched earlier fixture); fixed unique per-run reason. Raw initial/confirmation reports are retained in artifacts/frontend.
- `npx playwright test e2e/admin.spec.ts --grep 'real admin'`: exit0, 3 functional tests passed, including real stock/stale-write/audit, role/session revocation and COD fulfillment. Raw admin-functional-results.json retained.
- Anonymous denial and responsive inventory checks passed separately in both browser rounds, at 360/768/1440 pixels with no horizontal overflow and zero axe violations. Screenshots retained in artifacts/frontend/screenshots/admin. The final functional-only run does not represent a final 4/4 full browser suite.

The backend tests exercise permission denial, commit-time role recheck, concurrent stock/cancellation, stale versions, audit-insert rollback, private detail, strict schema/query rejection and catalog dependency failures. Test doubles disable model loading for these business logic checks; browser uses the local application server and actual SQLite APIs. No model quality or voice provider claim follows from these checks.

## Fixtures and boundaries

Browser administrators are explicitly provisioned only by the manual fixture command with random ephemeral credentials; no startup/CI default admin. After test cleanup, reserved fixture accounts have no active administrator privileges or sessions; see admin-fixture-retirement.json. Credentials are omitted from reports. Runtime DB/models/env/build output remain ignored.

Product metadata/assets CRUD, index rebuild/publication, variants/sizes, account lock/delete, returns/refunds, catalog photo cleanup, independent frozen quality gates, editable .vpp and provider-specific live speech evidence remain pending. E5 and the overall project are not complete. Public deployment and Azure resource changes were not performed.
