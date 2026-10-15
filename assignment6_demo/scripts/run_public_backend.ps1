param([int]$Port = 8003)
$ErrorActionPreference = 'Stop'
$demoRoot = Split-Path $PSScriptRoot -Parent
$publicRoot = Join-Path $demoRoot 'runtime/public-demo/app'
if (-not (Test-Path -LiteralPath (Join-Path $publicRoot 'runtime/demo/access.json'))) {
    throw 'Run scripts/prepare_public_demo.py first.'
}
$previousRoot = $env:APP_ROOT
try {
    $env:APP_ROOT = $publicRoot
    & (Join-Path $demoRoot 'backend/.venv/Scripts/python.exe') -m uvicorn app.main:app --app-dir (Join-Path $demoRoot 'backend') --host 127.0.0.1 --port $Port --no-access-log
    $demoExit = $LASTEXITCODE
} finally { $env:APP_ROOT = $previousRoot }
exit $demoExit
