#!/usr/bin/env python3
"""
Memory System Demo - MemoryManager with Pruning Strategies

Demonstrates the new structured memory system for tinyAgent:
- MemoryManager for storing conversation steps
- Step types: SystemPromptStep, TaskStep, ActionStep, ScratchpadStep
- Pruning strategies: keep_last_n_steps, prune_old_observations, no_pruning

This demo shows how to:
1. Use basic memory without pruning
2. Enable pruning to manage conversation length
3. Inspect memory contents using get_steps_by_type()
4. Access action_count property

Note: This demo uses mock LLM responses to avoid API calls.
"""

from tinyagent import (
    ActionStep,
    MemoryManager,
    ScratchpadStep,
    Step,
    SystemPromptStep,
    TaskStep,
    keep_last_n_steps,
    no_pruning,
    prune_old_observations,
)


def demo_basic_memory() -> None:
    """Demo 1: Basic memory usage without pruning."""
    print("=" * 60)
    print("Demo 1: Basic Memory Usage (No Pruning)")
    print("=" * 60)

    # Create a memory manager
    manager = MemoryManager()

    # Add initial conversation setup
    manager.add(SystemPromptStep(content="You are a helpful calculator assistant."))
    manager.add(TaskStep(task="Calculate 2 + 2, then multiply the result by 3."))

    # Simulate agent steps
    manager.add(
        ActionStep(
            thought="I need to first calculate 2 + 2",
            tool_name="calculator",
            tool_args={"expression": "2+2"},
            observation="4",
            raw_llm_response='{"tool": "calculator", "arguments": {"expression": "2+2"}}',
        )
    )

    manager.add(
        ActionStep(
            thought="Now I multiply 4 by 3",
            tool_name="calculator",
            tool_args={"expression": "4*3"},
            observation="12",
            raw_llm_response='{"tool": "calculator", "arguments": {"expression": "4*3"}}',
        )
    )

    manager.add(
        ActionStep(
            thought="I have the final answer",
            is_final=True,
            observation="The result is 12",
            raw_llm_response='{"answer": "The result is 12"}',
        )
    )

    # Display memory state
    print(f"\nTotal steps: {len(manager.steps)}")
    print(f"Action count: {manager.action_count}")

    # Show messages that would be sent to LLM
    messages = manager.to_messages()
    print(f"\nMessages for LLM ({len(messages)} total):")
    for i, msg in enumerate(messages):
        role = msg["role"]
        content = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
        print(f"  {i + 1}. [{role}] {content}")

    print()


def demo_keep_last_n_pruning() -> None:
    """Demo 2: Memory with keep_last_n_steps pruning."""
    print("=" * 60)
    print("Demo 2: Memory with keep_last_n_steps Pruning")
    print("=" * 60)

    manager = MemoryManager()

    # Add system and task (always preserved)
    manager.add(SystemPromptStep(content="You are a helpful assistant."))
    manager.add(TaskStep(task="Process a series of numbers."))

    # Add many action steps
    for i in range(10):
        manager.add(
            ActionStep(
                tool_name="process",
                tool_args={"n": i},
                observation=f"Processed number {i} with result {i * 2}",
                raw_llm_response=f'{{"tool": "process", "arguments": {{"n": {i}}}}}',
            )
        )

    print("\nBefore pruning:")
    print(f"  Total steps: {len(manager.steps)}")
    print(f"  Action count: {manager.action_count}")

    # Apply pruning - keep only last 3 action steps
    strategy = keep_last_n_steps(3)
    manager.prune(strategy)

    print("\nAfter pruning (keep_last_n_steps(3)):")
    print(f"  Total steps: {len(manager.steps)}")
    print(f"  Action count: {manager.action_count}")

    # Show which steps remain
    print("\n  Remaining step types:")
    print(f"    SystemPromptStep: {len(manager.get_steps_by_type(SystemPromptStep))}")
    print(f"    TaskStep: {len(manager.get_steps_by_type(TaskStep))}")
    print(f"    ActionStep: {len(manager.get_steps_by_type(ActionStep))}")

    # Show the preserved action steps
    actions = manager.get_steps_by_type(ActionStep)
    print("\n  Preserved actions (last 3):")
    for action in actions:
        obs = (
            action.observation[:40] + "..." if len(action.observation) > 40 else action.observation
        )
        print(f"    - {obs}")

    print()


def demo_prune_old_observations() -> None:
    """Demo 3: Memory with prune_old_observations strategy."""
    print("=" * 60)
    print("Demo 3: Memory with prune_old_observations Pruning")
    print("=" * 60)

    manager = MemoryManager()

    manager.add(SystemPromptStep(content="You are a data analyzer."))
    manager.add(TaskStep(task="Analyze multiple data sets."))

    # Add action steps with long observations
    for i in range(5):
        long_observation = f"Analysis result for dataset {i}: " + ("detailed data " * 50)
        manager.add(
            ActionStep(
                tool_name="analyze",
                tool_args={"dataset": i},
                observation=long_observation,
                raw_llm_response=f'{{"tool": "analyze", "arguments": {{"dataset": {i}}}}}',
            )
        )

    # Get observation lengths before pruning
    actions_before = manager.get_steps_by_type(ActionStep)
    print("\nBefore pruning:")
    print(f"  Action count: {len(actions_before)}")
    for i, action in enumerate(actions_before):
        print(f"  Step {i}: observation length = {len(action.observation)}")

    # Apply pruning - truncate observations in old steps
    strategy = prune_old_observations(keep_last_n=2, max_length=50)
    manager.prune(strategy)

    # Get observation lengths after pruning
    actions_after = manager.get_steps_by_type(ActionStep)
    print("\nAfter pruning (keep_last_n=2, max_length=50):")
    print(f"  Action count: {len(actions_after)}")
    for i, action in enumerate(actions_after):
        print(f"  Step {i}: observation length = {len(action.observation)}")

    print("\n  Old steps (0-2) have truncated observations")
    print("  Recent steps (3-4) preserve full observations")
    print()


def demo_inspect_memory() -> None:
    """Demo 4: Inspecting memory contents."""
    print("=" * 60)
    print("Demo 4: Inspecting Memory Contents")
    print("=" * 60)

    manager = MemoryManager()

    manager.add(SystemPromptStep(content="You are a helpful assistant."))
    manager.add(TaskStep(task="Help me with a task."))

    # Add a scratchpad note
    manager.add(
        ScratchpadStep(
            content="User seems to prefer concise answers",
            raw_llm_response='{"scratchpad": "User seems to prefer concise answers"}',
        )
    )

    manager.add(
        ActionStep(
            tool_name="helper",
            tool_args={"action": "assist"},
            observation="Task completed successfully",
            raw_llm_response='{"tool": "helper", "arguments": {"action": "assist"}}',
        )
    )

    # Inspect by type
    print("\nMemory inspection:")
    print(f"  Total steps: {len(manager.steps)}")

    system_steps = manager.get_steps_by_type(SystemPromptStep)
    task_steps = manager.get_steps_by_type(TaskStep)
    action_steps = manager.get_steps_by_type(ActionStep)
    scratchpad_steps = manager.get_steps_by_type(ScratchpadStep)

    print("\n  By type:")
    print(f"    SystemPromptStep: {len(system_steps)}")
    print(f"    TaskStep: {len(task_steps)}")
    print(f"    ActionStep: {len(action_steps)}")
    print(f"    ScratchpadStep: {len(scratchpad_steps)}")

    # Show scratchpad content
    if scratchpad_steps:
        print("\n  Scratchpad notes:")
        for sp in scratchpad_steps:
            print(f"    - {sp.content}")

    # Using base Step type gets all steps
    all_steps = manager.get_steps_by_type(Step)
    print(f"\n  All steps (via Step base class): {len(all_steps)}")

    # action_count property
    print(f"\n  action_count property: {manager.action_count}")

    print()


def demo_no_pruning() -> None:
    """Demo 5: Using no_pruning strategy (identity function)."""
    print("=" * 60)
    print("Demo 5: no_pruning Strategy (Identity)")
    print("=" * 60)

    manager = MemoryManager()

    manager.add(SystemPromptStep(content="System"))
    manager.add(TaskStep(task="Task"))

    for i in range(5):
        manager.add(ActionStep(observation=f"Observation {i}" * 20))

    print("\nBefore no_pruning:")
    print(f"  Total steps: {len(manager.steps)}")

    strategy = no_pruning()
    manager.prune(strategy)

    print("\nAfter no_pruning (should be unchanged):")
    print(f"  Total steps: {len(manager.steps)}")

    # Verify nothing changed
    actions = manager.get_steps_by_type(ActionStep)
    print("\n  All observations preserved:")
    for i, action in enumerate(actions):
        print(f"    Step {i}: length = {len(action.observation)}")

    print()


def main() -> None:
    """Run all memory demos."""
    print("\n")
    print("#" * 60)
    print("# TinyAgent Memory System Demo")
    print("#" * 60)
    print("\n")

    demo_basic_memory()
    demo_keep_last_n_pruning()
    demo_prune_old_observations()
    demo_inspect_memory()
    demo_no_pruning()

    print("=" * 60)
    print("All demos completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
