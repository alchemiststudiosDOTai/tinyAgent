#!/usr/bin/env python3
# ruff: noqa: E402
"""Run three MiniMax tool examples and render a polished HTML report."""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import re
import sys
import webbrowser
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tinyagent import Agent, AgentOptions, AgentTool, AgentToolResult, extract_text
from tinyagent.agent_types import (
    AgentEvent,
    AssistantMessage,
    AssistantMessageEvent,
    Context,
    JsonObject,
    Model,
    SimpleStreamOptions,
    StreamResponse,
    TextContent,
    ToolResultMessage,
)
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions

DEFAULT_MINIMAX_BASE_URL = "https://api.minimax.io/v1/chat/completions"
DEFAULT_MINIMAX_MODEL = "MiniMax-M2.5"
DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_MAX_TOKENS = 256
DEFAULT_REPORT_PATH = Path.home() / ".agent" / "diagrams" / "minimax-tool-contract-examples.html"
THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


@dataclass
class ExampleSpec:
    name: str
    contract_focus: str
    tool: AgentTool
    prompt: str
    system_prompt: str


@dataclass
class ExampleRunResult:
    name: str
    contract_focus: str
    tool_name: str
    parameters: JsonObject
    assistant_text: str
    assistant_stream_event_types: list[str]
    agent_event_types: list[str]
    message_types: list[str]
    tool_result_content_types: list[str]
    tool_result_details: JsonObject


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _clean_assistant_text(message: AssistantMessage) -> str:
    text = extract_text(message)
    text = THINK_BLOCK_RE.sub("", text)
    return " ".join(text.split())


def _pretty_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def _resolve_api_key(provider: str) -> str | None:
    if provider.lower() == "minimax":
        return os.getenv("MINIMAX_API_KEY")
    return None


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


class CapturingStreamResponse(StreamResponse):
    """Wrap a provider stream and record assistant event type names."""

    def __init__(self, inner: StreamResponse, sink: list[str]):
        self._inner = inner
        self._sink = sink

    async def result(self) -> AssistantMessage:
        return await self._inner.result()

    def __aiter__(self) -> AsyncIterator[AssistantMessageEvent]:
        return self

    async def __anext__(self) -> AssistantMessageEvent:
        event = await self._inner.__anext__()
        if event.type:
            self._sink.append(event.type)
        return event


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
                        "nights": {"type": "integer"},
                        "travelers": {"type": "integer"},
                        "nightly_rate": {"type": "number"},
                        "fixed_costs": {"type": "array", "items": {"type": "number"}},
                    },
                    "required": ["nights", "travelers", "nightly_rate", "fixed_costs"],
                },
                execute=build_trip_budget,
            ),
            system_prompt=(
                "You are a strict tool-using assistant. "
                "Call build_trip_budget exactly once before answering. "
                "Use the tool for all arithmetic."
            ),
            prompt=(
                "Plan a budget for 3 nights, 2 travelers, a nightly rate of 145 dollars, "
                "and fixed shared costs [80, 45, 30]. "
                "After the tool returns, answer with one short sentence."
            ),
        ),
    ]


async def _run_example(model: OpenAICompatModel, example: ExampleSpec) -> ExampleRunResult:
    assistant_stream_event_types: list[str] = []
    agent_event_types: list[str] = []

    async def stream_fn(
        stream_model: Model,
        context: Context,
        options: SimpleStreamOptions,
    ) -> StreamResponse:
        response = await stream_alchemy_openai_completions(stream_model, context, options)
        return CapturingStreamResponse(response, assistant_stream_event_types)

    agent = Agent(
        AgentOptions(
            stream_fn=stream_fn,
            get_api_key=_resolve_api_key,
            session_id=f"examples-{example.tool.name}",
        )
    )
    agent.set_model(model)
    agent.set_tools([example.tool])
    agent.set_system_prompt(example.system_prompt)

    def on_event(event: AgentEvent) -> None:
        agent_event_types.append(event.type)

    unsubscribe = agent.subscribe(on_event)
    try:
        assistant_message = await asyncio.wait_for(
            agent.prompt(example.prompt),
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    finally:
        unsubscribe()

    if not isinstance(assistant_message, AssistantMessage):
        raise RuntimeError("Expected assistant response after tool execution")

    tool_results = [
        message for message in agent.state.messages if isinstance(message, ToolResultMessage)
    ]
    if len(tool_results) != 1:
        raise RuntimeError(
            f"{example.tool.name}: expected exactly one tool result, got {len(tool_results)}"
        )

    tool_result = tool_results[0]
    return ExampleRunResult(
        name=example.name,
        contract_focus=example.contract_focus,
        tool_name=example.tool.name,
        parameters=example.tool.parameters,
        assistant_text=_clean_assistant_text(assistant_message),
        assistant_stream_event_types=_ordered_unique(assistant_stream_event_types),
        agent_event_types=_ordered_unique(agent_event_types),
        message_types=_ordered_unique([type(message).__name__ for message in agent.state.messages]),
        tool_result_content_types=_ordered_unique(
            [type(item).__name__ for item in tool_result.content]
        ),
        tool_result_details=tool_result.details,
    )


def _render_badges(values: list[str], tone: str) -> str:
    badges = []
    for value in values:
        badges.append(f'<span class="badge badge--{tone}">{html.escape(value)}</span>')
    return "".join(badges)


def _render_example_card(index: int, result: ExampleRunResult) -> str:
    schema = html.escape(_pretty_json(result.parameters))
    details = html.escape(_pretty_json(result.tool_result_details))
    answer = html.escape(result.assistant_text)
    focus = html.escape(result.contract_focus)
    title = html.escape(result.name)
    tool_name = html.escape(result.tool_name)

    return f"""
    <section class="example-card">
      <div class="example-head">
        <div>
          <div class="eyebrow">Example {index}</div>
          <h2>{title}</h2>
        </div>
        <div class="tool-chip">{tool_name}</div>
      </div>
      <p class="focus">{focus}</p>
      <div class="answer-card">
        <div class="label">Observed Assistant Answer</div>
        <p>{answer}</p>
      </div>
      <div class="meta-grid">
        <div class="panel">
          <h3>Assistant Stream Events</h3>
          <div class="badge-row">
            {_render_badges(result.assistant_stream_event_types, "terracotta")}
          </div>
        </div>
        <div class="panel">
          <h3>Agent Events</h3>
          <div class="badge-row">
            {_render_badges(result.agent_event_types, "sage")}
          </div>
        </div>
        <div class="panel">
          <h3>Message Types</h3>
          <div class="badge-row">
            {_render_badges(result.message_types, "ink")}
          </div>
        </div>
        <div class="panel">
          <h3>Tool Result Content Types</h3>
          <div class="badge-row">
            {_render_badges(result.tool_result_content_types, "gold")}
          </div>
        </div>
      </div>
      <div class="code-grid">
        <div class="panel panel--code">
          <h3>Tool Schema</h3>
          <pre>{schema}</pre>
        </div>
        <div class="panel panel--code">
          <h3>Typed Tool Result Details</h3>
          <pre>{details}</pre>
        </div>
      </div>
    </section>
    """


def _render_html_report(results: list[ExampleRunResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    all_agent_events = _ordered_unique(
        [event for result in results for event in result.agent_event_types]
    )
    cards = "".join(_render_example_card(index + 1, result) for index, result in enumerate(results))

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MiniMax Tool Contract Examples</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link
    href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap"
    rel="stylesheet"
  >
  <style>
    :root {{
      --bg: #f7f1e8;
      --bg-2: #efe3d4;
      --surface: rgba(255, 252, 247, 0.88);
      --surface-strong: rgba(255, 250, 244, 0.96);
      --border: rgba(39, 55, 75, 0.14);
      --text: #213447;
      --text-dim: #566778;
      --terracotta: #b6542d;
      --terracotta-dim: rgba(182, 84, 45, 0.12);
      --sage: #647d5c;
      --sage-dim: rgba(100, 125, 92, 0.14);
      --gold: #bc8a2c;
      --gold-dim: rgba(188, 138, 44, 0.12);
      --ink: #314a62;
      --ink-dim: rgba(49, 74, 98, 0.12);
      --shadow: 0 28px 80px rgba(41, 37, 31, 0.09);
      --radius: 28px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(188, 138, 44, 0.16), transparent 30%),
        radial-gradient(circle at top right, rgba(100, 125, 92, 0.14), transparent 28%),
        linear-gradient(180deg, var(--bg), var(--bg-2));
      font-family: "IBM Plex Sans", sans-serif;
    }}
    .shell {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 40px 0 72px;
    }}
    .hero {{
      background: linear-gradient(145deg, rgba(255,255,255,0.74), rgba(255,248,239,0.94));
      border: 1px solid var(--border);
      border-radius: 36px;
      box-shadow: var(--shadow);
      padding: 40px;
      position: relative;
      overflow: hidden;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      inset: auto -8% -45% auto;
      width: 280px;
      height: 280px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(182,84,45,0.18), transparent 68%);
      pointer-events: none;
    }}
    .eyebrow {{
      letter-spacing: 0.14em;
      text-transform: uppercase;
      font-size: 12px;
      color: var(--terracotta);
      font-weight: 600;
    }}
    h1, h2, h3 {{
      margin: 0;
      line-height: 1.05;
    }}
    h1 {{
      margin-top: 10px;
      font-family: "Instrument Serif", serif;
      font-size: clamp(3rem, 8vw, 5.6rem);
      font-weight: 400;
      max-width: 11ch;
    }}
    .hero p {{
      max-width: 66ch;
      color: var(--text-dim);
      font-size: 1.04rem;
      line-height: 1.7;
      margin: 18px 0 0;
    }}
    .hero-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
      margin-top: 28px;
    }}
    .metric {{
      background: rgba(255,255,255,0.68);
      border: 1px solid var(--border);
      border-radius: 22px;
      padding: 18px 20px;
    }}
    .metric .value {{
      display: block;
      font-family: "Instrument Serif", serif;
      font-size: 2.1rem;
      margin-top: 6px;
    }}
    .stack {{
      display: grid;
      gap: 24px;
      margin-top: 28px;
    }}
    .example-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 28px;
      animation: rise 620ms ease both;
    }}
    .example-card:nth-child(2) {{ animation-delay: 90ms; }}
    .example-card:nth-child(3) {{ animation-delay: 180ms; }}
    .example-head {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
    }}
    h2 {{
      margin-top: 8px;
      font-family: "Instrument Serif", serif;
      font-size: clamp(2rem, 4vw, 3rem);
      font-weight: 400;
    }}
    .tool-chip {{
      border-radius: 999px;
      padding: 10px 14px;
      background: var(--ink-dim);
      color: var(--ink);
      border: 1px solid rgba(49, 74, 98, 0.16);
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.82rem;
    }}
    .focus {{
      margin: 16px 0 0;
      color: var(--text-dim);
      line-height: 1.7;
      max-width: 80ch;
    }}
    .answer-card {{
      margin-top: 22px;
      padding: 22px 24px;
      border-radius: 24px;
      background:
        linear-gradient(140deg, rgba(255,255,255,0.78), rgba(255,248,244,0.96));
      border: 1px solid rgba(182, 84, 45, 0.14);
    }}
    .answer-card p {{
      margin: 10px 0 0;
      font-size: 1.15rem;
      line-height: 1.6;
    }}
    .label {{
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 0.72rem;
      color: var(--terracotta);
      font-weight: 600;
    }}
    .meta-grid, .code-grid {{
      display: grid;
      gap: 16px;
      margin-top: 20px;
    }}
    .meta-grid {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .code-grid {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .panel {{
      background: var(--surface-strong);
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 18px 18px 20px;
    }}
    .panel h3 {{
      font-size: 0.9rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--text-dim);
      font-weight: 600;
    }}
    .badge-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 14px;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      padding: 8px 11px;
      font-size: 0.78rem;
      line-height: 1;
      border: 1px solid transparent;
      font-family: "IBM Plex Mono", monospace;
    }}
    .badge--terracotta {{
      color: var(--terracotta);
      background: var(--terracotta-dim);
      border-color: rgba(182, 84, 45, 0.16);
    }}
    .badge--sage {{
      color: var(--sage);
      background: var(--sage-dim);
      border-color: rgba(100, 125, 92, 0.16);
    }}
    .badge--gold {{
      color: var(--gold);
      background: var(--gold-dim);
      border-color: rgba(188, 138, 44, 0.18);
    }}
    .badge--ink {{
      color: var(--ink);
      background: var(--ink-dim);
      border-color: rgba(49, 74, 98, 0.16);
    }}
    .panel--code pre {{
      margin: 14px 0 0;
      padding: 18px;
      border-radius: 18px;
      background: #1f2a33;
      color: #edf3f7;
      overflow-x: auto;
      font-size: 0.82rem;
      line-height: 1.55;
      font-family: "IBM Plex Mono", monospace;
    }}
    .footer {{
      margin-top: 24px;
      color: var(--text-dim);
      font-size: 0.9rem;
    }}
    @keyframes rise {{
      from {{ opacity: 0; transform: translateY(24px) scale(0.985); }}
      to {{ opacity: 1; transform: translateY(0) scale(1); }}
    }}
    @media (max-width: 900px) {{
      .hero, .example-card {{ padding: 24px; }}
      .hero-grid, .meta-grid, .code-grid {{ grid-template-columns: 1fr; }}
      .example-head {{ flex-direction: column; }}
      .tool-chip {{ align-self: flex-start; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      .example-card {{ animation: none; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">MiniMax Live Example Report</div>
      <h1>Tool Contracts, but actually readable.</h1>
      <p>
        This report turns the raw runtime dump into a visual pass across three real
        MiniMax tool calls: the schema, the event flow, the typed tool result payload,
        and the final assistant answer.
      </p>
      <div class="hero-grid">
        <div class="metric">
          <div class="eyebrow">Examples</div>
          <span class="value">{len(results)}</span>
        </div>
        <div class="metric">
          <div class="eyebrow">Unique Agent Events</div>
          <span class="value">{len(all_agent_events)}</span>
        </div>
        <div class="metric">
          <div class="eyebrow">Output</div>
          <span class="value">HTML</span>
        </div>
      </div>
    </section>
    <section class="stack">
      {cards}
    </section>
    <p class="footer">Generated by examples/minimax_tool_contract_examples.py</p>
  </main>
</body>
</html>
"""
    output_path.write_text(html_text, encoding="utf-8")


def _browser_hint() -> str:
    if sys.platform == "darwin":
        return "open"
    return "xdg-open"


def _print_terminal_summary(results: list[ExampleRunResult], report_path: Path) -> None:
    print("MiniMax Tool Contract Examples")
    print()
    for result in results:
        print(f"- {result.name}: {result.assistant_text}")
    print()
    print(f"HTML report: {report_path}")
    print(f"Open it with: {_browser_hint()} {report_path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="HTML report output path.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the generated HTML report in a browser.",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    load_dotenv(REPO_ROOT / ".env")

    if not os.getenv("MINIMAX_API_KEY"):
        raise RuntimeError("MINIMAX_API_KEY is required for these live examples")

    model = OpenAICompatModel(
        provider="minimax",
        api="minimax-completions",
        id=os.getenv("MINIMAX_MODEL", DEFAULT_MINIMAX_MODEL),
        base_url=os.getenv("MINIMAX_BASE_URL", DEFAULT_MINIMAX_BASE_URL),
        max_tokens=int(os.getenv("HARNESS_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))),
    )

    results: list[ExampleRunResult] = []
    for example in _build_examples():
        results.append(await _run_example(model, example))

    report_path = args.output.expanduser()
    _render_html_report(results, report_path)
    _print_terminal_summary(results, report_path)

    if args.open:
        webbrowser.open(report_path.resolve().as_uri())


if __name__ == "__main__":
    asyncio.run(main())
