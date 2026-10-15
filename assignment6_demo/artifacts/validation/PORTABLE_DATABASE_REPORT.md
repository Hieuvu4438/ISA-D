# Portable demo database handoff — 2026-10-15

Scope: reproducible public demo data on a new Windows checkout. Private existing accounts, sessions and runtime purchase history are not exported to Git. No paid speech calls or Azure calls made during these checks.

## Data and implementation

- Canonical catalog now matches the active 181-product runtime catalog, including P181 metadata, photo and provenance. The previous 180 product records were unchanged in this promotion.
- `data/demo_database.json`: 183 inventory rows, two P041 size variants, 181 sale states; schema/fingerprint validation before import. A transaction and snapshot marker prevent repeated setup resetting later business activity. A previously used, unmarked database is refused.
- Fresh operational SQLite schemas plus new random demo credentials; the demo user owns C001 historical orders. No original SQLite/password hashes/credentials copied into the isolated checkout.
- Catalog fingerprint: `d63667407ac0faba690181f90b47f528aad6594a4cdbd30634c0e0ba909ba45f`.
- Real CPU index fingerprint: `1903765b5e724df63aa88b6e58332db58784bea00fa0dd6879e21c9bf4388b17`.
- Model fingerprint: `8079066fd176407685d890a0d3ecf86c795ab8256019c955ad70e1cbea986ab2`.
- Import snapshot digest: `4526f0c9b2dd93f362b65df70ff0181ebd0c0f4af2729cd5766777421b8ddca7`.

## Executed checks

All commands below exited 0:

```powershell
.\backend\.venv\Scripts\python.exe scripts/update_image_credits.py
.\backend\.venv\Scripts\python.exe scripts/validate_dataset.py
.\backend\.venv\Scripts\python.exe scripts/build_index.py
.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_demo_database.py backend/tests/test_data.py backend/tests/test_catalog_repair.py backend/tests/test_catalog_search.py backend/tests/test_scope_query.py backend/tests/test_color_scope.py backend/tests/test_size_scope.py -q --basetemp=runtime/tests/portable-db --junitxml=artifacts/validation/portable-database-tests.xml
```

Result: **156 passed, 11.19s**, one upstream Starlette/httpx deprecation warning. Tests cover import completeness, repeated import preserving edited stock, refusal to overwrite existing stock, invalid snapshot rejection before creating SQLite, roles, product media and historical order ownership.

Copied tracked/new application source into ignored `runtime/demo/portable-checkout`, excluding old runtime, credentials and `.env`. Set `APP_ROOT` to that root and executed its `scripts/import_demo_database.py` and `scripts/prepare_demo.py` twice using the existing backend Python environment: all exit 0. First import `applied=true`, second `false`; counts 181/30/183/2 and credentials remained stable. Built actual CPU index with `scripts/build_index.py --root runtime/demo/portable-checkout`, exit 0.

Started the exported backend with uvicorn `--app-dir runtime/demo/portable-checkout/backend` on port 8002. HTTP checks against this actual fresh database all passed, process exit 0: both logins; user admin access 403/admin 200; own O001 200/foreign O002 404; P181 photo bytes matching source; P041-M=3/L=2; real CPU search for apparel size M; add P041-M to cart, quote, create COD 201, read own order, cancel and verify stock restored. Sanitized results: [portable-database-http.json](portable-database-http.json). Test server stopped after verification.

PowerShell setup script parsed successfully. Dependencies/models were reused from local caches for the isolated test; this is not evidence of a full fresh Internet install or a second physical machine. The complete setup script orchestrates existing locked installation, model download, build and the individually verified import/account commands. No new browser test was needed for this database/setup change; previous demo browser evidence remains in [DEMO_HANDOFF_REPORT.md](DEMO_HANDOFF_REPORT.md).

Run instructions and limits: [docs36](../../docs/36_RUN_ON_ANOTHER_MACHINE.md). Research relevance/OOD and Azure verification remain outside this demo handoff.
