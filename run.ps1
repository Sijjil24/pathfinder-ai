# Start the website again later:  double-click run.bat
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "Run setup.bat first." -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }
Write-Host "Opening http://localhost:5000 ... press Ctrl+C to stop." -ForegroundColor Green
Start-Job { Start-Sleep 4; Start-Process "http://localhost:5000" } | Out-Null
& $py app.py
