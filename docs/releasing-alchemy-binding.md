# Shipping the `tinyagent._alchemy` Binding in Release Wheels

This document captures the release task we completed to make `tiny-agent-os`
ship the prebuilt `tinyagent._alchemy` binary again when a release wheel is
built.

## Goal

Ship the alchemy-backed runtime path in published wheels by building the Rust
binding from the in-repo `rust/` crate in CI, staging the resulting
`tinyagent._alchemy` extension into `tinyagent/`, and packaging that binary into
platform wheels.

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
  - rejects staged binaries whose file format does not match the current host
    platform (for example, ELF on macOS)
- `scripts/check_release_wheels.py`
  - rejects generic `linux_*` wheel tags that PyPI will not accept for Linux uploads
- `scripts/stage_release_binding.py` (legacy)
  - stages `_alchemy...` from a built wheel by basename
  - not used by the current in-repo binding release path
- `tests/test_release_binding.py`
  - regression tests for the release check
- `tests/test_release_wheels.py`
  - regression tests for Linux wheel tag validation
- `scripts/build_release_debug_artifact.py`
  - captures wheel metadata, staged-binding state, and file listings into a `.artifact` debug bundle
- `tests/test_release_debug_artifact.py`
  - regression tests for the release debug bundle contents
- `tests/test_stage_release_binding.py`
  - regression tests for wheel extraction/staging behavior
- `AGENTS.md`
  - documents the release command and staging requirement
- `HARNESS.md`
  - records the release gate for wheels expected to ship `_alchemy`
- `.github/workflows/publish-pypi.yml`
  - builds Linux (manylinux), macOS, and Windows release wheels from the in-repo binding
  - repairs Linux wheels into PyPI-acceptable `manylinux` artifacts before upload
  - smoke-tests each built wheel in a clean virtualenv before publishing
  - publishes the built distributions to PyPI with the repo `PYPI_TOKEN` secret

## Release workflow

### 1. Build the binding from this repo

Build the Rust binding from `rust/` and stage it into `tinyagent/`. Expected
staged filenames include one of:

- `tinyagent/_alchemy.abi3.so`
- `tinyagent/_alchemy.<platform>.so`
- `tinyagent/_alchemy.pyd`
- `tinyagent/_alchemy.dylib`

Platform examples:

- Linux: `cp rust/target/release/lib_alchemy.so tinyagent/_alchemy.abi3.so`
- macOS: `cp rust/target/release/lib_alchemy.dylib tinyagent/_alchemy.abi3.so`
- Windows: copy the built `*alchemy*.dll` to `tinyagent/_alchemy.pyd`

### 2. Stage the artifact into this repo

The staged `_alchemy` binary must exist in `tinyagent/` before packaging so
setuptools includes it as package data.

### 3. Run the release check

```bash
python3 scripts/check_release_binding.py --require-present
```

This must pass before building/publishing wheels that are expected to ship the
binding.

Run it on the same platform family you are about to publish for. A passing check
now means the staged artifact both exists and has the expected host binary
format.

## 4. Build the wheel

Use:

```bash
uv build --wheel
```

Because the staged binary is present, the produced wheel should be
platform-specific.

Example pre-repair Linux wheel output from this task:

- `tiny_agent_os-1.2.16-cp310-abi3-linux_x86_64.whl`

## 5. Repair Linux wheels for PyPI

On Linux, `uv build --wheel` still emits a generic `linux_x86_64` wheel tag. PyPI
expects a `manylinux_*` or `musllinux_*` Linux tag instead, so repair the built
wheel before publishing:

```bash
mkdir -p wheelhouse
uv tool run auditwheel repair --wheel-dir wheelhouse dist/*.whl
rm dist/*.whl
mv wheelhouse/*.whl dist/
python3 scripts/check_release_wheels.py dist
```

macOS and Windows wheels do not need this step.

Example repaired Linux wheel output from this task:

- `tiny_agent_os-1.2.16-cp310-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

## 6. Verify wheel contents

Confirm the built wheel contains the binding artifact:

- `tinyagent/_alchemy.abi3.so`

The wheel build output from this task showed:

- `adding 'tinyagent/_alchemy.abi3.so'`

## 7. Publish the wheel

After verification, publish the built wheel(s) as the release artifacts.

## Automated Linux + macOS + Windows release path

This repo now includes `.github/workflows/publish-pypi.yml`.

On GitHub release publish or manual dispatch, it:

- checks out this repo
- builds the in-repo binding on `ubuntu-latest` (manylinux), `macos-latest`, and `windows-latest`
- stages the binding into `tinyagent/`
- runs `python3 scripts/check_release_binding.py --require-present`
- builds the `tiny-agent-os` wheel
- repairs Linux wheels with `auditwheel repair`
- runs `python3 scripts/check_release_wheels.py dist`
- installs that wheel into a fresh virtualenv and smoke-tests `import tinyagent._alchemy`
- uploads the resulting wheels as artifacts
- publishes them to PyPI using the repo `PYPI_TOKEN` secret

That automation is the supported path for getting Linux, macOS, and Windows
wheels from the correct native binding, instead of relying on whatever
`_alchemy` file happened to be present in a local checkout.

## PyPI setup required once

Store a PyPI API token for the `tiny-agent-os` project in this repository as:

- repository secret: `PYPI_TOKEN`

The workflow publishes with:

- username: `__token__`
- password: `${{ secrets.PYPI_TOKEN }}`

After that one-time setup, publishing a GitHub release will build Linux, macOS,
and Windows wheels, then upload the artifacts to PyPI under the same release
version.

## Why this approach

This keeps the release contract simple:

- binding implementation lives in this repo under `rust/`
- CI builds the native `_alchemy` binary per platform
- published wheels include the binding so users do not need Rust to install

## Operational notes

- If no staged `_alchemy` binary exists, the package can still build as a pure
  Python distribution.
- If a staged `_alchemy` binary exists, `setup.py` ensures the wheel is treated
  as platform-specific.
- The release check is the explicit safeguard that prevents publishing a wheel
  meant to include alchemy without the actual binary.
- The release check also catches obvious staging mistakes such as copying a
  Linux ELF artifact into a macOS wheel build.
- The release wheel check blocks generic `linux_*` tags, which PyPI does not
  accept for Linux uploads.
- The debug artifact is uploaded even for failed platform jobs so wheel metadata
  and staging state can be inspected without re-running locally.

## Commands added for this workflow

- `python3 scripts/check_release_binding.py`
- `python3 scripts/check_release_binding.py --require-present`
- `python3 scripts/check_release_wheels.py dist`
- `python3 scripts/build_release_debug_artifact.py --output-dir .artifact/release-debug`
- `uv build --wheel`

## Files involved

- `pyproject.toml`
- `setup.py`
- `scripts/check_release_binding.py`
- `scripts/check_release_wheels.py`
- `scripts/build_release_debug_artifact.py`
- `tests/test_release_binding.py`
- `tests/test_release_wheels.py`
- `tests/test_release_debug_artifact.py`
- `AGENTS.md`
- `HARNESS.md`
- `CHANGELOG.md`

## Summary

The release contract is now:

1. build `_alchemy` from the external binding repo
2. copy it into `tinyagent/`
3. run `python3 scripts/check_release_binding.py --require-present`
4. build the wheel with `uv build --wheel`
5. on Linux, repair the wheel with `auditwheel` and run `python3 scripts/check_release_wheels.py dist`
6. verify the wheel contains `tinyagent/_alchemy...`
7. publish
