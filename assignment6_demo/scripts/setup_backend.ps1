$ErrorActionPreference = 'Stop'
$demoRoot = Split-Path $PSScriptRoot -Parent
$demoPython = Join-Path $demoRoot 'backend/.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $demoPython)) {
    & python -m venv (Join-Path $demoRoot 'backend/.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Không tạo được Python venv.' }
}
& $demoPython -m pip install -r (Join-Path $demoRoot 'backend/requirements.lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Không cài được dependencies.' }
foreach ($demoScript in @('validate_dataset.py', 'download_models.py', 'build_index.py', 'calibrate_thresholds.py')) {
    & $demoPython (Join-Path $PSScriptRoot $demoScript)
    if ($LASTEXITCODE -ne 0) { throw "Setup thất bại tại $demoScript." }
}
Write-Host 'Backend sẵn sàng. Chạy scripts/run_backend.ps1 rồi mở http://127.0.0.1:8000/docs'
