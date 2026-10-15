param([switch]$Calibrate)
$ErrorActionPreference = 'Stop'
$demoRoot = Split-Path $PSScriptRoot -Parent
$demoPython = Join-Path $demoRoot 'backend/.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $demoPython)) {
    & python -m venv (Join-Path $demoRoot 'backend/.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Không tạo được Python venv.' }
}
& $demoPython -m ensurepip --upgrade
if ($LASTEXITCODE -ne 0) { throw 'Không khởi tạo được pip trong virtualenv.' }
& $demoPython -m pip install --cache-dir (Join-Path $demoRoot 'runtime/pip-cache') -r (Join-Path $demoRoot 'backend/requirements.lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Không cài được dependencies.' }
& $demoPython -m pip install --cache-dir (Join-Path $demoRoot 'runtime/pip-cache') --no-deps -e (Join-Path $demoRoot 'backend')
if ($LASTEXITCODE -ne 0) { throw 'Không cài được application package.' }
$demoScripts = @('validate_dataset.py', 'download_models.py', 'build_index.py')
if ($Calibrate) { $demoScripts += 'calibrate_thresholds.py' }
foreach ($demoScript in $demoScripts) {
    & $demoPython (Join-Path $PSScriptRoot $demoScript)
    if ($LASTEXITCODE -ne 0) { throw "Setup thất bại tại $demoScript." }
}
if (-not $Calibrate) { Write-Host 'Demo dùng chế độ sản phẩm gần nhất. Thêm -Calibrate để chạy calibration riêng.' }
Write-Host 'Backend sẵn sàng. Chạy scripts/run_backend.ps1 rồi mở http://127.0.0.1:8000/docs'
