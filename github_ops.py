"""GitHub REST helpers (user-supplied personal access token)."""

from __future__ import annotations

import base64
from typing import Any

import httpx

API = "https://api.github.com"


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def list_repos(token: str, per_page: int = 30) -> list[dict]:
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{API}/user/repos",
            headers=_headers(token),
            params={"sort": "updated", "per_page": per_page},
        )
        resp.raise_for_status()
        data = resp.json()
    return [
        {
            "full_name": r["full_name"],
            "owner": r["owner"]["login"],
            "name": r["name"],
            "default_branch": r.get("default_branch", "main"),
            "private": r.get("private", False),
        }
        for r in data
    ]


def get_file(token: str, owner: str, repo: str, path: str, ref: str = "main") -> dict:
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{API}/repos/{owner}/{repo}/contents/{path}",
            headers=_headers(token),
            params={"ref": ref},
        )
        resp.raise_for_status()
        data = resp.json()
    content = ""
    if data.get("encoding") == "base64" and data.get("content"):
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    return {"path": path, "sha": data.get("sha"), "content": content, "size": data.get("size")}


def list_tree(token: str, owner: str, repo: str, ref: str = "main", max_files: int = 200) -> list[dict]:
    """Flat file list via git trees API."""
    with httpx.Client(timeout=30.0) as client:
        ref_resp = client.get(
            f"{API}/repos/{owner}/{repo}/git/ref/heads/{ref}",
            headers=_headers(token),
        )
        if ref_resp.status_code == 404:
            ref_resp = client.get(
                f"{API}/repos/{owner}/{repo}",
                headers=_headers(token),
            )
            ref_resp.raise_for_status()
            ref = ref_resp.json().get("default_branch", "main")
            ref_resp = client.get(
                f"{API}/repos/{owner}/{repo}/git/ref/heads/{ref}",
                headers=_headers(token),
            )
        ref_resp.raise_for_status()
        sha = ref_resp.json()["object"]["sha"]

        tree_resp = client.get(
            f"{API}/repos/{owner}/{repo}/git/trees/{sha}",
            headers=_headers(token),
            params={"recursive": "1"},
        )
        tree_resp.raise_for_status()
        tree = tree_resp.json().get("tree", [])

    files = [
        {"path": t["path"], "type": t["type"], "size": t.get("size")}
        for t in tree
        if t.get("type") == "blob"
    ][:max_files]
    return files


def upsert_file(
    token: str,
    owner: str,
    repo: str,
    path: str,
    content: str,
    message: str,
    branch: str = "main",
) -> dict[str, Any]:
    headers = _headers(token)
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    body: dict[str, Any] = {
        "message": message,
        "content": encoded,
        "branch": branch,
    }

    with httpx.Client(timeout=30.0) as client:
        existing = client.get(
            f"{API}/repos/{owner}/{repo}/contents/{path}",
            headers=headers,
            params={"ref": branch},
        )
        if existing.status_code == 200:
            body["sha"] = existing.json()["sha"]

        resp = client.put(
            f"{API}/repos/{owner}/{repo}/contents/{path}",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()
        return resp.json()
