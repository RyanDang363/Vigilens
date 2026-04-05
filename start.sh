#!/bin/bash
# Start all agents, backend API, and frontend dev server
# Usage: bash start.sh

echo "Starting SafeWatch..."

# Backend API
./venv/Scripts/python -m uvicorn backend.main:app --port 8000 --reload &
echo "  Backend API starting on http://localhost:8000"

sleep 2

# Health Agent
./venv/Scripts/python -m backend.agents.health.health_agent &
echo "  Health Agent starting on port 8001"

# Efficiency Agent
./venv/Scripts/python -m backend.agents.efficiency.efficiency_agent &
echo "  Efficiency Agent starting on port 8002"

# Browser Agent
./venv/Scripts/python -m backend.agents.browser.browser_agent &
echo "  Browser Agent starting on port 8003"

# Orchestrator Agent
./venv/Scripts/python -m backend.agents.orchestrator.orchestrator_agent &
echo "  Orchestrator starting on port 8004"

sleep 1

# Frontend
cd frontend && npm run dev &
cd ..
echo "  Frontend starting on http://localhost:5173"

echo ""
echo "All services launched in background."
echo "Dashboard: http://localhost:5173"
echo "API:       http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all, or run: kill \$(jobs -p)"

wait
