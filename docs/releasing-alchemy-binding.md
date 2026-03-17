# Shipping the `tinyagent._alchemy` Binding in Release Wheels

This document captures the release task we completed to make `tiny-agent-os`
ship the prebuilt `tinyagent._alchemy` binary again when a release wheel is
built.

## Goal

Restore the alchemy-backed runtime path in published wheels without moving the
binding source code back into this repository.

The binding source of truth remains external:

- `https://github.com/tunahorse/tinyagent-alchemy`

This repo now supports **staging a prebuilt binding artifact into `tinyagent/`**
before packaging so the final wheel includes it.

## What changed

### Packaging

- `pyproject.toml`
  - setuptools package data now includes:
    - `_alchemy*.so`
    - `_alchemy*.pyd`
    - `_alchemy*.dylib`
- `setup.py`
  - adds a custom setuptools `Distribution`
  - when a staged `_alchemy` binary exists in `tinyagent/`, wheel builds are
    marked as platform-specific instead of pure-Python

### Release enforcement

- `scripts/check_release_binding.py`
  - validates that package-data is configured to include `_alchemy`
  - can require that a staged binary is actually present
- `tests/test_release_binding.py`
  - regression tests for the release check
- `AGENTS.md`
  - documents the release command and staging requirement
- `HARNESS.md`
  - records the release gate for wheels expected to ship `_alchemy`

## Release workflow

### 1. Build the binding from the external repo

Build the correct prebuilt artifact from:

- `https://github.com/tunahorse/tinyagent-alchemy`

Expected staged filenames include one of:

- `tinyagent/_alchemy.abi3.so`
- `tinyagent/_alchemy.<platform>.so`
- `tinyagent/_alchemy.pyd`
- `tinyagent/_alchemy.dylib`

### 2. Stage the artifact into this repo

Copy the built binary into:

- `tinyagent/`

Example:

```bash
cp /path/to/built/_alchemy.abi3.so tinyagent/
```

### 3. Run the release check

```bash
python3 scripts/check_release_binding.py --require-present
```

This must pass before building/publishing wheels that are expected to ship the
binding.

## 4. Build the wheel

Use:

```bash
uv build --wheel
```

Because the staged binary is present, the produced wheel should be
platform-specific.

Example verified output from this task:

- `tiny_agent_os-1.2.9-cp310-cp310-linux_x86_64.whl`

## 5. Verify wheel contents

Confirm the built wheel contains the binding artifact:

- `tinyagent/_alchemy.abi3.so`

The `uv build` output from this task showed:

- `adding 'tinyagent/_alchemy.abi3.so'`

## 6. Publish the wheel

After verification, publish the built wheel(s) as the release artifacts.

## Why this approach

This keeps the repository split clean:

- binding implementation lives in the external binding repo
- TinyAgent release wheels can still ship the prebuilt runtime dependency
- downstream users get a working alchemy-backed install from the wheel again

## Operational notes

- If no staged `_alchemy` binary exists, the package can still build as a pure
  Python distribution.
- If a staged `_alchemy` binary exists, `setup.py` ensures the wheel is treated
  as platform-specific.
- The release check is the explicit safeguard that prevents publishing a wheel
  meant to include alchemy without the actual binary.

## Commands added for this workflow

- `python3 scripts/check_release_binding.py`
- `python3 scripts/check_release_binding.py --require-present`
- `uv build --wheel`

## Files involved

- `pyproject.toml`
- `setup.py`
- `scripts/check_release_binding.py`
- `tests/test_release_binding.py`
- `AGENTS.md`
- `HARNESS.md`
- `CHANGELOG.md`

## Summary

The release contract is now:

1. build `_alchemy` from the external binding repo
2. copy it into `tinyagent/`
3. run `python3 scripts/check_release_binding.py --require-present`
4. build the wheel with `uv build --wheel`
5. verify the wheel contains `tinyagent/_alchemy...`
6. publish
