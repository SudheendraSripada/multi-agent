"""Unified LLM client — any provider with a user-supplied API key."""

from __future__ import annotations

import json
from typing import Any

import httpx

PROVIDER_CONFIG: dict[str, dict[str, Any]] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "fast_model": "llama-3.1-8b-instant",
        "style": "openai",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "fast_model": "gpt-4o-mini",
        "style": "openai",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "meta-llama/llama-3.3-70b-instruct:free",
        "fast_model": "meta-llama/llama-3.1-8b-instruct:free",
        "style": "openai",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-haiku-20241022",
        "fast_model": "claude-3-5-haiku-20241022",
        "style": "anthropic",
    },
}


class LLMClient:
    def __init__(self, provider: str, api_key: str, model: str | None = None):
        provider = provider.lower().strip()
        if provider not in PROVIDER_CONFIG:
            raise ValueError(f"Unknown provider '{provider}'. Choose: {', '.join(PROVIDER_CONFIG)}")
        self.provider = provider
        self.api_key = api_key
        self.config = PROVIDER_CONFIG[provider]
        self.model = model or self.config["default_model"]

    def list_models(self) -> list[str]:
        return [self.config["default_model"], self.config.get("fast_model", self.config["default_model"])]

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> str:
        model = model or self.model
        if self.config["style"] == "anthropic":
            return self._chat_anthropic(messages, model, temperature)
        return self._chat_openai_compat(messages, model, temperature, json_mode)

    def _chat_openai_compat(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        json_mode: bool,
    ) -> str:
        url = f"{self.config['base_url']}/chat/completions"
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/SudheendraSripada/multi-agent"
            headers["X-Title"] = "Codex Agency"

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, headers=headers, json=body)
            if resp.status_code >= 400:
                raise RuntimeError(f"{self.provider} API error {resp.status_code}: {resp.text[:500]}")
            data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _chat_anthropic(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
    ) -> str:
        system_parts: list[str] = []
        api_messages: list[dict[str, str]] = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                api_messages.append({"role": msg["role"], "content": msg["content"]})

        body: dict[str, Any] = {
            "model": model,
            "max_tokens": 8192,
            "temperature": temperature,
            "messages": api_messages,
        }
        if system_parts:
            body["system"] = "\n\n".join(system_parts)

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{self.config['base_url']}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"anthropic API error {resp.status_code}: {resp.text[:500]}")
            data = resp.json()

        parts = data.get("content", [])
        return "".join(p.get("text", "") for p in parts if p.get("type") == "text")
