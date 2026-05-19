# Groq Multi-Agent Agency Platform

Autonomous software agency with CFO, Architect, Developer, QA (Docker sandbox), and DevOps agents powered by Groq.

## Quick start (Windows)

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (optional; QA runs in simulation mode without it).
2. Get a Groq API key from [console.groq.com](https://console.groq.com/).
3. Double-click `run-agency.bat` or run:

```bash
python -m venv venv-agency
venv-agency\Scripts\activate
pip install -r requirements-agency.txt
python -m uvicorn server:app --reload
```

4. Open **http://localhost:8000/** in your browser (recommended) or double-click `index.html`.
5. Paste your `gsk_...` key, choose project type, enter requirements, and click **Launch Agency Pipeline**.
6. Watch the Cursor terminal for live agent logs (`[CFO]`, `[ARCHITECT]`, `[DEVELOPER]`, `[DEVOPS]`, `[EXPORT]`).
7. Files auto-save to `generated-projects/<timestamp>-<name>/` when **Auto-save** is checked.

### Deploy a server project (Step 6 — automated)

After a server pipeline completes, open the saved folder and run:

```powershell
cd "f:\vs code\echo-sync-v2\generated-projects\<your-folder>"
docker compose up --build
```

The folder contains `app.py`, `Dockerfile`, `docker-compose.yml`, and `DEPLOY.md`.

## API

- `GET /` — Control dashboard (`index.html`)
- `POST /v1/agency/execute` — Full pipeline (header: `X-Groq-Key`)

## Project types

| Type     | Output |
|----------|--------|
| `script` | Verified Python code |
| `server` | App + Dockerfile + docker-compose + deploy steps |

## Files

| File | Role |
|------|------|
| `server.py` | FastAPI backend + all agents |
| `index.html` | Monaco editor control panel |
| `requirements-agency.txt` | Python dependencies |
| `run-agency.bat` | One-click Windows launcher |
