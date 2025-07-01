# Memory Anchors Registry

## Purpose
This file maintains a registry of memory anchors used throughout the codebase for precise reference by Claude instances.

## Anchor Format
`CLAUDE-ANCHOR-[UUID]-[SEMANTIC-TAG]`

## Active Anchors

### Core System Anchors
- `CLAUDE-ANCHOR-a1b2c3d4-MAIN-ENTRY`: Main application entry point (src/index.ts:1)
- `CLAUDE-ANCHOR-e5f6g7h8-ERROR-HANDLER`: Global error handler (src/errors/handler.ts:15)
- `CLAUDE-ANCHOR-i9j0k1l2-CONFIG-LOADER`: Configuration loading logic (src/config/loader.ts:42)

### Critical Functions
- `CLAUDE-ANCHOR-m3n4o5p6-AUTH-CHECK`: Authentication verification (src/auth/verify.ts:78)
- `CLAUDE-ANCHOR-q7r8s9t0-DATA-VALIDATE`: Data validation pipeline (src/validate/pipeline.ts:23)

### Known Problem Areas
- `CLAUDE-ANCHOR-u1v2w3x4-MEMORY-LEAK`: Potential memory leak location (src/cache/manager.ts:156)
- `CLAUDE-ANCHOR-y5z6a7b8-RACE-CONDITION`: Race condition in async handler (src/async/handler.ts:89)

## Usage
Reference these anchors in queries like:
"Check the error handling at CLAUDE-ANCHOR-e5f6g7h8-ERROR-HANDLER"

## Maintenance
- Add new anchors when identifying critical code sections
- Remove obsolete anchors during refactoring
- Update line numbers when code moves
