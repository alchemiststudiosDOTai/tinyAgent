"""Typed provider for the in-repo Rust binding.

This module is the new Python-side contract for `tinyagent._alchemy`.
Unlike the legacy compatibility adapter in `alchemy_provider.py`, this module
models the Rust binding payloads explicitly and only accepts the binding's
current API surface.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from typing import Literal, Protocol, TypeAlias, cast

from pydantic import BaseModel, ConfigDict, field_validator

from .agent_types import (
    Context,
    JsonObject,
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
from .provider_contracts import (
    ReasoningEffort as ReasoningEffort,
)
from .provider_contracts import (
    ReasoningMode as ReasoningMode,
)

BindingApi: TypeAlias = Literal[
    "anthropic-messages",
    "openai-completions",
    "minimax-completions",
]
DEFAULT_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "chutes": "https://llm.chutes.ai/v1/chat/completions",
    "minimax": "https://api.minimax.io/v1/chat/completions",
    "minimax-cn": "https://api.minimax.chat/v1/chat/completions",
    "kimi": "https://api.kimi.com/coding",
}

_PROVIDER_API_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "chutes": "CHUTES_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "minimax-cn": "MINIMAX_CN_API_KEY",
    "kimi": "KIMI_API_KEY",
}


class _BindingModule(Protocol):
    def openai_completions_stream(
        self,
        model: dict[str, object],
        context: dict[str, object],
        options: dict[str, object],
    ) -> BindingStreamHandle: ...


class _BindingPayloadModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RustBindingModel(ProviderMetadataModel):
    """Typed model surface for the restored Rust binding."""

    provider: str = "openrouter"
    id: str = "moonshotai/kimi-k2.5"
    api: BindingApi | Literal[""] = ""
    base_url: str | None = None

    @field_validator("api")
    @classmethod
    def _validate_api(cls, value: str) -> str:
        del cls
        valid = {"", "anthropic-messages", "openai-completions", "minimax-completions"}
        if value not in valid:
            raise ValueError(
                "api must be one of '', 'anthropic-messages', "
                "'openai-completions', or 'minimax-completions'"
            )
        return value

    @field_validator("base_url")
    @classmethod
    def _normalize_base_url(cls, value: str | None) -> str | None:
        del cls
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class BindingModelPayload(_BindingPayloadModel):
    id: str
    provider: str
    api: BindingApi
    base_url: str
    name: str | None = None
    headers: dict[str, str] | None = None
    reasoning: ReasoningMode = False
    context_window: int
    max_tokens: int


class BindingToolPayload(_BindingPayloadModel):
    name: str
    description: str
    parameters: JsonObject


class BindingContextPayload(_BindingPayloadModel):
    system_prompt: str = ""
    messages: list[dict[str, object]]
    tools: list[BindingToolPayload] | None = None


class BindingOptionsPayload(_BindingPayloadModel):
    api_key: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None


_BINDING_MODULE: _BindingModule | None = None


def _get_binding_module() -> _BindingModule:
    global _BINDING_MODULE
    if _BINDING_MODULE is None:
        package = __package__ or "tinyagent"
        import_errors: list[Exception] = []
        for module_name in (f"{package}._alchemy", "_alchemy"):
            try:
                module = importlib.import_module(module_name)
                _BINDING_MODULE = cast(_BindingModule, module)
                break
            except Exception as exc:  # pragma: no cover
                import_errors.append(exc)
        if _BINDING_MODULE is None:
            raise RuntimeError(
                "tinyagent._alchemy is not installed. "
                "Build/install the in-repo Rust binding before using "
                "tinyagent.rust_binding_provider."
            ) from import_errors[-1]
    return _BINDING_MODULE


@dataclass
class RustBindingStreamResponse(BindingStreamResponseBase):
    """StreamResponse backed by the in-repo Rust binding."""

    invalid_event_message: str = "tinyagent._alchemy returned an invalid event"


def _resolve_provider(model: Model) -> str:
    provider = model.provider.strip()
    if not provider:
        raise ValueError("Model `provider` must be a non-empty string")
    return provider


def _resolve_model_api(model: Model, provider: str) -> BindingApi:
    if isinstance(model, RustBindingModel) and model.api:
        return model.api
    explicit = model.api.strip()
    if explicit:
        allowed = {"anthropic-messages", "openai-completions", "minimax-completions"}
        if explicit not in allowed:
            raise ValueError(
                "Model `api` must be one of "
                "'anthropic-messages', 'openai-completions', or 'minimax-completions'"
            )
        return cast(BindingApi, explicit)

    provider_lc = provider.lower()
    if provider_lc == "kimi":
        return "anthropic-messages"
    if provider_lc in {"minimax", "minimax-cn"}:
        return "minimax-completions"
    return "openai-completions"


def _resolve_base_url(model: Model, provider: str) -> str:
    if isinstance(model, RustBindingModel) and model.base_url:
        return model.base_url
    base_url = getattr(model, "base_url", None)
    if isinstance(base_url, str):
        stripped = base_url.strip()
        if stripped:
            return stripped

    default = DEFAULT_BASE_URLS.get(provider.lower())
    if default:
        return default

    raise ValueError("Model `base_url` must be set for unknown providers in rust_binding_provider")


def _resolve_api_key(model: Model, options: SimpleStreamOptions) -> str | None:
    if options.api_key:
        return options.api_key

    provider = _resolve_provider(model).lower()
    env_var = _PROVIDER_API_KEY_ENV.get(provider)
    if env_var is None:
        return None
    return os.environ.get(env_var)


def _build_model_payload(model: Model) -> BindingModelPayload:
    provider = _resolve_provider(model)
    if not model.id.strip():
        raise ValueError("Model `id` must be a non-empty string")

    metadata = resolve_model_metadata(model, context_window=128_000, max_tokens=4096)

    return BindingModelPayload(
        id=model.id,
        provider=provider,
        api=_resolve_model_api(model, provider),
        base_url=_resolve_base_url(model, provider),
        name=metadata.name,
        headers=metadata.headers,
        reasoning=metadata.reasoning,
        context_window=metadata.context_window or 128_000,
        max_tokens=metadata.max_tokens or 4096,
    )


def _build_context_payload(context: Context) -> BindingContextPayload:
    tools: list[BindingToolPayload] | None = None
    if context.tools:
        tools = [
            BindingToolPayload(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters or {"type": "object", "properties": {}},
            )
            for tool in context.tools
        ]

    return BindingContextPayload(
        system_prompt=context.system_prompt or "",
        messages=[
            dump_model_dumpable(message, where="context.messages") for message in context.messages
        ],
        tools=tools,
    )


def _build_options_payload(model: Model, options: SimpleStreamOptions) -> BindingOptionsPayload:
    return BindingOptionsPayload(
        api_key=_resolve_api_key(model, options),
        temperature=options.temperature,
        max_tokens=options.max_tokens,
    )


async def stream_rust_binding(
    model: Model,
    context: Context,
    options: SimpleStreamOptions,
) -> RustBindingStreamResponse:
    """Stream via the restored Rust binding using the typed contract module."""

    binding = _get_binding_module()
    model_payload = _build_model_payload(model)
    context_payload = _build_context_payload(context)
    options_payload = _build_options_payload(model, options)

    handle = binding.openai_completions_stream(
        model_payload.model_dump(exclude_none=True),
        context_payload.model_dump(exclude_none=True),
        options_payload.model_dump(exclude_none=True),
    )
    return RustBindingStreamResponse(_handle=handle)
