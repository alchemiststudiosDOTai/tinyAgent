import pytest

from tinyagent.tools.builtin.planning import create_plan, get_plan, update_plan


def test_create_plan_initializes_with_expected_defaults() -> None:
    plan = create_plan("Ship feature", context="Docs for planning")

    assert plan["goal"] == "Ship feature"
    assert plan["status"] == "created"
    assert plan["steps"] == []
    assert plan["context"] == "Docs for planning"
    assert isinstance(plan["id"], str) and plan["id"]

    retrieved = get_plan(plan["id"])
    assert retrieved == plan


def test_update_plan_applies_steps_and_status() -> None:
    plan = create_plan("Write tutorial")

    updated = update_plan(
        plan["id"],
        {
            "steps": ["Outline sections", "Draft content"],
            "status": "in_progress",
        },
    )

    assert updated["steps"] == ["Outline sections", "Draft content"]
    assert updated["status"] == "in_progress"
    assert get_plan(plan["id"]) == updated


def test_get_plan_unknown_id_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Plan with id 'missing' not found"):
        get_plan("missing")


def test_update_plan_validates_steps_type() -> None:
    plan = create_plan("Validate steps")

    with pytest.raises(ValueError, match="steps must only contain strings"):
        update_plan(plan["id"], {"steps": ["first", 2]})


def test_update_plan_requires_non_empty_payload() -> None:
    plan = create_plan("Check payload")

    with pytest.raises(ValueError, match="updates cannot be empty"):
        update_plan(plan["id"], {})


def test_update_plan_rejects_unknown_keys() -> None:
    plan = create_plan("Validate keys")

    with pytest.raises(ValueError, match="Unsupported update keys"):
        update_plan(plan["id"], {"owner": "codex"})
