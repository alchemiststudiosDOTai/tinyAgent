"""
tinyagent.core.adapters
Tool calling adapter implementations and selection.
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, Sequence, get_type_hints

from pydantic import BaseModel, ConfigDict, ValidationError, create_model

from .parsing import parse_json_response
from .registry import Tool
from .schema import tool_to_json_schema

__all__ = [
    "ToolCallingMode",
    "ToolCallingAdapter",
    "ToolCallValidation",
    "OpenAIStructuredAdapter",
    "NativeToolAdapter",
    "ValidatedAdapter",
    "ParsedAdapter",
    "get_adapter",
]

TOOL_KEY = "tool"
ARGUMENTS_KEY = "arguments"
ANSWER_KEY = "answer"
SCRATCHPAD_KEY = "scratchpad"

RESPONSE_FORMAT_KEY = "response_format"
RESPONSE_TYPE_KEY = "type"
JSON_SCHEMA_KEY = "json_schema"
SCHEMA_KEY = "schema"
STRICT_KEY = "strict"
NAME_KEY = "name"

RESPONSE_SCHEMA_NAME = "agent_response"
RESPONSE_FORMAT_TYPE = "json_schema"

DEFAULT_VALIDATION_RETRIES = 2
VALIDATION_ERROR_PREFIX = "ArgValidationError: "

STRUCTURED_MODEL_PREFIXES = ("gpt-4o", "gpt-4.1", "o1", "o3", "openai/gpt-oss")

# Models that support native OpenAI-compatible tool calling
NATIVE_TOOL_MODEL_PATTERNS = (
    "gpt-3.5",
    "gpt-4",
    "claude",
    "gemini",
    "mistral",
    "llama",
    "qwen",
    "deepseek",
    "openai/",
    "anthropic/",
    "google/",
    "meta-llama/",
    "mistralai/",
)


class ToolCallingMode(Enum):
    AUTO = "auto"
    NATIVE = "native"
    STRUCTURED = "structured"
    VALIDATED = "validated"
    PARSED = "parsed"


@dataclass(frozen=True)
class ToolCallValidation:
    is_valid: bool
    error_message: str | None = None
    arguments: dict[str, Any] | None = None


class ToolCallingAdapter(Protocol):
    def format_request(
        self, tools: Sequence[Tool], messages: Sequence[dict[str, str]]
    ) -> dict[str, Any]:
        """Return kwargs to add to a chat completion request."""

    def extract_tool_call(self, response: Any) -> dict[str, Any] | None:
        """Extract a tool call payload from an LLM response (str or ChatCompletion)."""

    def validate_tool_call(
        self, payload: dict[str, Any], tools_by_name: dict[str, Tool]
    ) -> ToolCallValidation:
        """Validate tool call arguments, returning normalized arguments when applicable."""

    def format_assistant_message(self, response: Any) -> dict[str, Any]:
        """Format assistant response for memory."""

    def format_tool_result(
        self, tool_call_id: str | None, result: str, is_error: bool
    ) -> dict[str, Any]:
        """Format tool result for memory."""


class OpenAIStructuredAdapter:
    def format_request(
        self, tools: Sequence[Tool], messages: Sequence[dict[str, str]]
    ) -> dict[str, Any]:
        schema = self._build_combined_schema(tools)
        response_schema = {
            NAME_KEY: RESPONSE_SCHEMA_NAME,
            STRICT_KEY: True,
            SCHEMA_KEY: schema,
        }
        return {
            RESPONSE_FORMAT_KEY: {
                RESPONSE_TYPE_KEY: RESPONSE_FORMAT_TYPE,
                JSON_SCHEMA_KEY: response_schema,
            }
        }

    def extract_tool_call(self, response: Any) -> dict[str, Any] | None:
        return _safe_json_loads(_extract_content(response))

    def validate_tool_call(
        self, payload: dict[str, Any], tools_by_name: dict[str, Tool]
    ) -> ToolCallValidation:
        return ToolCallValidation(is_valid=True)

    def format_assistant_message(self, response: Any) -> dict[str, Any]:
        return {"role": "assistant", "content": _extract_content(response)}

    def format_tool_result(
        self, tool_call_id: str | None, result: str, is_error: bool
    ) -> dict[str, Any]:
        prefix = "" if is_error else "Observation: "
        return {"role": "user", "content": f"{prefix}{result}"}

    def _build_combined_schema(self, tools: Sequence[Tool]) -> dict[str, Any]:
        tool_variants = [self._tool_schema(tool) for tool in tools]
        answer_schema = self._answer_schema()
        scratchpad_schema = self._scratchpad_schema()
        variants = [*tool_variants, answer_schema, scratchpad_schema]
        return {"anyOf": variants}

    def _tool_schema(self, tool: Tool) -> dict[str, Any]:
        arguments_schema = tool_to_json_schema(tool)
        properties = {
            TOOL_KEY: {"enum": [tool.name]},
            ARGUMENTS_KEY: arguments_schema,
            SCRATCHPAD_KEY: {"type": "string"},
        }
        return {
            "type": "object",
            "properties": properties,
            "required": [TOOL_KEY, ARGUMENTS_KEY],
            "additionalProperties": False,
        }

    def _answer_schema(self) -> dict[str, Any]:
        properties = {
            ANSWER_KEY: {"type": "string"},
            SCRATCHPAD_KEY: {"type": "string"},
        }
        return {
            "type": "object",
            "properties": properties,
            "required": [ANSWER_KEY],
            "additionalProperties": False,
        }

    def _scratchpad_schema(self) -> dict[str, Any]:
        properties = {
            SCRATCHPAD_KEY: {"type": "string"},
        }
        return {
            "type": "object",
            "properties": properties,
            "required": [SCRATCHPAD_KEY],
            "additionalProperties": False,
        }


class ValidatedAdapter:
    max_retries: int = DEFAULT_VALIDATION_RETRIES

    def format_request(
        self, tools: Sequence[Tool], messages: Sequence[dict[str, str]]
    ) -> dict[str, Any]:
        return {}

    def extract_tool_call(self, response: Any) -> dict[str, Any] | None:
        return parse_json_response(_extract_content(response))

    def validate_tool_call(
        self, payload: dict[str, Any], tools_by_name: dict[str, Tool]
    ) -> ToolCallValidation:
        tool_name = payload.get(TOOL_KEY)
        if not tool_name:
            return ToolCallValidation(is_valid=True)

        tool = tools_by_name.get(tool_name)
        if tool is None:
            return ToolCallValidation(is_valid=True)

        raw_args = payload.get(ARGUMENTS_KEY, {})
        args = _normalize_arguments(raw_args)
        if args is None:
            return ToolCallValidation(
                is_valid=False,
                error_message="Tool arguments must be a JSON object.",
            )

        args_model = _build_args_model(tool)
        try:
            validated_args = args_model.model_validate(args)
        except ValidationError as exc:
            error_message = f"{VALIDATION_ERROR_PREFIX}{exc}"
            return ToolCallValidation(is_valid=False, error_message=error_message)

        normalized_args = validated_args.model_dump()
        return ToolCallValidation(is_valid=True, arguments=normalized_args)

    def format_assistant_message(self, response: Any) -> dict[str, Any]:
        return {"role": "assistant", "content": _extract_content(response)}

    def format_tool_result(
        self, tool_call_id: str | None, result: str, is_error: bool
    ) -> dict[str, Any]:
        prefix = "" if is_error else "Observation: "
        return {"role": "user", "content": f"{prefix}{result}"}


class ParsedAdapter:
    def format_request(
        self, tools: Sequence[Tool], messages: Sequence[dict[str, str]]
    ) -> dict[str, Any]:
        return {}

    def extract_tool_call(self, response: Any) -> dict[str, Any] | None:
        return parse_json_response(_extract_content(response))

    def validate_tool_call(
        self, payload: dict[str, Any], tools_by_name: dict[str, Tool]
    ) -> ToolCallValidation:
        return ToolCallValidation(is_valid=True)

    def format_assistant_message(self, response: Any) -> dict[str, Any]:
        return {"role": "assistant", "content": _extract_content(response)}

    def format_tool_result(
        self, tool_call_id: str | None, result: str, is_error: bool
    ) -> dict[str, Any]:
        prefix = "" if is_error else "Observation: "
        return {"role": "user", "content": f"{prefix}{result}"}


class NativeToolAdapter:
    """Adapter for models with native OpenAI-compatible tool calling."""

    # Store last tool_call_id for format_tool_result
    _last_tool_call_id: str | None = None

    def format_request(
        self, tools: Sequence[Tool], messages: Sequence[dict[str, str]]
    ) -> dict[str, Any]:
        return {"tools": [self._to_openai_tool(t) for t in tools]}

    def extract_tool_call(self, response: Any) -> dict[str, Any] | None:
        message = response.choices[0].message

        # Check for native tool calls first
        if message.tool_calls:
            tc = message.tool_calls[0]
            self._last_tool_call_id = tc.id
            args = _safe_json_loads(tc.function.arguments) or {}
            return {TOOL_KEY: tc.function.name, ARGUMENTS_KEY: args}

        # Fall back to content (for final answers)
        self._last_tool_call_id = None
        content = (message.content or "").strip()
        if content:
            return {ANSWER_KEY: content}

        return None

    def validate_tool_call(
        self, payload: dict[str, Any], tools_by_name: dict[str, Tool]
    ) -> ToolCallValidation:
        return ToolCallValidation(is_valid=True)

    def format_assistant_message(self, response: Any) -> dict[str, Any]:
        message = response.choices[0].message
        msg: dict[str, Any] = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ]
        return msg

    def format_tool_result(
        self, tool_call_id: str | None, result: str, is_error: bool
    ) -> dict[str, Any]:
        call_id = tool_call_id or self._last_tool_call_id or "unknown"
        return {"role": "tool", "tool_call_id": call_id, "content": result}

    def _to_openai_tool(self, tool: Tool) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.doc or "",
                "parameters": tool.json_schema,
            },
        }


def get_adapter(model: str, mode: ToolCallingMode = ToolCallingMode.AUTO) -> ToolCallingAdapter:
    if mode == ToolCallingMode.AUTO:
        if _supports_structured_outputs(model):
            return OpenAIStructuredAdapter()
        if _supports_native_tools(model):
            return NativeToolAdapter()
        return ValidatedAdapter()

    if mode == ToolCallingMode.NATIVE:
        return NativeToolAdapter()
    if mode == ToolCallingMode.STRUCTURED:
        return OpenAIStructuredAdapter()
    if mode == ToolCallingMode.VALIDATED:
        return ValidatedAdapter()
    if mode == ToolCallingMode.PARSED:
        return ParsedAdapter()

    raise ValueError(f"Unsupported tool calling mode: {mode}")


def _supports_structured_outputs(model: str) -> bool:
    model_lower = model.lower()
    return any(model_lower.startswith(prefix) for prefix in STRUCTURED_MODEL_PREFIXES)


def _supports_native_tools(model: str) -> bool:
    model_lower = model.lower()
    return any(pattern in model_lower for pattern in NATIVE_TOOL_MODEL_PATTERNS)


def _safe_json_loads(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _extract_content(response: Any) -> str:
    """Extract content string from response (handles both str and ChatCompletion)."""
    if isinstance(response, str):
        return response
    # ChatCompletion object
    return (response.choices[0].message.content or "").strip()


def _normalize_arguments(value: Any) -> dict[str, Any] | None:
    if value is None:
        return {}
    if not isinstance(value, dict):
        return None
    return value


def _build_args_model(tool: Tool) -> type[BaseModel]:
    hints = get_type_hints(tool.fn)
    fields: dict[str, tuple[Any, Any]] = {}
    empty_default = inspect._empty
    for name, param in tool.signature.parameters.items():
        param_type = hints.get(name, param.annotation)
        default = param.default if param.default is not empty_default else ...
        fields[name] = (param_type, default)

    config = ConfigDict(extra="forbid")
    model_name = f"{tool.name}Args"
    return create_model(model_name, __config__=config, **fields)
