# Autonomous Multi-Agent AI Software Agency

Groq-powered enterprise pipeline: **CFO** → **Architect** → **Developer** (Docker QA loop) → **DevOps**, with a Monaco control-panel frontend and automatic export to disk.

## Quick start

```powershell
pip install -r requirements-agency.txt
python -m uvicorn server:app --reload
```

Open **http://localhost:8000/** — paste your [Groq API key](https://console.groq.com/), enter requirements, and click **Launch Agency Pipeline**.

Or on Windows, double-click `run-agency.bat`.

## What it does

| Agent | Role |
|-------|------|
| CFO | Budget / token gate |
| Architect | SOP, dependencies, verification tests |
| Developer | Code + up to 3 QA self-heal loops |
| DevOps | Dockerfile, compose, deploy commands (server projects) |

Deliverables auto-save to `generated-projects/<timestamp>-<name>/` (`app.py`, `Dockerfile`, `docker-compose.yml`, `DEPLOY.md`).

## Deploy generated server

```powershell
cd generated-projects\<your-folder>
docker compose up --build
```

## API

- `GET /` — Dashboard
- `POST /v1/agency/execute` — Full pipeline (header: `X-Groq-Key`)
- `POST /v1/agency/export` — Re-export last result to disk

## Requirements

- Python 3.11+
- [Groq API key](https://console.groq.com/)
- Docker Desktop (optional; QA runs in simulation mode without it)

## Deploy on Render

| Setting | Value |
|---------|--------|
| **Build Command** | `python3 -m venv .venv && .venv/bin/pip install --upgrade pip && .venv/bin/pip install -r requirements-agency.txt` |
| **Start Command** | `bash start.sh` |

Build installs into `.venv/`; start uses `.venv/bin/python` (system `python3` does not see those packages). A `render.yaml` in this repo sets these automatically on blueprint deploys.

## License

MIT
