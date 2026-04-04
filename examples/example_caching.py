#!/usr/bin/env python3
"""Run a two-turn prompt-caching probe and print usage JSON."""

from __future__ import annotations

import asyncio
import json
import os

from tinyagent import Agent, AgentOptions
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions

SYSTEM_PROMPT = (
    "You are a concise assistant. Keep answers to one sentence. "
    "Use the prior conversation context. "
    "This prompt is intentionally repeated and slightly long "
    "to keep the prefix stable across turns. "
    "Return plain text only."
)

PROMPTS = [
    "Reply with exactly: turn one acknowledged.",
    "Reply with exactly: turn two acknowledged.",
]

_DEFAULT_PROVIDER = "minimax"
_DEFAULT_SESSION_ID = "prompt-caching-probe"
_DEFAULT_MAX_TOKENS = 128

_DEFAULT_MODEL_BY_PROVIDER = {
    "chutes": "Qwen/Qwen3-32B",
    "minimax": "MiniMax-M2.5",
    "minimax-cn": "MiniMax-M2.5",
    "openai": "gpt-4.1-mini",
    "openrouter": "openai/gpt-4.1-mini",
}

_DEFAULT_BASE_URL_BY_PROVIDER = {
    "chutes": "https://llm.chutes.ai/v1/chat/completions",
    "minimax": "https://api.minimax.io/v1/chat/completions",
    "minimax-cn": "https://api.minimax.chat/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
}

_DEFAULT_API_BY_PROVIDER = {
    "minimax": "minimax-completions",
    "minimax-cn": "minimax-completions",
}

_PROVIDER_API_KEY_ENV = {
    "chutes": "CHUTES_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "minimax-cn": "MINIMAX_CN_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def _provider_name() -> str:
    provider = os.getenv("CACHE_PROBE_PROVIDER", _DEFAULT_PROVIDER).strip().lower()
    return provider or _DEFAULT_PROVIDER


def _model_name(provider: str) -> str:
    explicit = os.getenv("CACHE_PROBE_MODEL", "").strip()
    if explicit:
        return explicit
    return _DEFAULT_MODEL_BY_PROVIDER.get(provider, _DEFAULT_MODEL_BY_PROVIDER[_DEFAULT_PROVIDER])


def _base_url(provider: str) -> str:
    explicit = os.getenv("CACHE_PROBE_BASE_URL", "").strip()
    if explicit:
        return explicit
    return _DEFAULT_BASE_URL_BY_PROVIDER.get(
        provider, _DEFAULT_BASE_URL_BY_PROVIDER[_DEFAULT_PROVIDER]
    )


def _api(provider: str) -> str:
    explicit = os.getenv("CACHE_PROBE_API", "").strip()
    if explicit:
        return explicit
    return _DEFAULT_API_BY_PROVIDER.get(provider, "")


def _session_id() -> str:
    explicit = os.getenv("CACHE_PROBE_SESSION_ID", "").strip()
    if explicit:
        return explicit
    return _DEFAULT_SESSION_ID


def _max_tokens() -> int:
    raw = os.getenv("CACHE_PROBE_MAX_TOKENS", str(_DEFAULT_MAX_TOKENS)).strip()
    return int(raw)


def _resolve_api_key(provider: str) -> str | None:
    explicit = os.getenv("CACHE_PROBE_API_KEY", "").strip()
    if explicit:
        return explicit

    env_var = _PROVIDER_API_KEY_ENV.get(provider)
    if not env_var:
        return None
    return os.getenv(env_var)


def _extract_text(message_content: list[object]) -> str:
    lines: list[str] = []
    for block in message_content:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text:
            lines.append(text)
    return "\n".join(lines)


async def main() -> None:
    provider = _provider_name()
    model_name = _model_name(provider)
    base_url = _base_url(provider)
    api = _api(provider)

    agent = Agent(
        AgentOptions(
            stream_fn=stream_alchemy_openai_completions,
            get_api_key=_resolve_api_key,
            enable_prompt_caching=True,
            session_id=_session_id(),
        )
    )
    agent.set_model(
        OpenAICompatModel(
            provider=provider,
            api=api,
            id=model_name,
            base_url=base_url,
            max_tokens=_max_tokens(),
        )
    )
    agent.set_system_prompt(SYSTEM_PROMPT)

    records: list[dict[str, object]] = []
    for turn, prompt in enumerate(PROMPTS, start=1):
        message = await agent.prompt(prompt)
        records.append(
            {
                "turn": turn,
                "prompt": prompt,
                "text": _extract_text(message.content),
                "usage": message.usage,
                "provider": message.provider,
                "model": message.model,
                "api": message.api,
                "stop_reason": message.stop_reason,
            }
        )

    print(
        json.dumps(
            {
                "provider": provider,
                "model": model_name,
                "api": api or None,
                "base_url": base_url,
                "enable_prompt_caching": True,
                "session_id": agent.session_id,
                "records": records,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
