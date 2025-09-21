
###Instruction###
Your task is to optimize and extend this repository following explicit coding, testing, and documentation workflows.

Example of ReAct loop:

Reason: I need to know if a golden baseline test exists for this feature.

Act: Search the tests/ directory for existing coverage.

You MUST comply with the rules below. You will be penalized if you deviate. Answer in a natural, human-like manner. you MUST keep.claude updated as instructed below. You will be punished for now keeping .claude kb in synch. You MUST always follow the ReAct Pattern (reasoning + acting) when solving tasks, explicitly alternating between reasoning steps and concrete actions.
---

### Workflow Rules
* Never begin coding until the objective is **explicitly defined**. If unclear, ask questions or use best practices.
* Always use `.venv` and `uv` for package management.
* Small, focused diffs only. Commit frequently.

### Code Style & Typing

* Enforce `ruff check --fix .` before PRs.
* Use explicit typing. `cast(...)` and `assert ...` are OK.
* `# type: ignore` only with strong justification.

### Error Handling

* Fail fast, fail loud. No silent fallbacks.
* Minimize branching: every `if`/`try` must be justified.

### Dependencies

* Avoid new core dependencies. Tiny deps OK if widely reused.

### Testing (TDD Red → Green → Blue)

1. If a test doesn’t exist, create a **golden baseline test first**.
2. Add a failing test for the new feature.
3. Implement until tests pass.
4. Refactor cleanly.

* Run with: `hatch run test`.

### Documentation

* Keep concise and actionable.
* Update when behavior changes.
* Avoid duplication.

### Scope & Maintenance

* Backward compatibility only if low maintenance cost.
* Delete dead code (never guard it).
* Always run `ruff .`.
* Use `git commit -n` if pre-commit hooks block rollback.
