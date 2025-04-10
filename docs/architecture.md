# tinyAgent System Architecture

## 1. Core Philosophy

The architectural design of tinyAgent is guided by the following principles:

1.  **Functions as Agents:** Core functionalities are encapsulated within distinct agent components. This promotes modularity and reusability.

2.  **Hierarchical Orchestra of Specialized Agents:** Agents can be organized hierarchically. Higher-level agents (like an Orchestrator) can manage and coordinate the workflows of more specialized, lower-level agents, allowing for complex task decomposition.

3.  **Dynamic Capability Creation:** The framework supports the on-the-fly creation of agents and their capabilities, particularly through the `DynamicAgentFactory`. This allows the system to adapt to evolving task requirements without predefined structures for every possible scenario.

## 2. Key Components (Initial Overview)

- **Agents:** The primary units of execution. They manage state, interact with tools, and process information.
  - Types created via: `Orchestrator`, `AgentFactory`, `DynamicAgentFactory`.
- **Tools:** Discrete functions or modules (decorated with `@tool`) that agents can invoke to perform specific actions (e.g., file operations, API calls, code execution).
- **Factories (`AgentFactory`, `DynamicAgentFactory`):** Responsible for the instantiation and configuration of agents, potentially including dynamic tool loading.
- **Orchestrator:** A high-level agent type designed for simpler task management and workflow execution.
- **Configuration (`config.yml`):** Centralized settings for models, API keys, logging, etc.

_(Note: This is a high-level overview based on the initial README.md. It will be expanded as the system design is further detailed.)_
