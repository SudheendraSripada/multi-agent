"""Codex-style workspace API: chat, memory, multi-provider LLM, GitHub."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

import github_ops
import memory_store
from llm_client import LLMClient, PROVIDER_CONFIG

router = APIRouter(prefix="/v1/codex", tags=["codex"])

CODEX_SYSTEM = """You are Codex Agency — an expert autonomous software engineer (like OpenAI Codex / GitHub Copilot Workspace).

Capabilities you should use in reasoning:
- Write, explain, and refactor code in any language
- Plan multi-step engineering work
- Remember project facts the user wants kept (emit MEMO lines, see below)
- Reference linked GitHub repos when context is provided

Rules:
- Be concise but thorough. Use markdown code fences for code.
- When the user states a durable preference or fact, add a line: MEMO: key=value
- For GitHub file changes, describe exact path and content; the UI can commit via API.
- If asked to run the full multi-agent pipeline (CFO/Architect/Dev/DevOps), tell them to use the Agency tab.

You do NOT have direct shell access on the server unless the user deploys generated artifacts themselves."""


class SessionCreate(BaseModel):
    title: str = "New project"
    provider: str = "groq"
    model: str | None = None


class ChatRequest(BaseModel):
    session_id: str
    message: str
    provider: str | None = None
    model: str | None = None


class MemorySet(BaseModel):
    key: str
    value: str


class GithubLink(BaseModel):
    owner: str
    repo: str
    branch: str = "main"


class GithubFileWrite(BaseModel):
    path: str
    content: str
    message: str
    branch: str = "main"


def _require_api_key(x_api_key: str | None) -> str:
    if not x_api_key:
        raise HTTPException(401, "X-Api-Key header required (your AI provider API key).")
    return x_api_key


def _client(
    provider: str,
    api_key: str,
    model: str | None,
) -> LLMClient:
    try:
        return LLMClient(provider, api_key, model)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


def _parse_memos(text: str, session_id: str) -> str:
    cleaned_lines = []
    for line in text.splitlines():
        if line.strip().upper().startswith("MEMO:"):
            payload = line.split(":", 1)[1].strip()
            if "=" in payload:
                key, value = payload.split("=", 1)
                memory_store.set_memory(session_id, key.strip(), value.strip())
        else:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def _build_context(session_id: str, github_token: str | None) -> str:
    parts = []
    memories = memory_store.get_memories(session_id)
    if memories:
        parts.append("## Session memory")
        for m in memories:
            parts.append(f"- {m['key']}: {m['value']}")

    link = memory_store.get_github_link(session_id)
    if link and github_token:
        parts.append(
            f"\n## Linked GitHub repo\n{link['owner']}/{link['repo']} (branch: {link['branch']})"
        )
        try:
            files = github_ops.list_tree(
                github_token, link["owner"], link["repo"], link["branch"], max_files=40
            )
            paths = [f["path"] for f in files[:40]]
            parts.append("Files (sample):\n" + "\n".join(f"- {p}" for p in paths))
        except Exception as exc:
            parts.append(f"(Could not load tree: {exc})")
    elif link:
        parts.append(
            f"\n## Linked GitHub repo\n{link['owner']}/{link['repo']} — provide GitHub token to load files."
        )

    return "\n".join(parts)


@router.get("/providers")
def list_providers():
    return {
        "providers": [
            {
                "id": pid,
                "default_model": cfg["default_model"],
                "fast_model": cfg.get("fast_model"),
            }
            for pid, cfg in PROVIDER_CONFIG.items()
        ]
    }


@router.post("/sessions")
def create_session(body: SessionCreate):
    model = body.model or PROVIDER_CONFIG[body.provider.lower()]["default_model"]
    return memory_store.create_session(body.title, body.provider.lower(), model)


@router.get("/sessions")
def sessions():
    return {"sessions": memory_store.list_sessions()}


@router.get("/sessions/{session_id}")
def session_detail(session_id: str):
    try:
        return memory_store.get_session(session_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/sessions/{session_id}/messages")
def session_messages(session_id: str):
    return {"messages": memory_store.get_messages(session_id)}


@router.get("/sessions/{session_id}/memory")
def session_memory(session_id: str):
    return {"memories": memory_store.get_memories(session_id)}


@router.post("/sessions/{session_id}/memory")
def session_memory_set(session_id: str, body: MemorySet):
    return memory_store.set_memory(session_id, body.key, body.value)


@router.post("/sessions/{session_id}/github")
def session_github_link(
    session_id: str,
    body: GithubLink,
):
    return memory_store.link_github(session_id, body.owner, body.repo, body.branch)


@router.post("/chat")
def codex_chat(
    body: ChatRequest,
    x_api_key: str = Header(None, alias="X-Api-Key"),
    x_github_token: str = Header(None, alias="X-Github-Token"),
):
    api_key = _require_api_key(x_api_key)
    try:
        sess = memory_store.get_session(body.session_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc

    provider = (body.provider or sess["provider"]).lower()
    model = body.model or sess["model"]
    client = _client(provider, api_key, model)

    memory_store.add_message(body.session_id, "user", body.message)
    context = _build_context(body.session_id, x_github_token)
    history = memory_store.get_messages(body.session_id)

    messages = [{"role": "system", "content": CODEX_SYSTEM}]
    if context:
        messages.append({"role": "system", "content": context})
    for msg in history[-20:]:
        if msg["role"] in ("user", "assistant"):
            messages.append({"role": msg["role"], "content": msg["content"]})

    try:
        reply = client.chat(messages, model=model, temperature=0.3)
    except Exception as exc:
        raise HTTPException(502, f"LLM error: {exc}") from exc

    reply = _parse_memos(reply, body.session_id)
    memory_store.add_message(body.session_id, "assistant", reply)

    return {
        "reply": reply,
        "session_id": body.session_id,
        "provider": provider,
        "model": model,
        "memories": memory_store.get_memories(body.session_id),
    }


@router.post("/github/repos")
def github_list_repos(x_github_token: str = Header(None, alias="X-Github-Token")):
    if not x_github_token:
        raise HTTPException(401, "X-Github-Token required.")
    try:
        return {"repos": github_ops.list_repos(x_github_token)}
    except Exception as exc:
        raise HTTPException(502, f"GitHub error: {exc}") from exc


@router.get("/github/{owner}/{repo}/tree")
def github_tree(
    owner: str,
    repo: str,
    branch: str = "main",
    x_github_token: str = Header(None, alias="X-Github-Token"),
):
    if not x_github_token:
        raise HTTPException(401, "X-Github-Token required.")
    try:
        return {"files": github_ops.list_tree(x_github_token, owner, repo, branch)}
    except Exception as exc:
        raise HTTPException(502, f"GitHub error: {exc}") from exc


@router.get("/github/{owner}/{repo}/file")
def github_read_file(
    owner: str,
    repo: str,
    path: str,
    branch: str = "main",
    x_github_token: str = Header(None, alias="X-Github-Token"),
):
    if not x_github_token:
        raise HTTPException(401, "X-Github-Token required.")
    try:
        return github_ops.get_file(x_github_token, owner, repo, path, branch)
    except Exception as exc:
        raise HTTPException(502, f"GitHub error: {exc}") from exc


@router.post("/github/{owner}/{repo}/file")
def github_write_file(
    owner: str,
    repo: str,
    body: GithubFileWrite,
    x_github_token: str = Header(None, alias="X-Github-Token"),
):
    if not x_github_token:
        raise HTTPException(401, "X-Github-Token required.")
    try:
        result = github_ops.upsert_file(
            x_github_token,
            owner,
            repo,
            body.path,
            body.content,
            body.message,
            body.branch,
        )
        return {"status": "committed", "result": result.get("commit", {})}
    except Exception as exc:
        raise HTTPException(502, f"GitHub error: {exc}") from exc
