"""Compatibility provider for the optional tinyagent._alchemy binding.

This module keeps the Python-side adapter for the in-repo `tinyagent._alchemy`
extension built from `rust/`.

Important limitations:
- The binding currently dispatches only `openai-completions` and
  `minimax-completions` APIs.
- Image blocks are not supported yet.
- Python receives events by calling a blocking `next_event()` method in a thread,
  so it is real-time but has more overhead than a native async generator.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from typing import Protocol, cast

from .agent_types import (
    AgentTool,
    Context,
    Model,
    SimpleStreamOptions,
    dump_model_dumpable,
)
from .provider_contracts import (
    BindingStreamHandle,
    BindingStreamResponseBase,
    ProviderMetadataModel,
    resolve_model_metadata,
)


class _AlchemyModule(Protocol):
    def openai_completions_stream(
        self,
        model: dict[str, object],
        context: dict[str, object],
        options: dict[str, object],
    ) -> BindingStreamHandle: ...


_ALCHEMY_MODULE: _AlchemyModule | None = None

DEFAULT_OPENAI_COMPAT_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"

_PROVIDER_API_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "minimax-cn": "MINIMAX_CN_API_KEY",
}


def _get_alchemy_module() -> _AlchemyModule:
    global _ALCHEMY_MODULE
    if _ALCHEMY_MODULE is None:
        package = __package__ or "tinyagent"
        import_errors: list[tuple[str, Exception]] = []
        for module_name in ("_alchemy", f"{package}._alchemy"):
            try:
                module = importlib.import_module(module_name)
                _ALCHEMY_MODULE = cast(_AlchemyModule, module)
                break
            except Exception as exc:  # pragma: no cover
                import_errors.append((module_name, exc))
        if _ALCHEMY_MODULE is None:
            import_failures = "; ".join(
                f"{module_name}: {type(exc).__name__}: {exc}" for module_name, exc in import_errors
            )
            cause = next(
                (exc for _, exc in import_errors if not isinstance(exc, ModuleNotFoundError)),
                import_errors[-1][1],
            )
            raise RuntimeError(
                "Failed to import the optional alchemy binding. "
                "Install a wheel that includes tinyagent._alchemy or build the "
                "binding from the in-repo rust crate if it is not already installed. "
                f"Import failures: {import_failures}"
            ) from cause
    return _ALCHEMY_MODULE


class OpenAICompatModel(ProviderMetadataModel):
    """Model config for OpenAI-compatible chat/completions endpoints."""

    provider: str = "openrouter"
    id: str = "moonshotai/kimi-k2.5"
    api: str = "openai-completions"

    base_url: str = DEFAULT_OPENAI_COMPAT_CHAT_COMPLETIONS_URL


@dataclass
class AlchemyStreamResponse(BindingStreamResponseBase):
    """StreamResponse backed by a Rust stream handle."""

    invalid_event_message: str = "tinyagent._alchemy returned an invalid event"


def _convert_tools(tools: list[AgentTool] | None) -> list[dict[str, object]] | None:
    if not tools:
        return None
    out: list[dict[str, object]] = []
    for t in tools:
        out.append(
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters or {"type": "object", "properties": {}},
            }
        )
    return out


def _resolve_base_url(model: Model) -> str:
    if not isinstance(model, OpenAICompatModel):
        return DEFAULT_OPENAI_COMPAT_CHAT_COMPLETIONS_URL
    base_url = model.base_url.strip()
    if not base_url:
        raise ValueError("Model `base_url` must be a non-empty string")
    return base_url


def _resolve_provider(model: Model) -> str:
    provider = model.provider.strip()
    return provider or "openai"


def _canonicalize_api(raw_api: str) -> str:
    api = raw_api.strip().lower()
    if not api:
        return ""

    # Legacy aliases used in tinyagent Model.api values.
    if api in {"openai", "openai-compatible", "chat-completions"}:
        return "openai-completions"
    if api == "minimax":
        return "minimax-completions"

    return api


def _infer_api_from_provider(provider: str) -> str:
    provider_lc = provider.strip().lower()
    if provider_lc in {"minimax", "minimax-cn"}:
        return "minimax-completions"
    return "openai-completions"


def _resolve_model_api(model: Model, provider: str) -> str:
    """Resolve alchemy API with explicit override and provider fallback.

    Resolution order:
    1) `model.api` when present/non-empty (with legacy alias normalization)
    2) provider-based inference (`minimax|minimax-cn` => minimax-completions,
       else openai-completions)
    """

    explicit = _canonicalize_api(model.api)
    if explicit:
        return explicit

    return _infer_api_from_provider(provider)


def _resolve_api_key(model: Model, options: SimpleStreamOptions) -> str | None:
    explicit = options.api_key
    if explicit:
        return explicit

    provider = _resolve_provider(model).lower()
    env_var = _PROVIDER_API_KEY_ENV.get(provider)
    if not env_var:
        return None

    return os.environ.get(env_var)


async def stream_alchemy_openai_completions(
    model: Model,
    context: Context,
    options: SimpleStreamOptions,
) -> AlchemyStreamResponse:
    """Stream using the Rust alchemy-llm implementation (OpenAI-compatible)."""

    alchemy_llm_py = _get_alchemy_module()

    provider = _resolve_provider(model)
    base_url = _resolve_base_url(model)
    api = _resolve_model_api(model, provider)
    metadata = resolve_model_metadata(model, context_window=None, max_tokens=None)

    model_dict: dict[str, object] = {
        "id": model.id,
        "provider": provider,
        "api": api,
        "base_url": base_url,
        "name": metadata.name,
        "headers": metadata.headers,
        "reasoning": metadata.reasoning,
        "context_window": metadata.context_window,
        "max_tokens": metadata.max_tokens,
    }

    context_dict: dict[str, object] = {
        "system_prompt": context.system_prompt or "",
        "messages": [
            dump_model_dumpable(message, where="context.messages") for message in context.messages
        ],
        "tools": _convert_tools(context.tools),
    }

    options_dict: dict[str, object] = {
        "api_key": _resolve_api_key(model, options),
        "temperature": options.temperature,
        "max_tokens": options.max_tokens,
    }

    handle = alchemy_llm_py.openai_completions_stream(
        model_dict,
        context_dict,
        options_dict,
    )

    return AlchemyStreamResponse(_handle=handle)
