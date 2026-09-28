param(
    [ValidateSet("setup", "check", "test", "migrate", "run", "generate-data", "seed", "train", "help")]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$venvPython = Join-Path $root ".venv\Scripts\python.exe"

if ($Command -eq "help") {
    Write-Output "Usage: .\scripts\dev.ps1 <setup|check|test|migrate|run|generate-data|seed|train>"
    exit 0
}

if ($Command -eq "setup") {
    if (-not (Test-Path $venvPython)) {
        & python -m venv .venv
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    & $venvPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
    }
    Write-Output "Environment ready. Activate with .\.venv\Scripts\Activate.ps1"
    exit 0
}

if (-not (Test-Path $venvPython)) {
    Write-Error "Virtual environment not found. Run .\scripts\dev.ps1 setup first."
    exit 1
}

switch ($Command) {
    "check" { & $venvPython manage.py check }
    "test" { & $venvPython manage.py test }
    "migrate" { & $venvPython manage.py migrate }
    "run" { & $venvPython manage.py runserver }
    "generate-data" { & $venvPython ml/data/generate_sample_data.py }
    "seed" {
        & $venvPython ml/data/generate_sample_data.py
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        & $venvPython manage.py seed_data
    }
    "train" { & $venvPython manage.py train_models }
}

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
