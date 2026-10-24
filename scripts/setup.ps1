$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    & py -3 scripts/check_package.py
    if ($LASTEXITCODE -ne 0) { throw 'Package integrity check failed. Review differences before continuing.' }
    if (-not (Test-Path '.venv/Scripts/python.exe')) {
        & py -3 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create Python environment.' }
    }
    & ./.venv/Scripts/python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    Write-Host 'Setup complete. Next: .\.venv\Scripts\python.exe scripts\run_baseline.py'
} finally { Pop-Location }
