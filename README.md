# Vigilens

Kitchen and workspace monitoring demo: video understanding, health and efficiency agents (Fetch.ai uAgents), orchestration, and a React dashboard.  Built for UCSD DiamondHacks 2026

## Prerequisites

- **Python** 3.10 or newer  
- **Node.js** 18+ and **npm**  
- **Git**

For full features: [TwelveLabs](https://twelvelabs.io/) API key, Fetch.ai / Agentverse setup, Browser Use, Google OAuth, Stripe (see [Environment variables](#environment-variables)).

## Download

Clone the repository and enter the project root:

```bash
git clone <repository-url>
cd Vigilens
```

## Backend setup

Create a virtual environment **inside `backend/`** (this matches `start.sh`):

```bash
cd backend
python3 -m venv .venv
```

**macOS / Linux** — activate and install dependencies:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)** — activate and install:

```bash
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Return to the repository root for the run step:

```bash
cd ..
```

## Frontend setup

From the repository root:

```bash
cd frontend
npm install
cd ..
```

## Environment variables

Create a file at **`backend/.env`** (it is gitignored). The API loads this path first.

| Variable | Required for |
|----------|----------------|
| `TWELVELABS_API_KEY` | Video indexing / detection |
| `HEALTH_AGENT_SEED`, `EFFICIENCY_AGENT_SEED`, `BROWSER_AGENT_SEED`, `ORCHESTRATOR_SEED` | Stable agent identities |
| `BROWSER_USE_API_KEY`, `GOOGLE_PROFILE_ID` | Browser agent automation |
| `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY` | Paid report checkout |
| `ASI_ONE_API_KEY`, `GEMINI_API_KEY` | LLM features |


## Run the application

Run everything **from the repository root** so imports like `backend.main` resolve.

### macOS / Linux (recommended)

```bash
bash start.sh
```

This starts:

- FastAPI on **http://localhost:8000** (Swagger UI: **http://localhost:8000/docs**)  
- Health agent on **8001**, efficiency on **8002**, browser on **8003**, orchestrator on **8004**  
- Vite dev server on **http://localhost:5173**

Stop: press **Ctrl+C** in that terminal, or run `kill $(jobs -p)` if you backgrounded jobs manually.

### Windows

`start.ps1` in this repo expects a venv at the repo **root** (`.\venv`). To avoid mismatches, open **separate** terminals from the repo root and run:

```powershell
# Terminal 1 — API
backend\.venv\Scripts\python -m uvicorn backend.main:app --port 8000 --reload

# Terminal 2–5 — agents (one command per terminal)
backend\.venv\Scripts\python -m backend.agents.health.health_agent
backend\.venv\Scripts\python -m backend.agents.efficiency.efficiency_agent
backend\.venv\Scripts\python -m backend.agents.browser.browser_agent
backend\.venv\Scripts\python -m backend.agents.orchestrator.orchestrator_agent

# Terminal 6 — frontend
cd frontend
npm run dev
```

Or use **Git Bash** and run `bash start.sh` after creating `backend/.venv` as above.

### Optional: seed demo data

With the backend venv active and cwd at repo root:

```bash
backend/.venv/bin/python -m backend.seed
```

(On Windows: `backend\.venv\Scripts\python -m backend.seed`.)

## License

See [LICENSE](LICENSE).
