"""Simple planning tools with in-memory storage for plans."""

from __future__ import annotations

import uuid
from typing import Any

from tinyagent.core.registry import tool

_PLANS: dict[str, dict[str, Any]] = {}


def _get_plan(plan_id: str) -> dict[str, Any]:
    try:
        return _PLANS[plan_id]
    except KeyError as exc:
        raise ValueError(f"Plan with id '{plan_id}' not found") from exc


def _validate_steps(candidate: Any) -> None:
    if not isinstance(candidate, list):
        raise ValueError("steps must be provided as a list of strings")
    if not all(isinstance(step, str) for step in candidate):
        raise ValueError("steps must only contain strings")


@tool
def create_plan(goal: str, context: str = "") -> dict[str, Any]:
    """Create a new plan and store it in memory."""

    plan_id = uuid.uuid4().hex
    plan = {
        "id": plan_id,
        "goal": goal,
        "context": context,
        "steps": [],
        "status": "created",
    }
    _PLANS[plan_id] = plan
    return plan.copy()


@tool
def update_plan(plan_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Update an existing plan with new values."""

    if not updates:
        raise ValueError("updates cannot be empty")

    plan = _get_plan(plan_id)

    allowed_keys = {"goal", "context", "steps", "status"}
    unknown_keys = set(updates) - allowed_keys
    if unknown_keys:
        allowed_list = ", ".join(sorted(allowed_keys))
        raise ValueError(
            f"Unsupported update keys: {sorted(unknown_keys)}; allowed: {allowed_list}"
        )

    if "goal" in updates and not isinstance(updates["goal"], str):
        raise ValueError("goal must be a string")
    if "context" in updates and not isinstance(updates["context"], str):
        raise ValueError("context must be a string")
    if "status" in updates and not isinstance(updates["status"], str):
        raise ValueError("status must be a string")
    if "steps" in updates:
        _validate_steps(updates["steps"])

    plan.update(updates)
    return plan.copy()


@tool
def get_plan(plan_id: str) -> dict[str, Any]:
    """Retrieve a plan by its identifier."""

    plan = _get_plan(plan_id)
    return plan.copy()
