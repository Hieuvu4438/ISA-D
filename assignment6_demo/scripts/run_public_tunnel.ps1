$ErrorActionPreference = 'Stop'
$demoRoot = Split-Path $PSScriptRoot -Parent
$demoTunnel = Join-Path $demoRoot 'runtime/tools/cloudflared.exe'
if (-not (Test-Path -LiteralPath $demoTunnel)) {
    throw 'Download cloudflared-windows-amd64.exe from the official cloudflare/cloudflared GitHub releases to runtime/tools/cloudflared.exe first.'
}
& $demoTunnel tunnel --url http://127.0.0.1:8003 --no-autoupdate --protocol http2 --logfile (Join-Path $demoRoot 'runtime/public-demo/tunnel.log')
exit $LASTEXITCODE
