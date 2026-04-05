# Start all agents, backend API, and frontend dev server
# Usage: .\start.ps1

Write-Host "Stopping old processes..." -ForegroundColor Yellow
Get-Process -Name "python" -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name "node" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

Write-Host "Starting SafeWatch..." -ForegroundColor Cyan

# Backend API
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\venv\Scripts\python -m uvicorn backend.main:app --port 8000 --reload"
Write-Host "  Backend API starting on http://localhost:8000" -ForegroundColor Green

Start-Sleep -Seconds 2

# Health Agent
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\venv\Scripts\python -m backend.agents.health.health_agent"
Write-Host "  Health Agent starting on port 8001" -ForegroundColor Green

# Efficiency Agent
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\venv\Scripts\python -m backend.agents.efficiency.efficiency_agent"
Write-Host "  Efficiency Agent starting on port 8002" -ForegroundColor Green

# Browser Agent
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\venv\Scripts\python -m backend.agents.browser.browser_agent"
Write-Host "  Browser Agent starting on port 8003" -ForegroundColor Green

# Orchestrator Agent
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\venv\Scripts\python -m backend.agents.orchestrator.orchestrator_agent"
Write-Host "  Orchestrator starting on port 8004" -ForegroundColor Green

Start-Sleep -Seconds 1

# Frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; npm run dev"
Write-Host "  Frontend starting on http://localhost:5173" -ForegroundColor Green

Write-Host ""
Write-Host "All services launched. Each runs in its own PowerShell window." -ForegroundColor Cyan
Write-Host "Dashboard: http://localhost:5173" -ForegroundColor Yellow
Write-Host "API:       http://localhost:8000/docs" -ForegroundColor Yellow
