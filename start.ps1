# LLM Council - PowerShell Start Script
Write-Host "Starting LLM Council..." -ForegroundColor Cyan

# Start backend in a new window
Write-Host "Starting backend on http://localhost:8001..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "py -m uv run python -m backend.main"

# Wait a bit for backend to start
Start-Sleep -Seconds 2

# Start frontend in a new window
Write-Host "Starting frontend on http://localhost:5173..." -ForegroundColor Green
Set-Location frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev"
Set-Location ..

Write-Host "✓ LLM Council is starting!" -ForegroundColor Yellow
Write-Host "  Backend:  http://localhost:8001"
Write-Host "  Frontend: http://localhost:5173"
Write-Host ""
Write-Host "Separate terminal windows have been opened for the Backend and Frontend."
