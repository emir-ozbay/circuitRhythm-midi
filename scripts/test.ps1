$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    if (-not (Test-Path '.venv/Scripts/python.exe')) { throw 'Run setup.ps1 or create .venv first.' }
    & ./.venv/Scripts/python.exe scripts/run_baseline.py
    if ($LASTEXITCODE -ne 0) { throw 'Baseline failed. Inspect logs.' }
} finally { Pop-Location }
