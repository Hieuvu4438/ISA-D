# Public Vercel demo — 2026-10-15

User explicitly authorized Vercel public deployment and confirmed a local backend is acceptable for shared demo use.

- Public frontend: **https://cortis-demo.vercel.app**.
- Project: `hieuvus-projects-eea5c248/cortis-demo`.
- Deployment: `dpl_vEuFEgFJ6YAPki72qvJzzfub2nkF`, READY, production alias assigned.
- Deployment URL: `https://cortis-demo-cb4khgouf-hieuvus-projects-eea5c248.vercel.app`.
- Backend: FastAPI on localhost8003, real pinned CLIP CPU models and public demo SQLite under ignored `runtime/public-demo/app`; HTTPS via cloudflared2026.10.0.
- Vercel CLI64.1.0 installed under ignored runtime; device login completed. Only 437.2KB of built frontend/assets/config uploaded. No model, Python environment, database, credentials or key uploaded.
- Git auto-deployment disconnected explicitly after CLI automatically connected the parent repository; later source pushes cannot replace the packaged deployment with an incorrect monorepo-root build.

## Executed verification

`npm.cmd run build` in frontend exited0. `prepare_public_demo.py` imported181products/30historicalorders/183inventoryrows/2variants into a fresh, separate SQLite and generated random public admin/user credentials. No original local commerce database or account copied. Model files shared by hard links, index copied from the already verified seed build. Existing local port8000 was left running separately.

`prepare_vercel_site.py --backend-url <HTTPS tunnel origin>` exited0; `--update-proxy` verified exit0. Packaged only frontend/dist plus Vercel routing config under ignored runtime. Same-origin proxy routes `/api/*` and `/health/*`, disables caching, serves static assets and falls back to index.html for SPA links. Public backend configured with exact frontend origins and secure cookies. Groq key copied only between ignored local environment files; no speech calls made.

`vercel deploy runtime/public-demo/site --yes --name cortis-demo --prod --global-config <ignored local config> --no-color` exited0, deployment READY and production alias assigned. `vercel git disconnect --yes --cwd <site package> --global-config <ignored local config>` exited0.

Public browser command, executed against Vercel and its actual tunneled backend (no mock API):

```powershell
cd frontend
$env:PUBLIC_DEMO_URL='https://cortis-demo.vercel.app'
$env:PLAYWRIGHT_BROWSERS_PATH='D:/PROJECTS/ISA-D/assignment6_demo/runtime/browsers'
.\node_modules\.bin\playwright.cmd test --config playwright.public.config.ts
```

Exit0: **5 passed, 21.7s**. Account register/profile/password/logout/login, catalog filtering/sorting/pagination/deep-link reload, real hybrid CPU search, quote/COD/history/cancel/stock restoration, public admin HTTPS login/inventory/catalog management and session persistence. Admin cookie confirmed Secure, HttpOnly, SameSite=Lax. These checks create disposable demo accounts and cancelled demo orders only in the public database. [Browser evidence](vercel-public-browser.json).

Independent HTTP verification through production alias exited0: homepage, catalog deep link, meta and P181 photo HTTP200;181products/searchavailable/model+indexfingerprints; untrusted Origin write403; request for private runtime credentials returned SPA HTML, not credentials. [HTTP evidence](vercel-public-http.json).

Ruff for both new preparation scripts exited0; both PowerShell run scripts parsed without errors; Git diff whitespace check passed. Initial Ruff import-order findings were corrected before final checks. One initial Ruff invocation from frontend used a root-relative Python path and failed to locate Python; the build still succeeded, and Ruff was then rerun successfully from project root. No backend application behavior or API contract changed.

## Runtime dependency and limits

The frontend is public without Vercel login, verified by fresh browser contexts and unauthenticated HTTP. Keep the local machine online/awake and its public backend/tunnel running. Quick Tunnel hostname changes on recreation; update the packaged proxy and redeploy to keep the same frontend alias working. No uptime SLA claimed. No paid backend hosting, public Azure change, Azure live verification or research-quality certification performed. Existing voice evidence remains separate; this deployment did not make paid speech calls.

[Operation/restart/handoff instructions](../../docs/37_VERCEL_LOCAL_BACKEND.md).
