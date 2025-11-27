# Tool System Architecture Issues

## 1. Global Mutable Singleton (High Impact)

**Location:** `tinyagent/core/registry.py:110`

The `REGISTRY = ToolRegistry()` is module-level global state mutated by every `@tool` decorator.

**Problems:**
- Test isolation breaks - decorated tools persist across test runs
- Import order determines registration order
- No way to scope tools to specific agents or contexts
- Hidden side effects from imports

**Pattern:** Consider dependency injection or registry-per-agent.

---

## 2. Duplicated Tool Resolution Logic (Medium Impact)

**Locations:**
- `tinyagent/agents/react.py:67-79`
- `tinyagent/agents/code.py:123-132`

Both agents have copy-pasted logic for building `_tool_map` from mixed `Tool` objects and decorated functions.

**Problems:**
- Violates DRY - changes require updating both locations
- Inconsistency risk if one is modified without the other
- Logic spread across files instead of centralized

**Pattern:** Extract to shared utility or base class method.

---

## 3. Name Collision Without Warning (Medium Impact)

**Location:** `tinyagent/core/registry.py:69`

Tools are keyed solely by `fn.__name__`. Two functions with identical names silently overwrite each other.

```python
# module_a.py
@tool
def search(): ...

# module_b.py
@tool
def search(): ...  # Silently overwrites module_a.search
```

**Problems:**
- Silent data loss - no error or warning
- Debugging nightmare when wrong tool executes
- No namespace isolation

**Pattern:** Use qualified names (`module.function`) or raise on collision.
