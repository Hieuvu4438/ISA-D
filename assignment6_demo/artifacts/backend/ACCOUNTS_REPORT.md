# E1 — account/session/role verification

Scope: local persisted SQLite identities and real account HTTP API, UI, order ownership, role gate. Source/dataset hashes, versions and results: [accounts-verification.json](accounts-verification.json). Full backend JUnit: [accounts-tests.xml](accounts-tests.xml). Browser raw report: [accounts-e2e-results.json](../frontend/accounts-e2e-results.json). UI screenshots: `../frontend/screenshots/accounts/account-{360,768,1440}.png`; desktop/mobile inspected visually.

## Commands actually executed

Working directory `assignment6_demo` unless frontend noted. Successful commands exit 0.

| Command | Result |
| --- | --- |
| `uv venv backend/.venv --python 3.12` | Installed CPython 3.12.13 and isolated environment |
| `uv pip install --python backend/.venv/Scripts/python.exe -r backend/requirements.lock.txt` | Exit 1: uv first-index lookup could not resolve certifi pinned on CPU index |
| `uv pip install --python backend/.venv/Scripts/python.exe --index-strategy unsafe-best-match -r backend/requirements.lock.txt` | Exit 0: installed 70 locked packages; both configured package indexes considered |
| `uv pip install --python backend/.venv/Scripts/python.exe --no-deps -e backend` | Exit 0: app installed editable |
| `backend/.venv/Scripts/python.exe -m pytest backend/tests -q --junitxml=artifacts/backend/accounts-tests.xml` | **133 passed**, 148.98s; one upstream Starlette/httpx deprecation warning |
| `backend/.venv/Scripts/python.exe -m ruff check backend/app backend/tests/test_accounts.py scripts/create_account.py` | Passed after unused import/lambda/import ordering fixes |
| `backend/.venv/Scripts/python.exe scripts/verify_architecture.py` | AST direction check passed for 24 files; limits retained in architecture.json |
| `backend/.venv/Scripts/python.exe scripts/create_account.py --help` | Passed, no credential/provider call |
| `npm ci` (frontend) | 223 packages, audit 0 vulnerabilities |
| `npm run typecheck`, `npm run lint`, `npm test`, `npm run build` (frontend) | Exit 0 each; **17 unit tests passed**; production build created |
| `npx playwright install chromium` (frontend), workspace PLAYWRIGHT_BROWSERS_PATH | Browser installed under ignored runtime |
| `backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000` | Live backend started; no model files configured |
| `npm run preview` (frontend) | Production frontend served on 127.0.0.1:5173 |
| `npx playwright test e2e/accounts.spec.ts` (frontend) | **2 passed**, 19.3s, API not mocked; axe zero violations, no horizontal overflow at 360/768/1440 |
| `git diff --check`, `git check-ignore` env/venv/node_modules/dist/runtime DB | Clean whitespace; sensitive/runtime/generated paths ignored |

Initial test invocations before environment setup failed because venv/tsc absent; corrected by clean installs. One Playwright CLI invocation used an unquoted comma reporter argument interpreted by PowerShell as `list json`; exit 1 before tests, rerun with configured reporter above. Historical e2e-results.json retained; E1 results saved to distinct report.

## Behavior verified

Backend tests use real SQLite and password hashing; inference doubles in existing tests do not prove AI quality. Checks cover registration persistence across app restart, canonical duplicate email and race, extra-field/role/customer forgery, separate user/admin privileges, explicit C001 ownership, foreign/missing order privacy, expiry/session replay, login rotation, logout revocation, profile validation, password change and revoking other sessions, CSRF origin/intent, rate-limit quota concurrency, Secure/HttpOnly cookie/CORS.

Real Chromium + real HTTP API: register, reload with retained session, profile save, password change, logout, old password rejected, new password accepted, user denied admin/C001 orders. Anonymous order detail recovers through login link. Login layout inspected at mobile and desktop, axe tested at all three widths. DB generated only in ignored runtime; test accounts use reserved example.test addresses.

## Pending and limits

E1 does not establish full ecommerce stability. Hybrid search, richer filters/facets/sort, variants/cart/wishlist/checkout/order list/mutations/returns, full admin CRUD/audit and full-system acceptance remain pending under docs/15. Existing browser/scripts assuming anonymous C001 must migrate to explicit owner fixtures before their results can count for the new contract. No real model index/quality, provider live call, Azure or Groq validation performed in this milestone. Existing provider reports are historical evidence only. Editable `.vpp` still pending. Goal remains active.
