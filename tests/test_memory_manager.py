"""
Tests for MemoryManager and pruning strategies in tinyagent.memory.manager.
"""

from tinyagent.memory.manager import (
    MemoryManager,
    keep_last_n_steps,
    no_pruning,
    prune_old_observations,
)
from tinyagent.memory.steps import (
    ActionStep,
    ScratchpadStep,
    SystemPromptStep,
    TaskStep,
)


class TestMemoryManager:
    """Test MemoryManager class."""

    def test_memory_manager_initialization_empty(self) -> None:
        """MemoryManager should initialize with empty steps list."""
        manager = MemoryManager()

        assert manager.steps == []
        assert len(manager.steps) == 0

    def test_memory_manager_add_step(self) -> None:
        """MemoryManager.add() should append steps with correct numbering."""
        manager = MemoryManager()

        step1 = SystemPromptStep(content="System")
        step2 = TaskStep(task="Task")

        manager.add(step1)
        manager.add(step2)

        assert len(manager.steps) == 2
        assert manager.steps[0].step_number == 0
        assert manager.steps[1].step_number == 1

    def test_memory_manager_to_messages(self) -> None:
        """MemoryManager.to_messages() should aggregate all step messages."""
        manager = MemoryManager()

        manager.add(SystemPromptStep(content="You are helpful"))
        manager.add(TaskStep(task="What is 2+2?"))
        manager.add(
            ActionStep(
                raw_llm_response='{"tool": "calc"}',
                observation="4",
            )
        )

        messages = manager.to_messages()

        assert len(messages) == 4
        assert messages[0] == {"role": "system", "content": "You are helpful"}
        assert messages[1] == {"role": "user", "content": "What is 2+2?"}
        assert messages[2] == {"role": "assistant", "content": '{"tool": "calc"}'}
        assert messages[3] == {"role": "user", "content": "Observation: 4"}

    def test_memory_manager_clear(self) -> None:
        """MemoryManager.clear() should remove all steps."""
        manager = MemoryManager()

        manager.add(SystemPromptStep(content="System"))
        manager.add(TaskStep(task="Task"))

        assert len(manager.steps) == 2

        manager.clear()

        assert len(manager.steps) == 0
        assert manager.steps == []

    def test_memory_manager_get_steps_by_type(self) -> None:
        """MemoryManager.get_steps_by_type() should filter steps correctly."""
        manager = MemoryManager()

        manager.add(SystemPromptStep(content="System"))
        manager.add(TaskStep(task="Task"))
        manager.add(ActionStep(observation="Obs1"))
        manager.add(ActionStep(observation="Obs2"))
        manager.add(ScratchpadStep(content="Note"))

        system_steps = manager.get_steps_by_type(SystemPromptStep)
        task_steps = manager.get_steps_by_type(TaskStep)
        action_steps = manager.get_steps_by_type(ActionStep)
        scratchpad_steps = manager.get_steps_by_type(ScratchpadStep)

        assert len(system_steps) == 1
        assert len(task_steps) == 1
        assert len(action_steps) == 2
        assert len(scratchpad_steps) == 1

    def test_memory_manager_action_count(self) -> None:
        """MemoryManager.action_count should return count of ActionSteps."""
        manager = MemoryManager()

        assert manager.action_count == 0

        manager.add(SystemPromptStep(content="System"))
        manager.add(TaskStep(task="Task"))
        assert manager.action_count == 0

        manager.add(ActionStep(observation="Obs1"))
        assert manager.action_count == 1

        manager.add(ActionStep(observation="Obs2"))
        manager.add(ActionStep(observation="Obs3"))
        assert manager.action_count == 3


class TestKeepLastNSteps:
    """Test keep_last_n_steps pruning strategy."""

    def test_keep_last_n_preserves_critical_steps(self) -> None:
        """keep_last_n_steps should always preserve SystemPromptStep and TaskStep."""
        manager = MemoryManager()

        manager.add(SystemPromptStep(content="System"))
        manager.add(TaskStep(task="Task"))
        manager.add(ActionStep(observation="Obs1"))
        manager.add(ActionStep(observation="Obs2"))
        manager.add(ActionStep(observation="Obs3"))

        strategy = keep_last_n_steps(1)
        manager.prune(strategy)

        # Should have System + Task + last 1 action
        assert len(manager.steps) == 3

        system_steps = manager.get_steps_by_type(SystemPromptStep)
        task_steps = manager.get_steps_by_type(TaskStep)
        action_steps = manager.get_steps_by_type(ActionStep)

        assert len(system_steps) == 1
        assert len(task_steps) == 1
        assert len(action_steps) == 1
        assert action_steps[0].observation == "Obs3"  # Last action preserved

    def test_keep_last_n_with_n_equals_zero(self) -> None:
        """keep_last_n_steps(0) should remove all action steps."""
        manager = MemoryManager()

        manager.add(SystemPromptStep(content="System"))
        manager.add(TaskStep(task="Task"))
        manager.add(ActionStep(observation="Obs1"))
        manager.add(ActionStep(observation="Obs2"))

        strategy = keep_last_n_steps(0)
        manager.prune(strategy)

        assert len(manager.steps) == 2  # Only System + Task
        assert manager.action_count == 0

    def test_keep_last_n_preserves_all_when_n_large(self) -> None:
        """keep_last_n_steps(n) with large n should preserve all steps."""
        manager = MemoryManager()

        manager.add(SystemPromptStep(content="System"))
        manager.add(TaskStep(task="Task"))
        manager.add(ActionStep(observation="Obs1"))
        manager.add(ActionStep(observation="Obs2"))

        strategy = keep_last_n_steps(100)
        manager.prune(strategy)

        assert len(manager.steps) == 4  # All preserved
        assert manager.action_count == 2

    def test_keep_last_n_maintains_order(self) -> None:
        """keep_last_n_steps should maintain step order after pruning."""
        manager = MemoryManager()

        manager.add(SystemPromptStep(content="System"))
        manager.add(TaskStep(task="Task"))
        manager.add(ActionStep(observation="Obs1"))
        manager.add(ActionStep(observation="Obs2"))
        manager.add(ActionStep(observation="Obs3"))

        strategy = keep_last_n_steps(2)
        manager.prune(strategy)

        # Order should be: System, Task, Obs2, Obs3
        assert isinstance(manager.steps[0], SystemPromptStep)
        assert isinstance(manager.steps[1], TaskStep)
        assert isinstance(manager.steps[2], ActionStep)
        assert manager.steps[2].observation == "Obs2"
        assert isinstance(manager.steps[3], ActionStep)
        assert manager.steps[3].observation == "Obs3"


class TestPruneOldObservations:
    """Test prune_old_observations pruning strategy."""

    def test_prune_old_observations_truncates_old_steps(self) -> None:
        """prune_old_observations should truncate observations in old steps."""
        manager = MemoryManager()

        manager.add(SystemPromptStep(content="System"))
        manager.add(TaskStep(task="Task"))
        manager.add(ActionStep(observation="x" * 500))  # Old - will be truncated
        manager.add(ActionStep(observation="y" * 500))  # Old - will be truncated
        manager.add(ActionStep(observation="z" * 500))  # New - preserved

        strategy = prune_old_observations(keep_last_n=1, max_length=50)
        manager.prune(strategy)

        actions = manager.get_steps_by_type(ActionStep)

        # Old steps truncated
        assert len(actions[0].observation) == 53  # 50 + "..."
        assert len(actions[1].observation) == 53  # 50 + "..."
        # Last step preserved
        assert len(actions[2].observation) == 500

    def test_prune_old_observations_preserves_recent_steps(self) -> None:
        """prune_old_observations should preserve observations in recent steps."""
        manager = MemoryManager()

        manager.add(ActionStep(observation="x" * 200))
        manager.add(ActionStep(observation="y" * 200))
        manager.add(ActionStep(observation="z" * 200))

        strategy = prune_old_observations(keep_last_n=2, max_length=50)
        manager.prune(strategy)

        actions = manager.get_steps_by_type(ActionStep)

        # First step truncated
        assert len(actions[0].observation) == 53
        # Last 2 preserved
        assert len(actions[1].observation) == 200
        assert len(actions[2].observation) == 200

    def test_prune_old_observations_no_action_steps(self) -> None:
        """prune_old_observations should handle empty action steps gracefully."""
        manager = MemoryManager()

        manager.add(SystemPromptStep(content="System"))
        manager.add(TaskStep(task="Task"))

        strategy = prune_old_observations(keep_last_n=1, max_length=50)
        manager.prune(strategy)  # Should not raise

        assert len(manager.steps) == 2


class TestNoPruning:
    """Test no_pruning strategy."""

    def test_no_pruning_identity(self) -> None:
        """no_pruning should return steps unchanged (identity function)."""
        manager = MemoryManager()

        manager.add(SystemPromptStep(content="System"))
        manager.add(TaskStep(task="Task"))
        manager.add(ActionStep(observation="x" * 1000))
        manager.add(ActionStep(observation="y" * 1000))

        original_len = len(manager.steps)
        original_obs_lens = [
            s.observation if isinstance(s, ActionStep) else None for s in manager.steps
        ]

        strategy = no_pruning()
        manager.prune(strategy)

        assert len(manager.steps) == original_len
        for i, step in enumerate(manager.steps):
            if isinstance(step, ActionStep):
                assert len(step.observation) == len(original_obs_lens[i])


class TestMemoryManagerIntegration:
    """Integration tests for full workflow with MemoryManager."""

    def test_full_conversation_workflow(self) -> None:
        """Test a complete conversation workflow with memory."""
        manager = MemoryManager()

        # Initialize conversation
        manager.add(SystemPromptStep(content="You are a calculator assistant."))
        manager.add(TaskStep(task="Calculate 2 + 2"))

        # Simulate agent steps
        manager.add(
            ActionStep(
                thought="I need to calculate this",
                tool_name="calculator",
                tool_args={"expression": "2+2"},
                observation="4",
                raw_llm_response='{"tool": "calculator", "arguments": {"expression": "2+2"}}',
            )
        )

        manager.add(
            ActionStep(
                thought="I have the answer",
                is_final=True,
                observation="The result is 4",
                raw_llm_response='{"answer": "The result is 4"}',
            )
        )

        # Verify state
        assert manager.action_count == 2
        messages = manager.to_messages()
        assert len(messages) == 6  # system + user + 2*(assistant + user)

        # Verify message order
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"
        assert messages[3]["role"] == "user"

    def test_workflow_with_pruning(self) -> None:
        """Test conversation workflow with pruning applied."""
        manager = MemoryManager()

        manager.add(SystemPromptStep(content="System"))
        manager.add(TaskStep(task="Task"))

        # Add many action steps
        for i in range(10):
            manager.add(ActionStep(observation=f"Observation {i}" * 100))

        assert manager.action_count == 10

        # Apply pruning
        strategy = keep_last_n_steps(3)
        manager.prune(strategy)

        assert manager.action_count == 3

        # Verify preserved steps are the last 3
        actions = manager.get_steps_by_type(ActionStep)
        assert "Observation 7" in actions[0].observation
        assert "Observation 8" in actions[1].observation
        assert "Observation 9" in actions[2].observation


class TestPruningContrastive:
    """Contrastive tests comparing pruned vs unpruned states."""

    def test_pruned_vs_unpruned_step_count(self) -> None:
        """Compare step counts between pruned and unpruned memory."""

        def create_manager() -> MemoryManager:
            manager = MemoryManager()
            manager.add(SystemPromptStep(content="System"))
            manager.add(TaskStep(task="Task"))
            for i in range(5):
                manager.add(ActionStep(observation=f"Obs{i}"))
            return manager

        # Unpruned
        unpruned = create_manager()
        assert len(unpruned.steps) == 7

        # Pruned
        pruned = create_manager()
        pruned.prune(keep_last_n_steps(2))
        assert len(pruned.steps) == 4  # System + Task + 2 actions

        # Verify difference
        assert len(unpruned.steps) > len(pruned.steps)

    def test_pruned_vs_unpruned_observation_length(self) -> None:
        """Compare observation lengths between pruned and unpruned memory."""
        long_obs = "x" * 1000

        def create_manager() -> MemoryManager:
            manager = MemoryManager()
            manager.add(ActionStep(observation=long_obs))
            manager.add(ActionStep(observation=long_obs))
            return manager

        # Unpruned
        unpruned = create_manager()
        unpruned_actions = unpruned.get_steps_by_type(ActionStep)
        assert len(unpruned_actions[0].observation) == 1000

        # Pruned
        pruned = create_manager()
        pruned.prune(prune_old_observations(keep_last_n=1, max_length=100))
        pruned_actions = pruned.get_steps_by_type(ActionStep)
        assert len(pruned_actions[0].observation) == 103  # Truncated

        # Verify last step preserved in both
        assert len(unpruned_actions[1].observation) == 1000
        assert len(pruned_actions[1].observation) == 1000
