# Localhost startup — 2026-10-15

Source: `e1f7b78f6636ec6c3d9c9756fed450a536cb197c` (`main`).

Followed `docs/36_RUN_ON_ANOTHER_MACHINE.md` and `docs/35_DEMO_HANDOFF.md`.

- `git pull --ff-only`: exit 0, fast-forward to latest origin/main.
- `scripts/setup_demo.ps1`: backend setup, dataset validation, pinned model download and real CPU index build succeeded. SQLite importer returned `applied: false`: existing snapshot retained, 181 products, 30 historical orders, 183 inventory rows, 2 size variants. Existing demo credentials preserved. Frontend installation initially failed with Windows EPERM because an existing project Vite preview process held esbuild/Rollup files.
- Stopped the identified project preview/esbuild processes. Retried `npm ci` and `npm run build`: exit 0; npm audit reported zero vulnerabilities.
- Started `scripts/run_backend.ps1` and `scripts/run_frontend.ps1 -Preview` as hidden background processes. An earlier duplicate backend launch encountered occupied port 8000; the identified old project backend was then restarted successfully.
- `PLAYWRIGHT_BROWSERS_PATH=runtime/browsers node runtime/verify-local.cjs`: exit 0 before speech credential update. See `checks.json` for latest rerun results and timestamp. Checks use the actual application, SQLite and CPU encoder: search, catalog with real image, desktop/mobile overflow, user/admin browser login/logout, admin overview, user historical order, cart, wishlist and purchase history. No new purchase or stock modification performed.
- User-supplied Groq key saved only in ignored `.env`, with `SPEECH_PROVIDER=groq`; backend restarted to load it. Key value never included in evidence. No paid speech call made and current key validity is not live verified. No Azure call made.
- Repeated browser smoke after the credential update: exit 0; `/api/v1/meta` reports Groq `configured_unverified`, language `vi-VN`.
- Created two additional local demo accounts with easier credentials at the user's request; verified both roles through the real login API (HTTP 200). Credentials remain only in ignored `runtime/demo/simple-access.json`. New user has separate business data; historical C001 ownership remains with the original demo user.

Website: http://localhost:5173/. API: http://127.0.0.1:8000/docs.
Credentials: ignored local file `runtime/demo/access.json`.
Server logs: `runtime/backend-local-current*.log`, `runtime/frontend-local-current*.log`.

Browser startup smoke passed; visual regression, independent relevance quality, physical microphone and current Groq key live transcription are not certified by this run.

## Self-evaluation

| Axis | Score | Evidence / improvement |
| --- | --- | --- |
| Accuracy | 4 | Real API/browser checks and setup exit codes recorded; current speech key not live tested. |
| Completeness | 4 | Pull, dependencies, database, frontend/backend and local speech configuration completed; no fresh checkout/payment journey rerun. |
| Clarity | 4 | URLs, credentials location and limitations documented; setup recovery adds operational detail. |
| Actionability | 5 | Servers remain running and local account file enables immediate use. |
| Conciseness | 4 | User-facing handoff is short; report preserves extra recovery detail. |

Overall: 4.2/5. Improvement: validate a user-initiated voice recording with the configured key. The user should agree that the website is usable while this live-provider check remains separate.
