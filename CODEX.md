# Codex Agency Workspace

A **Codex-style** coding agent UI: chat, Monaco editor, persistent memory, GitHub integration, and any LLM provider via API key.

## Open

- **Codex workspace:** `/` (main UI)
- **Classic agency pipeline:** `/agency` (CFO → Architect → Dev → DevOps)

## Your keys (never stored on server)

| Header / field | Purpose |
|----------------|---------|
| **AI API key** | `X-Api-Key` — Groq, OpenAI, Anthropic, OpenRouter |
| **GitHub PAT** | `X-Github-Token` — repo read/write (optional) |

Keys stay in your browser `localStorage` only.

## Providers

| Provider | Example key | Default model |
|----------|-------------|---------------|
| `groq` | `gsk_...` | llama-3.3-70b-versatile |
| `openai` | `sk-...` | gpt-4o-mini |
| `anthropic` | `sk-ant-...` | claude-3-5-haiku-20241022 |
| `openrouter` | `sk-or-...` | meta-llama/llama-3.3-70b-instruct:free |

## Features

- **Sessions** — chat threads stored in SQLite (`data/codex.db`)
- **Memory** — durable facts per session (`MEMO: key=value` in agent replies or manual add)
- **GitHub** — link repo, browse files, open in editor, commit back
- **Editor** — Monaco; code blocks from chat auto-load

## API (`/v1/codex/...`)

- `GET /providers` — list providers
- `POST /sessions` · `GET /sessions`
- `POST /chat` — main agent (headers: `X-Api-Key`, optional `X-Github-Token`)
- `GET|POST /sessions/{id}/memory`
- `POST /sessions/{id}/github`
- `POST /github/repos` · `GET /github/{owner}/{repo}/tree` · file read/write

## Roadmap (not yet in v1)

Streaming responses, tool-use file writes on server, GitHub OAuth, embeddings, multi-agent swarms, terminal sandbox.
