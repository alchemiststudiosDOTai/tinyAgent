"""
Tests for Step type hierarchy in tinyagent.memory.steps.
"""

import time

from tinyagent.memory.steps import (
    ActionStep,
    ScratchpadStep,
    Step,
    SystemPromptStep,
    TaskStep,
)


class TestStep:
    """Test base Step class."""

    def test_step_initialization_defaults(self) -> None:
        """Step should initialize with default timestamp and step_number."""
        before = time.time()
        step = Step()
        after = time.time()

        assert before <= step.timestamp <= after
        assert step.step_number == 0

    def test_step_initialization_custom_values(self) -> None:
        """Step should accept custom timestamp and step_number."""
        step = Step(timestamp=1234567890.0, step_number=5)

        assert step.timestamp == 1234567890.0
        assert step.step_number == 5

    def test_step_to_messages_returns_empty_list(self) -> None:
        """Base Step.to_messages() should return empty list."""
        step = Step()
        messages = step.to_messages()

        assert messages == []
        assert isinstance(messages, list)


class TestSystemPromptStep:
    """Test SystemPromptStep class."""

    def test_system_prompt_step_initialization(self) -> None:
        """SystemPromptStep should initialize with content."""
        step = SystemPromptStep(content="You are a helpful assistant.")

        assert step.content == "You are a helpful assistant."
        assert step.step_number == 0

    def test_system_prompt_step_to_messages(self) -> None:
        """SystemPromptStep.to_messages() should return system message."""
        step = SystemPromptStep(content="You are a helpful assistant.")
        messages = step.to_messages()

        assert len(messages) == 1
        assert messages[0] == {"role": "system", "content": "You are a helpful assistant."}

    def test_system_prompt_step_empty_content(self) -> None:
        """SystemPromptStep with empty content should return empty system message."""
        step = SystemPromptStep(content="")
        messages = step.to_messages()

        assert len(messages) == 1
        assert messages[0] == {"role": "system", "content": ""}


class TestTaskStep:
    """Test TaskStep class."""

    def test_task_step_initialization(self) -> None:
        """TaskStep should initialize with task text."""
        step = TaskStep(task="What is 2+2?")

        assert step.task == "What is 2+2?"
        assert step.step_number == 0

    def test_task_step_to_messages(self) -> None:
        """TaskStep.to_messages() should return user message."""
        step = TaskStep(task="What is 2+2?")
        messages = step.to_messages()

        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "What is 2+2?"}

    def test_task_step_multiline_task(self) -> None:
        """TaskStep should handle multiline task text."""
        task_text = "Please do the following:\n1. First thing\n2. Second thing"
        step = TaskStep(task=task_text)
        messages = step.to_messages()

        assert messages[0]["content"] == task_text


class TestActionStep:
    """Test ActionStep class."""

    def test_action_step_initialization_defaults(self) -> None:
        """ActionStep should initialize with default empty values."""
        step = ActionStep()

        assert step.thought == ""
        assert step.tool_name == ""
        assert step.tool_args == {}
        assert step.observation == ""
        assert step.error == ""
        assert step.is_final is False
        assert step.raw_llm_response == ""

    def test_action_step_initialization_with_values(self) -> None:
        """ActionStep should accept all field values."""
        step = ActionStep(
            thought="I need to calculate",
            tool_name="calculator",
            tool_args={"a": 2, "b": 2},
            observation="4",
            error="",
            is_final=False,
            raw_llm_response='{"tool": "calculator", "arguments": {"a": 2, "b": 2}}',
        )

        assert step.thought == "I need to calculate"
        assert step.tool_name == "calculator"
        assert step.tool_args == {"a": 2, "b": 2}
        assert step.observation == "4"
        assert step.error == ""
        assert step.is_final is False

    def test_action_step_to_messages_with_observation(self) -> None:
        """ActionStep with observation should return assistant + user observation messages."""
        step = ActionStep(
            raw_llm_response='{"tool": "calc"}',
            observation="Result: 42",
        )
        messages = step.to_messages()

        assert len(messages) == 2
        assert messages[0] == {"role": "assistant", "content": '{"tool": "calc"}'}
        assert messages[1] == {"role": "user", "content": "Observation: Result: 42"}

    def test_action_step_to_messages_with_error(self) -> None:
        """ActionStep with error should return assistant + user error messages."""
        step = ActionStep(
            raw_llm_response='{"tool": "calc"}',
            error="Division by zero",
        )
        messages = step.to_messages()

        assert len(messages) == 2
        assert messages[0] == {"role": "assistant", "content": '{"tool": "calc"}'}
        assert messages[1] == {"role": "user", "content": "Error: Division by zero"}

    def test_action_step_to_messages_error_takes_precedence(self) -> None:
        """When both error and observation exist, error should be used."""
        step = ActionStep(
            raw_llm_response='{"tool": "calc"}',
            observation="Some result",
            error="An error occurred",
        )
        messages = step.to_messages()

        # Error takes precedence
        assert len(messages) == 2
        assert messages[1] == {"role": "user", "content": "Error: An error occurred"}

    def test_action_step_to_messages_no_raw_response(self) -> None:
        """ActionStep without raw_llm_response should not include assistant message."""
        step = ActionStep(observation="42")
        messages = step.to_messages()

        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "Observation: 42"}

    def test_action_step_truncate(self) -> None:
        """ActionStep.truncate() should limit observation length."""
        long_observation = "x" * 1000
        step = ActionStep(observation=long_observation)

        step.truncate(max_length=100)

        assert len(step.observation) == 103  # 100 + "..."
        assert step.observation.endswith("...")

    def test_action_step_truncate_short_observation(self) -> None:
        """ActionStep.truncate() should not change short observations."""
        short_observation = "short result"
        step = ActionStep(observation=short_observation)

        step.truncate(max_length=100)

        assert step.observation == "short result"

    def test_action_step_truncate_exact_length(self) -> None:
        """ActionStep.truncate() should handle exact max_length observations."""
        exact_observation = "x" * 100
        step = ActionStep(observation=exact_observation)

        step.truncate(max_length=100)

        assert step.observation == exact_observation  # No change at exact length


class TestScratchpadStep:
    """Test ScratchpadStep class."""

    def test_scratchpad_step_initialization(self) -> None:
        """ScratchpadStep should initialize with content."""
        step = ScratchpadStep(content="Note: User prefers JSON format")

        assert step.content == "Note: User prefers JSON format"
        assert step.raw_llm_response == ""

    def test_scratchpad_step_to_messages_with_raw_response(self) -> None:
        """ScratchpadStep with raw_llm_response should return both messages."""
        step = ScratchpadStep(
            content="Working note",
            raw_llm_response='{"scratchpad": "Working note"}',
        )
        messages = step.to_messages()

        assert len(messages) == 2
        assert messages[0] == {"role": "assistant", "content": '{"scratchpad": "Working note"}'}
        assert messages[1] == {"role": "user", "content": "Scratchpad noted: Working note"}

    def test_scratchpad_step_to_messages_without_raw_response(self) -> None:
        """ScratchpadStep without raw_llm_response should return only acknowledgment."""
        step = ScratchpadStep(content="Working note")
        messages = step.to_messages()

        assert len(messages) == 1
        assert messages[0] == {"role": "user", "content": "Scratchpad noted: Working note"}


class TestStepContrastive:
    """Contrastive tests comparing valid vs invalid step configurations."""

    def test_action_step_observation_vs_error_difference(self) -> None:
        """Compare ActionStep behavior with observation vs error."""
        # Good: ActionStep with observation
        good_step = ActionStep(
            raw_llm_response='{"tool": "calc"}',
            observation="42",
        )

        # Bad: ActionStep with error
        bad_step = ActionStep(
            raw_llm_response='{"tool": "calc"}',
            error="Tool failed",
        )

        good_messages = good_step.to_messages()
        bad_messages = bad_step.to_messages()

        # Both have same structure but different content prefix
        assert "Observation:" in good_messages[1]["content"]
        assert "Error:" in bad_messages[1]["content"]

    def test_step_type_messages_comparison(self) -> None:
        """Compare message output across all step types."""
        system_step = SystemPromptStep(content="System")
        task_step = TaskStep(task="Task")
        action_step = ActionStep(raw_llm_response='{"answer": "x"}', observation="Obs")
        scratchpad_step = ScratchpadStep(content="Note", raw_llm_response='{"scratchpad": "Note"}')

        # Each type returns different number of messages
        assert len(system_step.to_messages()) == 1  # System only
        assert len(task_step.to_messages()) == 1  # User only
        assert len(action_step.to_messages()) == 2  # Assistant + User
        assert len(scratchpad_step.to_messages()) == 2  # Assistant + User

        # Verify roles are correct
        assert system_step.to_messages()[0]["role"] == "system"
        assert task_step.to_messages()[0]["role"] == "user"
        assert action_step.to_messages()[0]["role"] == "assistant"
        assert scratchpad_step.to_messages()[0]["role"] == "assistant"
