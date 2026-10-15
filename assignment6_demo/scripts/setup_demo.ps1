$ErrorActionPreference = 'Stop'
$demoRoot = Split-Path $PSScriptRoot -Parent
$demoPython = Join-Path $demoRoot 'backend/.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath (Join-Path $demoRoot '.env'))) {
    Copy-Item -LiteralPath (Join-Path $demoRoot '.env.example') -Destination (Join-Path $demoRoot '.env')
}
& (Join-Path $PSScriptRoot 'setup_backend.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Backend setup failed.' }
foreach ($demoScript in @('import_demo_database.py', 'prepare_demo.py')) {
    & $demoPython (Join-Path $PSScriptRoot $demoScript)
    if ($LASTEXITCODE -ne 0) { throw "Demo setup failed at $demoScript. Existing database was not reset." }
}
Push-Location -LiteralPath (Join-Path $demoRoot 'frontend')
try {
    & npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }
Write-Host 'Demo ready. Credentials: runtime/demo/access.json. Set GROQ_API_KEY in local .env for speech.'
Write-Host 'Run scripts/run_backend.ps1 and scripts/run_frontend.ps1 -Preview in separate terminals.'
