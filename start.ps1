Write-Host "Starting LLM Council..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "uv run python -m backend.main"
Start-Sleep -Seconds 2
Set-Location frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev"
Set-Location ..
Write-Host "Done."
