# Directory Organization Plan

## Current State Analysis

The tinyAgent directory has grown complex with 103 files and 29 directories. Several organizational issues identified:

### Problems to Address
1. **Root level clutter**: Files like `=0.13.1`, `=2.31.0`, `.DS_Store`, log files
2. **Mixed documentation**: Some docs in root (`plan.md`, `code_review_analysis.md`), some in `documentation/`
3. **Build artifacts**: `tiny_agent_os.egg-info/` should be managed properly
4. **Memory bank**: Large `memory-bank/` folder with dated execution logs
5. **Inconsistent structure**: No clear separation between code, docs, and temporary files

## Target Structure

```
tinyAgent/
├── tinyagent/                    # Main Python package (well-organized)
├── documentation/               # Consolidated documentation
│   ├── architecture/
│   ├── providers/
│   ├── guides/
│   └── archive/                 # Old planning docs
├── examples/                    # Clean demo scripts
├── tests/                       # Test suite
├── scripts/                     # Utility and deployment scripts
├── static/                      # Static assets
├── .memory-archive/            # Archived memory-bank (optional)
├── pyproject.toml              # Package configuration
├── README.md                   # Main project README
├── CONTRIBUTING.md             # Contributing guidelines
├── .gitignore                  # Proper ignore patterns
└── (root should otherwise be clean)
```

## Action Plan

### Phase 1: Root Level Cleanup
1. **Remove junk files**:
   - Delete `=0.13.1`, `=2.31.0`, `tunacode.log`
   - Update `.gitignore` to prevent future accumulation

2. **Move documentation to proper location**:
   - `plan.md` → `documentation/archive/old_plans.md`
   - `code_review_analysis.md` → `documentation/reviews/`
   - `CLAUDE.md` → `documentation/guides/claude_usage.md`
   - `AGENTS.md` → `documentation/guides/agent_guide.md`

### Phase 2: Build Management
3. **Clean build artifacts**:
   - Add `tiny_agent_os.egg-info/` to `.gitignore`
   - Consider removing existing egg-info directory
   - Ensure `pyproject.toml` has proper build configuration

### Phase 3: Memory Organization
4. **Handle memory-bank**:
   - Option A: Move to `.memory-archive/` for historical reference
   - Option B: Extract valuable patterns and delete the rest
   - Option C: Keep as is if actively used

### Phase 4: Documentation Consolidation
5. **Restructure documentation**:
   - Create `documentation/guides/` for how-to content
   - Create `documentation/archive/` for old planning documents
   - Update `documentation/CONTRIBUTING.md` to reflect new structure

### Phase 5: Examples and Scripts Cleanup
6. **Review examples**:
   - Consolidate similar demo scripts
   - Add documentation headers to examples
   - Ensure all examples work with current structure

7. **Script organization**:
   - Keep deployment scripts in `scripts/`
   - Add script documentation
   - Remove unused scripts

## Files to Create/Modify

### New Files
- `documentation/guides/claude_usage.md`
- `documentation/guides/agent_guide.md`
- `documentation/archive/README.md`
- `.memory-archive/README.md` (if keeping memory bank)
- Updated `.gitignore`

### Files to Modify
- `README.md` (update to reflect new structure)
- `documentation/CONTRIBUTING.md`
- `pyproject.toml` (if needed)

## Success Criteria
✅ Root directory contains only essential files
✅ All documentation organized in logical folders
✅ Build artifacts properly ignored
✅ Memory bank organized or archived
✅ Clear distinction between code, docs, and temporary files
✅ Updated documentation reflects new structure

## Decision Points
1. **Memory bank fate**: Archive vs delete vs keep
2. **Historical documents**: Keep vs extract vs discard
3. Examples cleanup level: Minimal vs comprehensive

## Next Steps
1. Get approval on memory bank handling
2. Execute Phase 1 (immediate cleanup)
3. Review and adjust based on findings
4. Complete remaining phases