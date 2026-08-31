$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Virtual environment belum tersedia. Ikuti langkah setup pada README.md."
}

& $PythonPath -m uvicorn social_connectors_api.main:app --host 0.0.0.0 --port 8000
