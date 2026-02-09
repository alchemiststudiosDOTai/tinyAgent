"""OpenRouter provider for the agent framework.

Implements streaming LLM calls via the OpenRouter API.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from typing import TypeGuard, cast

import httpx

from .agent_types import (
    AgentTool,
    AssistantContent,
    AssistantMessage,
    AssistantMessageEvent,
    Context,
    JsonObject,
    Message,
    Model,
    SimpleStreamOptions,
    TextContent,
    ToolCallContent,
    ToolResultMessage,
    UserMessage,
)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


def _openrouter_debug_enabled() -> bool:
    return os.environ.get("TINYAGENT_OPENROUTER_DEBUG", "").lower() in {"1", "true", "yes"}


def _openrouter_debug(msg: str) -> None:
    if not _openrouter_debug_enabled():
        return
    print(f"[tinyagent.openrouter] {msg}", file=sys.stderr, flush=True)


def _build_usage_dict(usage: dict[str, object]) -> JsonObject:
    """Build a normalized usage dict from API response usage, including cache stats."""
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    cache_write = usage.get("cache_creation_input_tokens", 0)
    # OpenRouter may also use prompt_tokens_details for cache info
    details = usage.get("prompt_tokens_details")
    if isinstance(details, dict):
        if not cache_read:
            cache_read = details.get("cached_tokens", 0)
        if not cache_write:
            # OpenRouter uses `cache_write_tokens` in prompt_tokens_details.
            cache_write = details.get("cache_write_tokens", 0)

    if not isinstance(input_tokens, int | float):
        input_tokens = 0
    if not isinstance(output_tokens, int | float):
        output_tokens = 0
    if not isinstance(cache_read, int | float):
        cache_read = 0
    if not isinstance(cache_write, int | float):
        cache_write = 0

    return cast(
        JsonObject,
        {
            "input": int(input_tokens),
            "output": int(output_tokens),
            "cacheRead": int(cache_read),
            "cacheWrite": int(cache_write),
            "totalTokens": int(input_tokens) + int(output_tokens),
        },
    )


def _context_has_cache_control(context: Context) -> bool:
    """Check if any message in the context has cache_control on a content block."""
    for msg in context.messages:
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("cache_control"):
                return True
    return False


@dataclass
class OpenRouterModel(Model):
    """OpenRouter model configuration."""

    provider: str = "openrouter"
    id: str = "anthropic/claude-3.5-sonnet"
    api: str = "openrouter"

    # OpenRouter-specific request controls.
    # Passed through to the OpenRouter request body as `provider` / `route`.
    # See: https://openrouter.ai/docs (provider routing)
    openrouter_provider: dict[str, object] | None = None
    openrouter_route: str | None = None


def _convert_tools_to_openai_format(
    tools: list[AgentTool] | None,
) -> list[dict[str, object]] | None:
    if not tools:
        return None

    result: list[dict[str, object]] = []
    for tool in tools:
        result.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters or {"type": "object", "properties": {}},
                },
            }
        )
    return result


def _is_text_content(content: AssistantContent | None) -> TypeGuard[TextContent]:
    return content is not None and content.get("type") == "text"


def _extract_text_parts(blocks: list[TextContent | dict[str, object]]) -> list[str]:
    text_parts: list[str] = []
    for part in blocks:
        if isinstance(part, dict) and part.get("type") == "text":
            value = part.get("text")
            if isinstance(value, str):
                text_parts.append(value)
    return text_parts


def _any_block_has_cache_control(blocks: list[TextContent | dict[str, object]]) -> bool:
    """Check if any content block carries a cache_control directive."""
    return any(isinstance(block, dict) and block.get("cache_control") for block in blocks)


def _convert_content_blocks_structured(
    blocks: list[TextContent | dict[str, object]],
) -> list[dict[str, object]]:
    """Convert content blocks to structured format preserving cache_control."""
    result: list[dict[str, object]] = []
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        entry: dict[str, object] = {"type": "text", "text": block.get("text", "")}
        cc = block.get("cache_control")
        if cc:
            entry["cache_control"] = cc
        result.append(entry)
    return result


def _convert_user_message(msg: UserMessage) -> dict[str, object]:
    content = msg.get("content", [])
    blocks = cast(list[TextContent | dict[str, object]], content)
    if _any_block_has_cache_control(blocks):
        return {"role": "user", "content": _convert_content_blocks_structured(blocks)}
    text_parts = _extract_text_parts(blocks)
    return {"role": "user", "content": "\n".join(text_parts)}


def _convert_assistant_message(msg: AssistantMessage) -> dict[str, object]:
    content = msg.get("content", [])
    text_parts: list[str] = []
    tool_calls: list[dict[str, object]] = []

    for part in content:
        if not part:
            continue

        ptype = part.get("type")
        if ptype == "text":
            text_val = part.get("text")
            if isinstance(text_val, str):
                text_parts.append(text_val)
        elif ptype == "tool_call":
            tc_args: JsonObject = cast(JsonObject, part.get("arguments", {}))
            tool_calls.append(
                {
                    "id": part.get("id"),
                    "type": "function",
                    "function": {
                        "name": part.get("name"),
                        "arguments": json.dumps(tc_args),
                    },
                }
            )

    msg_dict: dict[str, object] = {"role": "assistant"}
    if text_parts:
        msg_dict["content"] = "\n".join(text_parts)
    if tool_calls:
        msg_dict["tool_calls"] = tool_calls
    return msg_dict


def _convert_tool_result_message(msg: ToolResultMessage) -> dict[str, object]:
    tool_call_id = msg.get("tool_call_id")
    content = msg.get("content", [])
    text_parts = _extract_text_parts(cast(list[TextContent | dict[str, object]], content))
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": "\n".join(text_parts),
    }


def _convert_messages_to_openai_format(messages: list[Message]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []

    for msg in messages:
        role = msg.get("role")
        if role == "user":
            result.append(_convert_user_message(cast(UserMessage, msg)))
        elif role == "assistant":
            result.append(_convert_assistant_message(cast(AssistantMessage, msg)))
        elif role == "tool_result":
            result.append(_convert_tool_result_message(cast(ToolResultMessage, msg)))

    return result


@dataclass
class OpenRouterStreamResponse:
    """Streaming response from OpenRouter."""

    _final_message: AssistantMessage | None = None
    _events: list[AssistantMessageEvent] = field(default_factory=list)
    _index: int = 0

    async def result(self) -> AssistantMessage:
        if self._final_message is None:
            raise RuntimeError("No final message available")
        return self._final_message

    def __aiter__(self) -> OpenRouterStreamResponse:
        return self

    async def __anext__(self) -> AssistantMessageEvent:
        if self._index >= len(self._events):
            raise StopAsyncIteration
        event = self._events[self._index]
        self._index += 1
        return event


def _build_request_body(
    model_id: str,
    messages: list[dict[str, object]],
    tools: list[dict[str, object]] | None,
    options: SimpleStreamOptions,
) -> dict[str, object]:
    request_body: dict[str, object] = {
        "model": model_id,
        "messages": messages,
        "stream": True,
    }

    if tools:
        request_body["tools"] = tools

    temperature = options.get("temperature")
    if temperature is not None:
        request_body["temperature"] = temperature

    max_tokens = options.get("max_tokens")
    if max_tokens:
        request_body["max_tokens"] = max_tokens

    return request_body


def _handle_text_delta(
    delta: dict[str, object],
    current_text: str,
    partial: AssistantMessage,
    response: OpenRouterStreamResponse,
) -> str:
    content = delta.get("content")
    if not isinstance(content, str) or not content:
        return current_text

    current_text += content

    content_list = partial.get("content")
    if content_list is None:
        content_list = []
        partial["content"] = content_list

    last_content = content_list[-1] if content_list else None
    if not _is_text_content(last_content):
        content_list.append({"type": "text", "text": current_text})
    else:
        last_content["text"] = current_text

    response._events.append({"type": "text_delta", "partial": partial, "delta": content})
    return current_text


def _handle_tool_call_delta(
    delta: dict[str, object],
    tool_calls_map: dict[int, dict[str, str]],
    partial: AssistantMessage,
    response: OpenRouterStreamResponse,
) -> None:
    tool_calls = delta.get("tool_calls")
    if not isinstance(tool_calls, list):
        return

    for tc_raw in tool_calls:
        if not isinstance(tc_raw, dict):
            continue

        idx = tc_raw.get("index")
        idx_int = idx if isinstance(idx, int) else 0

        if idx_int not in tool_calls_map:
            tool_calls_map[idx_int] = {"id": "", "name": "", "arguments": ""}

        tc_id = tc_raw.get("id")
        if isinstance(tc_id, str) and tc_id:
            tool_calls_map[idx_int]["id"] = tc_id

        func = tc_raw.get("function")
        if isinstance(func, dict):
            name = func.get("name")
            if isinstance(name, str) and name:
                tool_calls_map[idx_int]["name"] = name
            args = func.get("arguments")
            if isinstance(args, str) and args:
                tool_calls_map[idx_int]["arguments"] += args

        response._events.append({"type": "tool_call_delta", "partial": partial})


def _finalize_tool_calls(
    tool_calls_map: dict[int, dict[str, str]], partial: AssistantMessage
) -> None:
    content_list = partial.get("content")
    if content_list is None:
        content_list = []
        partial["content"] = content_list

    for idx in sorted(tool_calls_map.keys()):
        tc = tool_calls_map[idx]

        args: JsonObject
        try:
            parsed = json.loads(tc["arguments"]) if tc["arguments"] else {}
            args = cast(JsonObject, parsed) if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            args = {}

        content_list.append(
            cast(
                ToolCallContent,
                {
                    "type": "tool_call",
                    "id": tc["id"],
                    "name": tc["name"],
                    "arguments": args,
                },
            )
        )


@dataclass(frozen=True)
class _OpenRouterSseEvent:
    done: bool
    delta: dict[str, object] | None = None
    finish_reason: str | None = None
    usage: dict[str, object] | None = None


def _extract_sse_data(line: str) -> str | None:
    if not line.startswith("data: "):
        return None
    return line[6:].strip()


def _parse_openrouter_chunk(
    data: str,
) -> tuple[dict[str, object], str | None, dict[str, object] | None] | None:
    try:
        chunk_raw = json.loads(data)
    except json.JSONDecodeError:
        return None

    if not isinstance(chunk_raw, dict):
        return None

    # Extract usage from the top-level chunk (present in final chunk)
    usage_raw = chunk_raw.get("usage")
    usage = cast(dict[str, object], usage_raw) if isinstance(usage_raw, dict) else None

    choices = chunk_raw.get("choices")
    if not isinstance(choices, list) or not choices:
        # Some chunks only have usage, no choices
        if usage:
            return {}, None, usage
        return None

    choice0 = choices[0]
    if not isinstance(choice0, dict):
        return None

    delta_raw = choice0.get("delta")
    delta = cast(dict[str, object], delta_raw) if isinstance(delta_raw, dict) else {}

    finish_raw = choice0.get("finish_reason")
    finish_reason = finish_raw if isinstance(finish_raw, str) and finish_raw else None

    return delta, finish_reason, usage


def _parse_openrouter_sse_line(line: str) -> _OpenRouterSseEvent | None:
    data = _extract_sse_data(line)
    if data is None:
        return None

    if data == "[DONE]":
        return _OpenRouterSseEvent(done=True)

    parsed = _parse_openrouter_chunk(data)
    if parsed is None:
        return None

    delta, finish_reason, usage = parsed
    return _OpenRouterSseEvent(done=False, delta=delta, finish_reason=finish_reason, usage=usage)


def _add_openrouter_system_prompt(
    messages: list[dict[str, object]],
    system_prompt: str | None,
    caching_active: bool,
) -> None:
    if not system_prompt:
        return

    if caching_active:
        messages.insert(
            0,
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            },
        )
        return

    messages.insert(0, {"role": "system", "content": system_prompt})


def _apply_openrouter_routing_controls(
    request_body: dict[str, object],
    model: OpenRouterModel,
) -> None:
    if isinstance(model.openrouter_provider, dict):
        request_body["provider"] = model.openrouter_provider

    route = model.openrouter_route
    if isinstance(route, str) and route:
        request_body["route"] = route


def _build_openrouter_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _debug_openrouter_request(
    model_id: str,
    caching_active: bool,
    headers: dict[str, str],
    request_body: dict[str, object],
) -> None:
    if not _openrouter_debug_enabled():
        return

    redacted_headers = {k: v for k, v in headers.items() if k.lower() != "authorization"}
    _openrouter_debug(f"model={model_id} caching_active={caching_active}")
    _openrouter_debug(f"request headers={json.dumps(redacted_headers, indent=2)}")
    _openrouter_debug(f"request body={json.dumps(request_body, indent=2)}")


async def _raise_for_openrouter_error(http_response: httpx.Response) -> None:
    if http_response.status_code == 200:
        return

    error_data = await http_response.aread()
    raise RuntimeError(f"OpenRouter error {http_response.status_code}: {error_data.decode()}")


def _debug_openrouter_response_headers(http_response: httpx.Response) -> None:
    if not _openrouter_debug_enabled():
        return

    _openrouter_debug(
        "response headers=" + json.dumps({k: v for k, v in http_response.headers.items()}, indent=2)
    )


async def _consume_openrouter_sse(
    http_response: httpx.Response,
    response: OpenRouterStreamResponse,
    partial: AssistantMessage,
    tool_calls_map: dict[int, dict[str, str]],
) -> None:
    current_text = ""
    debug = _openrouter_debug_enabled()

    async for line in http_response.aiter_lines():
        parsed = _parse_openrouter_sse_line(line)
        if parsed is None:
            continue
        if parsed.done:
            break

        delta = parsed.delta or {}
        current_text = _handle_text_delta(delta, current_text, partial, response)
        _handle_tool_call_delta(delta, tool_calls_map, partial, response)

        if parsed.usage:
            if debug:
                clip = line if len(line) <= 2000 else (line[:2000] + "…")
                _openrouter_debug(f"raw SSE line (usage chunk)={clip}")
                _openrouter_debug(f"parsed usage dict={json.dumps(parsed.usage, indent=2)}")

            partial["usage"] = _build_usage_dict(parsed.usage)

            if debug:
                _openrouter_debug(f"normalized usage={json.dumps(partial['usage'], indent=2)}")

        if parsed.finish_reason:
            partial["stop_reason"] = (
                "tool_calls" if parsed.finish_reason == "tool_calls" else "complete"
            )


async def stream_openrouter(
    model: Model,
    context: Context,
    options: SimpleStreamOptions,
) -> OpenRouterStreamResponse:
    """Stream a response from OpenRouter."""

    api_key = options.get("api_key") or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OpenRouter API key required")

    messages = _convert_messages_to_openai_format(context.messages)

    # Detect if any message carries cache_control (prompt caching is active)
    caching_active = _context_has_cache_control(context)
    _add_openrouter_system_prompt(messages, context.system_prompt, caching_active)

    tools = _convert_tools_to_openai_format(context.tools)
    request_body = _build_request_body(model.id, messages, tools, options)

    # OpenRouter routing controls (optional)
    _apply_openrouter_routing_controls(request_body, cast(OpenRouterModel, model))

    headers = _build_openrouter_headers(api_key)
    _debug_openrouter_request(model.id, caching_active, headers, request_body)

    response = OpenRouterStreamResponse()
    partial: AssistantMessage = {
        "role": "assistant",
        "content": [],
        "stop_reason": None,
        "timestamp": int(asyncio.get_event_loop().time() * 1000),
    }
    tool_calls_map: dict[int, dict[str, str]] = {}

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            OPENROUTER_API_URL,
            headers=headers,
            json=request_body,
            timeout=None,
        ) as http_response:
            await _raise_for_openrouter_error(http_response)
            _debug_openrouter_response_headers(http_response)

            response._events.append({"type": "start", "partial": partial})
            await _consume_openrouter_sse(http_response, response, partial, tool_calls_map)

    _finalize_tool_calls(tool_calls_map, partial)
    response._final_message = partial
    response._events.append({"type": "done", "partial": partial})

    return response
