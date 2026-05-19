# Codex Agency

**Codex-style AI coding workspace** + **multi-agent software agency** — bring your own API key from any supported provider.

## Live UI

| URL | What |
|-----|------|
| `/` | **Codex workspace** — chat, memory, GitHub, Monaco editor |
| `/agency` | **Agency pipeline** — CFO → Architect → Developer → DevOps |

## Quick start (local)

```powershell
pip install -r requirements-agency.txt
python -m uvicorn server:app --reload
```

Open http://localhost:8000/

1. Choose provider (Groq, OpenAI, Anthropic, OpenRouter)
2. Paste your API key
3. Optional: GitHub personal access token for repo integration
4. **+ New session** → chat

See [CODEX.md](CODEX.md) for full API and features.

## Deploy on Render

| Setting | Value |
|---------|--------|
| **Build** | `python3 -m venv .venv && .venv/bin/pip install --upgrade pip && .venv/bin/pip install -r requirements-agency.txt` |
| **Start** | `bash start.sh` |

## Providers (BYOK)

No keys on the server — users supply:

- **AI:** `X-Api-Key` (Groq `gsk_`, OpenAI `sk-`, Anthropic, OpenRouter)
- **GitHub:** `X-Github-Token` (optional PAT)

## What's included vs full Codex

| Feature | Status |
|---------|--------|
| Chat agent + markdown | ✅ |
| Multi-provider API keys | ✅ |
| Session memory (SQLite) | ✅ |
| GitHub read / commit files | ✅ |
| Monaco editor | ✅ |
| Agency multi-agent pipeline | ✅ `/agency` |
| Streaming | 🔜 |
| Server-side file sandbox | 🔜 |
| GitHub OAuth | 🔜 |

MIT
