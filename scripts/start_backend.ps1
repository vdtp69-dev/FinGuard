param(
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root "venv\Scripts\python.exe"

if (!(Test-Path $py)) {
  throw "Python not found at $py"
}

$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique

if ($listeners) {
 Write-Host ("Stopping existing listeners on port {0}: {1}" -f $Port, ($listeners -join ", "))
  foreach ($procId in $listeners) {
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
  }
}

Write-Host "Starting FinGuard API on 127.0.0.1:$Port"
& $py -m uvicorn api:app --host 127.0.0.1 --port $Port

