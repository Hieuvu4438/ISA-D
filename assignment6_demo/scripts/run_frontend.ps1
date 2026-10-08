param([switch]$Preview)
$ErrorActionPreference = 'Stop'
$demoRoot = Split-Path $PSScriptRoot -Parent
$frontendRoot = Join-Path $demoRoot 'frontend'
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw 'Node.js 22.12+ and npm are required.'
}
if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot 'node_modules'))) {
    throw 'Run npm ci in assignment6_demo/frontend first.'
}
Push-Location -LiteralPath $frontendRoot
try {
    if ($Preview) { & npm.cmd run preview } else { & npm.cmd run dev }
    $frontendExit = $LASTEXITCODE
} finally { Pop-Location }
exit $frontendExit
