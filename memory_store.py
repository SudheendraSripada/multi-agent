"""Persistent session memory for Codex-style workspace."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(WORKSPACE_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "codex.db")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                meta_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(session_id, key),
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            CREATE TABLE IF NOT EXISTS github_links (
                session_id TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                repo TEXT NOT NULL,
                branch TEXT NOT NULL DEFAULT 'main',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            """
        )


def create_session(title: str, provider: str, model: str) -> dict:
    sid = str(uuid.uuid4())
    now = _utc_now()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO sessions (id, title, provider, model, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (sid, title, provider, model, now, now),
        )
    return get_session(sid)


def list_sessions(limit: int = 50) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_session(session_id: str) -> dict:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        raise KeyError(f"Session {session_id} not found")
    return dict(row)


def touch_session(session_id: str) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (_utc_now(), session_id),
        )


def add_message(session_id: str, role: str, content: str, meta: dict | None = None) -> dict:
    mid = str(uuid.uuid4())
    now = _utc_now()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO messages (id, session_id, role, content, meta_json, created_at) VALUES (?,?,?,?,?,?)",
            (mid, session_id, role, content, json.dumps(meta or {}), now),
        )
    touch_session(session_id)
    return {"id": mid, "session_id": session_id, "role": role, "content": content, "created_at": now}


def get_messages(session_id: str, limit: int = 100) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["meta"] = json.loads(d.pop("meta_json") or "{}")
        out.append(d)
    return out


def set_memory(session_id: str, key: str, value: str) -> dict:
    mid = str(uuid.uuid4())
    now = _utc_now()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO memories (id, session_id, key, value, updated_at)
            VALUES (?,?,?,?,?)
            ON CONFLICT(session_id, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """,
            (mid, session_id, key, value, now),
        )
    return {"session_id": session_id, "key": key, "value": value, "updated_at": now}


def get_memories(session_id: str) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT key, value, updated_at FROM memories WHERE session_id = ? ORDER BY updated_at DESC",
            (session_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def link_github(session_id: str, owner: str, repo: str, branch: str = "main") -> dict:
    now = _utc_now()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO github_links (session_id, owner, repo, branch, updated_at)
            VALUES (?,?,?,?,?)
            ON CONFLICT(session_id) DO UPDATE SET owner=excluded.owner, repo=excluded.repo,
                branch=excluded.branch, updated_at=excluded.updated_at
            """,
            (session_id, owner, repo, branch, now),
        )
    return {"session_id": session_id, "owner": owner, "repo": repo, "branch": branch}


def get_github_link(session_id: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM github_links WHERE session_id = ?", (session_id,)
        ).fetchone()
    return dict(row) if row else None
