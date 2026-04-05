# Start all agents, backend API, and frontend dev server
# Usage: .\start.ps1

Write-Host "Starting SafeWatch..." -ForegroundColor Cyan

# Backend API
Start-Process -FilePath ".\venv\Scripts\python" -ArgumentList "-m", "uvicorn", "backend.main:app", "--port", "8000", "--reload" -WindowStyle Normal
Write-Host "  Backend API starting on http://localhost:8000" -ForegroundColor Green

Start-Sleep -Seconds 2

# Health Agent
Start-Process -FilePath ".\venv\Scripts\python" -ArgumentList "-m", "backend.agents.health.health_agent" -WindowStyle Normal
Write-Host "  Health Agent starting on port 8001" -ForegroundColor Green

# Efficiency Agent
Start-Process -FilePath ".\venv\Scripts\python" -ArgumentList "-m", "backend.agents.efficiency.efficiency_agent" -WindowStyle Normal
Write-Host "  Efficiency Agent starting on port 8002" -ForegroundColor Green

# Browser Agent
Start-Process -FilePath ".\venv\Scripts\python" -ArgumentList "-m", "backend.agents.browser.browser_agent" -WindowStyle Normal
Write-Host "  Browser Agent starting on port 8003" -ForegroundColor Green

# Orchestrator Agent
Start-Process -FilePath ".\venv\Scripts\python" -ArgumentList "-m", "backend.agents.orchestrator.orchestrator_agent" -WindowStyle Normal
Write-Host "  Orchestrator starting on port 8004" -ForegroundColor Green

Start-Sleep -Seconds 1

# Frontend
Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory ".\frontend" -WindowStyle Normal
Write-Host "  Frontend starting on http://localhost:5173" -ForegroundColor Green

Write-Host ""
Write-Host "All services launched. Each runs in its own window." -ForegroundColor Cyan
Write-Host "Dashboard: http://localhost:5173" -ForegroundColor Yellow
Write-Host "API:       http://localhost:8000/docs" -ForegroundColor Yellow
