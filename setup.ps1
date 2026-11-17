# One-click setup for PathFinder AI.
# Easiest: double-click setup.bat    (or: powershell -ExecutionPolicy Bypass -File .\setup.ps1)
Set-Location $PSScriptRoot
$ErrorActionPreference = "Continue"
function Fail($m) { Write-Host "`n$m" -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }
function Step($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }

Step "1/6  Checking Python 3.12"
py -3.12 --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python 3.12 not found. Installing it (one time). Your Python 3.14 stays your default."
    py install 3.12
    py -3.12 --version *> $null
    if ($LASTEXITCODE -ne 0) { Fail "Could not install Python 3.12. Install it from python.org, then run this again." }
}
py -3.12 --version

Step "2/6  Creating virtual environment"
if (-not (Test-Path ".\venv\Scripts\python.exe")) {
    py -3.12 -m venv venv
    if ($LASTEXITCODE -ne 0) { Fail "Could not create the virtual environment." }
} else { Write-Host "venv already exists, reusing it." }
$py = Join-Path $PSScriptRoot "venv\Scripts\python.exe"

Step "3/6  Installing libraries (TensorFlow is big, this can take a few minutes)"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Fail "Library install failed. Scroll up to read the error and send me a screenshot." }

Step "4/6  Setting up your .env file"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    $secret = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
    $key = Read-Host "Paste your FREE Groq API key (console.groq.com) or just press Enter to skip"
    $text = Get-Content ".env" -Raw
    $text = $text -replace "SECRET_KEY=[^\r\n]*", "SECRET_KEY=$secret"
    if ($key.Trim()) { $text = $text -replace "GROQ_API_KEY=[^\r\n]*", "GROQ_API_KEY=$($key.Trim())" }
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot ".env"), $text, (New-Object Text.UTF8Encoding $false))
    Write-Host ".env created."
} else { Write-Host ".env already exists, keeping it." }

Step "5/6  Training the TensorFlow model (first time only)"
if (-not (Test-Path "model\career_model.keras")) {
    & $py model\train.py
    if ($LASTEXITCODE -ne 0) { Fail "Training failed. Send me a screenshot of the error." }
} else { Write-Host "Model already trained, skipping." }

Step "6/6  Starting the website"
Write-Host "Opening http://localhost:5000 ... press Ctrl+C here to stop the server." -ForegroundColor Green
Start-Job { Start-Sleep 6; Start-Process "http://localhost:5000" } | Out-Null
& $py app.py
