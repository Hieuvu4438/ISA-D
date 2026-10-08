param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$demoRoot = Split-Path $PSScriptRoot -Parent
$demoPython = Join-Path $demoRoot 'backend/.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $demoPython)) {
    throw 'Chạy scripts/setup_backend.ps1 trước để cài backend.'
}
& $demoPython -m uvicorn app.main:app --app-dir (Join-Path $demoRoot 'backend') --host 127.0.0.1 --port $Port --no-access-log
exit $LASTEXITCODE
