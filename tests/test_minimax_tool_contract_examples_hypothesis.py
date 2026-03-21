"""Property-based tests for the MiniMax tool contract examples."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, cast

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from examples.minimax_tool_contract_examples import (
    _build_examples,
    add_numbers,
    build_trip_budget,
    convert_temperature,
)
from tinyagent.agent_types import AgentToolResult, JsonObject, TextContent

FLOATS = st.floats(
    min_value=-1_000_000,
    max_value=1_000_000,
    allow_nan=False,
    allow_infinity=False,
)
NON_NEGATIVE_FLOATS = st.floats(
    min_value=0,
    max_value=10_000,
    allow_nan=False,
    allow_infinity=False,
)
ToolFn = Callable[
    [str, JsonObject, asyncio.Event | None, Callable[[AgentToolResult], None]],
    Coroutine[Any, Any, AgentToolResult],
]


def _run_tool(
    tool_fn: ToolFn,
    args: JsonObject,
    on_update: Callable[[AgentToolResult], None] | None = None,
) -> AgentToolResult:
    callback = on_update or (lambda update: None)
    result: AgentToolResult = asyncio.run(tool_fn("tc_test", args, None, callback))
    assert isinstance(result, AgentToolResult)
    return result


def _extract_single_text(result: AgentToolResult) -> str:
    assert len(result.content) == 1
    item = result.content[0]
    assert isinstance(item, TextContent)
    assert isinstance(item.text, str)
    return item.text


class TestMiniMaxToolContractExamples:
    """Example metadata and tool outputs remain internally consistent."""

    def test_examples_expose_exactly_three_distinct_tools(self) -> None:
        examples = _build_examples()

        assert len(examples) == 3
        assert [example.tool.name for example in examples] == [
            "add_numbers",
            "convert_temperature",
            "build_trip_budget",
        ]
        assert all(example.tool.execute is not None for example in examples)

    @settings(deadline=None, max_examples=100)
    @given(a=FLOATS, b=FLOATS)
    def test_add_numbers_matches_numeric_contract(self, a: float, b: float) -> None:
        result = _run_tool(add_numbers, {"a": a, "b": b})

        sum_text = _extract_single_text(result)
        expected = a + b

        assert float(sum_text) == pytest.approx(expected)
        assert result.details["input"] == {"a": a, "b": b}
        assert result.details["output"] == pytest.approx({"sum": expected})

    @settings(deadline=None, max_examples=100)
    @given(value=FLOATS, from_unit=st.sampled_from(["C", "F"]), to_unit=st.sampled_from(["C", "F"]))
    def test_convert_temperature_matches_formula(
        self,
        value: float,
        from_unit: str,
        to_unit: str,
    ) -> None:
        result = _run_tool(
            convert_temperature,
            {"value": value, "from_unit": from_unit, "to_unit": to_unit},
        )

        if from_unit == to_unit:
            expected = value
        elif from_unit == "C":
            expected = value * 9 / 5 + 32
        else:
            expected = (value - 32) * 5 / 9

        rounded = round(expected, 1)
        output_text = _extract_single_text(result)

        assert output_text == f"{rounded:.1f} {to_unit}"
        assert result.details["input"] == {"value": value, "unit": from_unit}
        assert result.details["output"] == {"value": rounded, "unit": to_unit}

    @settings(deadline=None, max_examples=100)
    @given(
        nights=st.integers(min_value=1, max_value=30),
        travelers=st.integers(min_value=1, max_value=10),
        nightly_rate=NON_NEGATIVE_FLOATS,
        fixed_costs=st.lists(NON_NEGATIVE_FLOATS, max_size=8),
    )
    def test_build_trip_budget_returns_nested_breakdown_and_update(
        self,
        nights: int,
        travelers: int,
        nightly_rate: float,
        fixed_costs: list[float],
    ) -> None:
        updates: list[AgentToolResult] = []

        result = _run_tool(
            build_trip_budget,
            cast(
                JsonObject,
                {
                    "nights": nights,
                    "travelers": travelers,
                    "nightly_rate": nightly_rate,
                    "fixed_costs": fixed_costs,
                },
            ),
            on_update=updates.append,
        )

        assert len(updates) == 1
        assert _extract_single_text(updates[0]) == "budget_calculation_started"
        assert updates[0].details == {
            "stage": "costs_aggregated",
            "fixed_cost_count": len(fixed_costs),
        }

        lodging = nights * nightly_rate
        shared_total = sum(fixed_costs)
        trip_total = lodging + shared_total
        per_person = round(trip_total / travelers, 2)

        assert _extract_single_text(result) == (
            f"total ${trip_total:.2f}; per person ${per_person:.2f}"
        )
        breakdown = result.details["breakdown"]
        assert isinstance(breakdown, dict)
        assert breakdown["lodging"] == lodging
        assert breakdown["fixed_costs"] == fixed_costs
        assert breakdown["shared_total"] == shared_total
        assert breakdown["trip_total"] == trip_total
        assert breakdown["per_person"] == per_person

        contract = result.details["contract"]
        assert contract == {
            "input_type": "array[number]",
            "output_type": "nested object",
        }
