#!/usr/bin/env python3
"""MiniMax tool contract example helpers used by docs and regression tests."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from tinyagent import AgentTool, AgentToolResult
from tinyagent.agent_types import JsonObject, TextContent


@dataclass(frozen=True)
class ExampleSpec:
    """Describe one MiniMax tool example contract."""

    name: str
    contract_focus: str
    tool: AgentTool
    prompt: str
    system_prompt: str


def _coerce_number_argument(args: JsonObject, name: str) -> float:
    raw = args.get(name)
    if isinstance(raw, bool) or not isinstance(raw, str | int | float):
        raise RuntimeError(f"Tool argument `{name}` must be numeric")
    try:
        return float(raw)
    except ValueError as exc:
        raise RuntimeError(f"Tool argument `{name}` must be numeric") from exc


def _coerce_int_argument(args: JsonObject, name: str) -> int:
    value = _coerce_number_argument(args, name)
    if not value.is_integer():
        raise RuntimeError(f"Tool argument `{name}` must be an integer")
    return int(value)


def _coerce_number_list_argument(args: JsonObject, name: str) -> list[float]:
    raw = args.get(name, [])
    if not isinstance(raw, list):
        raise RuntimeError(f"Tool argument `{name}` must be a list")

    values: list[float] = []
    for item in raw:
        if isinstance(item, bool) or not isinstance(item, str | int | float):
            raise RuntimeError(f"Tool argument `{name}` must contain only numbers")
        values.append(float(item))
    return values


async def add_numbers(
    tool_call_id: str,
    args: JsonObject,
    signal: asyncio.Event | None,
    on_update: Callable[[AgentToolResult], None],
) -> AgentToolResult:
    del tool_call_id, signal, on_update
    a = _coerce_number_argument(args, "a")
    b = _coerce_number_argument(args, "b")
    result = a + b
    return AgentToolResult(
        content=[TextContent(text=format(result, ".15g"))],
        details=cast(
            JsonObject,
            {"input": {"a": a, "b": b}, "output": {"sum": result}},
        ),
    )


async def convert_temperature(
    tool_call_id: str,
    args: JsonObject,
    signal: asyncio.Event | None,
    on_update: Callable[[AgentToolResult], None],
) -> AgentToolResult:
    del tool_call_id, signal, on_update
    value = _coerce_number_argument(args, "value")
    from_unit = str(args["from_unit"]).upper()
    to_unit = str(args["to_unit"]).upper()

    if from_unit == to_unit:
        converted = value
    elif from_unit == "C" and to_unit == "F":
        converted = value * 9 / 5 + 32
    elif from_unit == "F" and to_unit == "C":
        converted = (value - 32) * 5 / 9
    else:
        raise RuntimeError(f"Unsupported conversion: {from_unit} -> {to_unit}")

    rounded = round(converted, 1)
    return AgentToolResult(
        content=[TextContent(text=f"{rounded:.1f} {to_unit}")],
        details=cast(
            JsonObject,
            {
                "input": {"value": value, "unit": from_unit},
                "output": {"value": rounded, "unit": to_unit},
                "contract": {"units": ["C", "F"], "output_type": "number+unit"},
            },
        ),
    )


async def build_trip_budget(
    tool_call_id: str,
    args: JsonObject,
    signal: asyncio.Event | None,
    on_update: Callable[[AgentToolResult], None],
) -> AgentToolResult:
    del tool_call_id, signal
    nights = _coerce_int_argument(args, "nights")
    travelers = _coerce_int_argument(args, "travelers")
    nightly_rate = _coerce_number_argument(args, "nightly_rate")
    fixed_costs = _coerce_number_list_argument(args, "fixed_costs")

    lodging = nights * nightly_rate
    shared_total = sum(fixed_costs)
    trip_total = lodging + shared_total
    per_person = round(trip_total / travelers, 2)

    on_update(
        AgentToolResult(
            content=[TextContent(text="budget_calculation_started")],
            details={"stage": "costs_aggregated", "fixed_cost_count": len(fixed_costs)},
        )
    )

    return AgentToolResult(
        content=[TextContent(text=f"total ${trip_total:.2f}; per person ${per_person:.2f}")],
        details=cast(
            JsonObject,
            {
                "breakdown": {
                    "lodging": lodging,
                    "fixed_costs": fixed_costs,
                    "shared_total": shared_total,
                    "trip_total": trip_total,
                    "per_person": per_person,
                },
                "contract": {
                    "input_type": "array[number]",
                    "output_type": "nested object",
                },
            },
        ),
    )


def _build_examples() -> list[ExampleSpec]:
    return [
        ExampleSpec(
            name="Numeric Tool Contract",
            contract_focus=(
                "AgentTool -> ToolCallContent(arguments:number) -> "
                "ToolResultMessage(details.object)"
            ),
            tool=AgentTool(
                name="add_numbers",
                description="Add two numbers and return the sum.",
                parameters={
                    "type": "object",
                    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                    "required": ["a", "b"],
                },
                execute=add_numbers,
            ),
            system_prompt=(
                "You are a strict tool-using assistant. "
                "Call add_numbers exactly once before answering. "
                "Do not perform the arithmetic yourself."
            ),
            prompt=(
                "Use add_numbers exactly once with a=17 and b=25. "
                "After the tool returns, answer with one short sentence."
            ),
        ),
        ExampleSpec(
            name="Enum + Structured Output Contract",
            contract_focus=(
                "AgentTool(enum inputs) -> ToolCallContent(arguments:string enum + number) "
                "-> ToolResultMessage(details.object)"
            ),
            tool=AgentTool(
                name="convert_temperature",
                description="Convert a temperature between Celsius and Fahrenheit.",
                parameters={
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"},
                        "from_unit": {"type": "string", "enum": ["C", "F"]},
                        "to_unit": {"type": "string", "enum": ["C", "F"]},
                    },
                    "required": ["value", "from_unit", "to_unit"],
                },
                execute=convert_temperature,
            ),
            system_prompt=(
                "You are a strict tool-using assistant. "
                "Call convert_temperature exactly once before answering. "
                "Do not convert temperatures mentally."
            ),
            prompt=(
                "Convert 20 degrees C to F with convert_temperature. "
                "After the tool returns, answer with one short sentence."
            ),
        ),
        ExampleSpec(
            name="Array Input + Update Callback Contract",
            contract_focus=(
                "AgentTool(array input + on_update) -> ToolExecutionUpdateEvent -> "
                "ToolResultMessage(details.nested object)"
            ),
            tool=AgentTool(
                name="build_trip_budget",
                description=(
                    "Build a simple trip budget from nights, travelers, nightly_rate, "
                    "and fixed shared costs."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "nights": {"type": "integer", "minimum": 1},
                        "travelers": {"type": "integer", "minimum": 1},
                        "nightly_rate": {"type": "number", "minimum": 0},
                        "fixed_costs": {"type": "array", "items": {"type": "number"}},
                    },
                    "required": ["nights", "travelers", "nightly_rate", "fixed_costs"],
                },
                execute=build_trip_budget,
            ),
            system_prompt=(
                "You are a strict tool-using assistant. "
                "Call build_trip_budget exactly once before answering. "
                "Do not estimate costs without the tool."
            ),
            prompt=(
                "Use build_trip_budget for 3 nights, 2 travelers, nightly_rate 180, and "
                "fixed_costs [120, 45.5]. After the tool returns, answer with one short sentence."
            ),
        ),
    ]
