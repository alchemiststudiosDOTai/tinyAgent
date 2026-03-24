# PyPI Release Postmortem: Rust Binding Restoration

Date: 2026-03-24
Final successful release: `tiny-agent-os==1.2.26`
Successful workflow run: `23511702681`

## Summary

This incident covered the attempt to restore the in-repo Rust binding,
reintroduce `tinyagent._alchemy` into published wheels, and ship a clean PyPI
release for Linux, macOS, and Windows.

The work eventually succeeded in `1.2.26`, but only after a long sequence of
failed release attempts from `1.2.18` through `1.2.25`.

The important conclusion is:

- the typed Rust binding contract was not the main problem
- the primary failures were in release engineering, packaging, and CI workflow design
- the final blocking issue was building multiple `abi3` wheels with the same
  filename from a Python-version matrix, which made the publish payload
  nondeterministic and caused PyPI uploads to fail

## Impact

### User impact

- PyPI releases repeatedly failed for roughly a full workday
- multiple patch versions were cut without producing a complete usable release
- partial uploads to PyPI created confusion because some versions had only a
  subset of platform wheels
- package metadata on PyPI temporarily described the old external-binding model
  even after the binding had been restored in-repo

### Repository impact

- release workflow churn across many commits and tags
- repeated manual release attempts
- repeated CI runs consumed time without improving confidence until the failure
  pattern was isolated correctly

## What We Were Trying To Ship

The intended release contract was:

1. keep the Rust binding in this repo under `rust/`
2. build `tinyagent._alchemy` in GitHub Actions for Linux, macOS, and Windows
3. package that binding into the `tiny-agent-os` wheel
4. publish those wheels to PyPI so users do not need Rust installed locally

That contract is now what `1.2.26` ships.

## Timeline

### Initial restoration

The binding was brought back into this repo and wired into the published Python
package:

- in-repo Rust crate added under `rust/`
- Python-side typed adapter added
- release workflow changed to build platform wheels from this repo instead of
  relying on the historical external split

This part succeeded functionally. The release failures came afterward.

### `1.2.18` to `1.2.23`: Linux workflow instability

The first failure cluster was Linux CI instability, not binding correctness.

Observed problems across these attempts included:

- job-level container use with an older manylinux base that broke JavaScript
  GitHub Actions due to host/container glibc mismatch
- vendored OpenSSL builds that depended on toolchain pieces that were missing in
  the manylinux image
- shell quoting mistakes in inline Python
- heredoc indentation mistakes in inline Python

These failures were operational workflow failures. They did not indicate a bad
Rust contract.

### `1.2.24`: first all-platform build success, PyPI rejects Linux wheel

By `1.2.24`, Linux, macOS, and Windows all built successfully.

However, PyPI still rejected the publish step with `HTTP 400 Bad Request`.

Investigation showed the Linux wheel still bundled OpenSSL shared libraries:

- `libssl`
- `libcrypto`

That upload path was the remaining Linux-specific problem.

### `1.2.25`: Linux fixed, publish still fails on Windows

The next fix vendored `alchemy-llm` and patched its dependency chain to use
Rustls instead of native OpenSSL:

- `alchemy-llm` patched under `vendor/alchemy-llm/`
- `reqwest` switched to Rustls
- `jsonschema` default features disabled to stop dragging in unwanted HTTP/TLS
  behavior

This removed the Linux OpenSSL baggage and fixed Linux publishing.

At that point:

- macOS uploaded
- Linux uploaded
- Windows still failed with `HTTP 400 Bad Request`

This was the critical turning point, because it proved the remaining problem was
not Linux and was no longer OpenSSL.

### `1.2.25` root cause discovery

The publish workflow was still building three wheels per platform from a Python
matrix:

- Python `3.10`
- Python `3.11`
- Python `3.12`

But the binding was built as `abi3`, so all three jobs emitted the same wheel
filename per platform:

- `cp310-abi3-manylinux_...`
- `cp310-abi3-macosx_...`
- `cp310-abi3-win_amd64`

That meant the matrix was producing multiple different binaries under the same
artifact filename.

This was worst on Windows:

- all three Windows jobs produced `tiny_agent_os-1.2.25-cp310-abi3-win_amd64.whl`
- the wheel file hashes differed
- the `_alchemy.pyd` binary hashes differed

So the publish job was not receiving one canonical Windows wheel. It was
receiving whichever same-named file survived artifact merging.

PyPI only returned a generic `400`, so the exact PyPI-side validation message
was not visible in the action log. However, after isolating this duplicate-name
pattern and removing it, the next release succeeded immediately. That makes the
duplicate `abi3` matrix build the practical root cause of the final blocker.

### `1.2.26`: successful release

The final fix set was:

- build exactly one wheel per platform
- use Python `3.10` once per platform because `abi3` only needs one build
- remove the redundant Python-version matrix from Linux, macOS, and Windows
- add a publish-payload check that asserts exactly three wheels exist before
  upload
- set `skip-existing: true` so a partial upload does not block a retry
- update package metadata and docs to describe the in-repo binding correctly

After that, the release succeeded:

- Linux wheel published
- macOS wheel published
- Windows wheel published

## Root Causes

### 1. `abi3` was treated like an interpreter-specific wheel

This was the most important design mistake.

`abi3` means one wheel can target multiple Python versions. The workflow still
used Python-version matrices as if each interpreter needed its own distinct
wheel artifact.

That produced duplicate filenames with different payloads.

### 2. Release logic was too fragile and too inline

Early versions of the workflow relied on inline shell and inline Python in
places where quoting and heredoc formatting mattered.

That created avoidable failures unrelated to the binding itself.

### 3. The native TLS/OpenSSL dependency chain was not controlled tightly enough

The initial Rust dependency graph pulled in native TLS behavior on Linux, which
complicated manylinux builds and produced unwanted wheel contents.

That path had to be removed before Linux uploads became acceptable.

### 4. Documentation and package metadata lagged the implementation

Even after the binding was restored in-repo, README-derived package metadata
still described an external binding flow.

This did not break the wheels, but it created confusion at exactly the moment
the release process was already unstable.

## Contributing Factors

### Partial PyPI uploads hid the true state

Some failed releases uploaded one or two wheels before failing on the next one.
That made it look like the release was "almost done" while still leaving the
version incomplete.

### PyPI publish logs were too coarse

`gh-action-pypi-publish` surfaced a generic `HTTP 400 Bad Request` without the
deeper rejection reason in the workflow output.

That slowed root-cause isolation significantly.

### Every retry required a new version

Once a partial release hit PyPI, the clean retry path was another patch release.
That amplified the cost of each mistaken assumption.

### Too many issues were initially grouped together

The problem space included:

- Rust binding restoration
- provider contract validation
- Linux toolchain differences
- wheel tagging
- PyPI upload behavior
- docs and metadata drift

The binding itself worked earlier than the release process did, but those
threads were initially entangled.

## What Went Well

- The Rust binding contract itself held up under direct testing.
- Linux/macOS/Windows wheel builds were eventually stabilized.
- The Rustls patch removed native OpenSSL baggage cleanly.
- Artifact inspection and hash comparison eventually exposed the duplicate-wheel
  issue clearly.
- Once the workflow was simplified to one `abi3` build per platform, the next
  release succeeded immediately.

## What Went Poorly

- Too many release retries were made before reducing the problem to a smaller
  set of falsifiable hypotheses.
- Inline scripting was allowed to stay in the critical path too long.
- README-derived PyPI metadata was not updated as soon as the architectural
  decision changed.
- The workflow allowed same-named wheel artifacts from multiple jobs to merge
  without an explicit guard.

## Final Fixes Landed

These changes are now part of the repo state that produced `1.2.26`:

- `.github/workflows/publish-pypi.yml`
  - one build per platform
  - Python `3.10` only for `abi3`
  - explicit publish payload verification
  - `skip-existing: true`
- `vendor/alchemy-llm/Cargo.toml`
  - Rustls path instead of native OpenSSL path
- `rust/Cargo.toml`
  - crates.io patch to the vendored `alchemy-llm`
- `README.md`
- `docs/README.md`
- `docs/releasing-alchemy-binding.md`
- `tinyagent/alchemy_provider.py`
- `pyproject.toml`
- `uv.lock`

## Preventive Actions

### Already completed

- publish workflow now rejects any payload that does not contain exactly three
  wheels
- the release workflow no longer builds multiple same-named `abi3` wheels
- Linux no longer pulls the problematic native OpenSSL path
- published metadata now documents the in-repo binding correctly

### Recommended next actions

1. Add a dedicated script that checks for duplicate wheel basenames before
   publish, rather than relying only on an inline workflow check.
2. Keep release logic in checked-in scripts where possible; avoid inline shell
   for non-trivial validation.
3. Consider switching PyPI publishing to Trusted Publishing to simplify release
   auth and reduce warning noise in the publish job.
4. Add a release dry-run target that builds all wheels locally or in CI and
   verifies the final publish directory layout before a GitHub release is cut.
5. Add a small release checklist document that explicitly asks:
   - is this an `abi3` wheel?
   - if yes, are we building it only once per platform?

## Bottom Line

The release failed repeatedly because the binding restoration work was correct
faster than the packaging and workflow design were.

The final blocker was not the Rust binding contract, not provider typing, and
not the Python adapter. It was a broken release workflow that treated `abi3`
artifacts as if they were interpreter-specific and allowed multiple different
binaries to be produced under the same wheel filename.

`1.2.26` is the first release where the in-repo binding, wheel contents,
metadata, and PyPI publish workflow all align with the intended contract.
