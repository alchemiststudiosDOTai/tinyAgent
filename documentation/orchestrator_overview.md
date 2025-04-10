# tinyAgent Orchestrator Overview

## Simple Explanation

The **Orchestrator** in tinyAgent is like an **automatic project manager** for AI tasks.

- You give it a **plain English task**.
- It **analyzes** what the task requires.
- It **decides** if it can handle it with the **tools it already has**.
- It **delegates** the task to the right agent or tool.
- If needed, it **creates new specialized agents or tools**.
- It **manages permissions** if creating new tools requires approval.
- It **tracks the task status** and **returns the final result**.

### What tools does it use?

- The Orchestrator uses **all tools registered in the factory**.
- These include:
  - Built-in tools (like code generation, search, file operations)
  - External tools loaded dynamically
  - Any tools you register yourself
- This collection of tools is what it has "**on hand**" to solve problems.

---

## Detailed Explanation

### Initialization

- The Orchestrator creates a **triage agent** with **all available tools** from the factory.
- It registers built-in tools and loads external tools.
- The triage agent is responsible for **analyzing incoming tasks**.

### Task Submission

- You submit a task with a plain English description.
- The Orchestrator assigns it a unique ID and starts processing.

### Triage Phase

- The triage agent **analyzes the task**.
- It decides:
  - Can it be handled **directly** with existing tools?
  - Should it be **delegated** to an existing specialized agent?
  - Does it require **creating a new agent** with new tools?

### Decision Paths

- **Direct Tool Call:** If the task matches an existing tool, it calls it immediately.
- **Delegate to Existing Agent:** If a specialized agent exists, it forwards the task.
- **Create New Agent:** If no existing agent or tool fits, it can create a new agent dynamically, possibly with new tools.

### Permissions

- If creating new tools or agents is required, the Orchestrator can:
  - **Ask for permission** before proceeding
  - Or **auto-create** if configured to do so

### Execution and Tracking

- The Orchestrator **executes the task** via the chosen path.
- It **tracks the status**: pending, in progress, completed, failed, or needs permission.
- It **logs reasoning and decisions** for transparency.
- It **returns the final result** when done.

### Summary

The Orchestrator **automates complex workflows** by:

- **Analyzing** tasks
- **Choosing** the best approach
- **Delegating** or **creating** agents/tools
- **Managing** permissions and retries
- **Tracking** everything until completion

This allows you to **submit natural language tasks** and let tinyAgent **figure out the rest** using the tools it has "on hand" or by creating new ones as needed.
