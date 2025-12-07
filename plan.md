# ASCII Logger Redesign Plan

## Problem
Built pyTermTk TUI dashboard (WRONG). User wants StarCraft-style ASCII text output from AgentLogger._panel() and _channel() methods only.

## Solution
1. **CLEANUP** - Delete all pyTermTk files
2. **RESTORE** - AgentLogger to simple ASCII output
3. **REDESIGN** - _panel() and _channel() with StarCraft UI principles

## StarCraft UI Principles
- Dense information (max data per line)
- Spatial consistency (same position, same info)
- Clear hierarchy (important stuff stands out)
- Strong icons (▶ @ ✓ ! for states)

## New ASCII Format

### Current _panel():
```
+========================+
| << TITLE >>             |
+------------------------+
| content                 |
+========================+
```

### New _panel():
```
╔════════════════════════════════════════════════════════════════════════════════╗
║ ▶ COMMAND CENTER // TITLE                                                     ║
╠════════════════════════════════════════════════════════════════════════════════╣
║ • STATUS: ████████░░ 80%    • ELAPSED: 00:12    • CYCLE: 3/10                ║
╚════════════════════════════════════════════════════════════════════════════════╝
```

### Current _channel():
```
[   API   ] >> message
```

### New _channel():
```
[▶   API   ] Calling gpt-4o-mini (temp=0.7)...
[@  EXEC   ] ddgs_search(query='ReAct pattern')
[✓ RESULT  ] Found 5 results
[!  ERROR  ] Search timeout
```

## Files to DELETE
- `tinyagent/observability/dashboard.py`
- `tinyagent/observability/termtk_dashboard.py`
- `examples/termtk_logger_demo.py`

## Files to MODIFY
- `tinyagent/observability/logger.py` - remove dashboard params, redesign _panel/_channel
- `tinyagent/observability/__init__.py` - revert to simple exports
- `tests/test_logger.py` - update test expectations

## Steps
1. Delete broken pyTermTk files
2. Clean AgentLogger (remove dashboard code)
3. Redesign _panel() with box-drawing chars
4. Redesign _channel() with arrow icons
5. Update tests
6. Test with examples

## Success
✅ Clean codebase (no pyTermTk)
✅ StarCraft-style ASCII output
✅ All tests pass
