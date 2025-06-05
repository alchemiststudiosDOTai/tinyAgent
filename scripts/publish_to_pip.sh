#!/usr/bin/env bash
# publish_to_pip.sh  —  build & upload with **automatic patch‑increment**
# -----------------------------------------------------------------------------
# 1. Find highest version among:
#       • the latest Git tag   (vX.Y.Z)
#       • the latest on PyPI   (tiny-agent-os)
# 2. Increment patch → X.Y.(Z+1)
# 3. Build and upload to **real** PyPI (git tagging is manual)
# -----------------------------------------------------------------------------

set -euo pipefail

PKG="tiny-agent-os"           # PyPI package name

# ── repo root ────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# ── emoji‑free logging helpers ─────────────────────────────────────────────
GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; NC=$'\033[0m'
log(){ printf "%b\n" "${GREEN}==>${NC} $*"; }
die(){ printf "%b\n" "${RED}ERROR:${NC} $*" >&2; exit 1; }

# ── prerequisites -----------------------------------------------------------
for cmd in python3 pip git twine; do command -v $cmd >/dev/null || die "$cmd missing"; done
[[ -f ~/.pypirc ]] || die "~/.pypirc missing (should contain real‑PyPI token)"

pip -q install build twine setuptools_scm packaging >/dev/null

# ── cleanup -----------------------------------------------------------------
rm -rf dist build *.egg-info

# ── fetch latest PyPI version ----------------------------------------------
remote=$(python3 - "$PKG" <<'PY'
import json, sys, ssl, urllib.request, packaging.version as V
pkg=sys.argv[1]
try:
    data=json.load(urllib.request.urlopen(f'https://pypi.org/pypi/{pkg}/json', context=ssl.create_default_context()))
    print(max(data['releases'], key=V.Version))
except Exception:
    print('0.0.0')
PY
)
log "Latest on PyPI  : $remote"

# ── fetch latest Git tag -----------------------------------------------------
git fetch --tags -q
local=$(git tag --sort=-v:refname | head -n1 | sed 's/^v//')
[[ -z $local ]] && local="0.0.0"
log "Latest Git tag  : $local"

# ── choose max(remote, local) & bump patch ----------------------------------
base=$(python3 - "$remote" "$local" <<'PY'
import sys, packaging.version as V
r,l=sys.argv[1:]
print(r if V.Version(r)>=V.Version(l) else l)
PY
)
IFS=. read -r MAJ MIN PAT <<<"$base"
VERSION="$MAJ.$MIN.$((PAT+1))"
log "Next version    : $VERSION"

export SETUPTOOLS_SCM_PRETEND_VERSION="$VERSION"

# ── skip git tagging (manual process) ----------------------------------------
log "Skipping git tag creation (manual process)"

# ── build -------------------------------------------------------------------
log "Building wheel/sdist"; python3 -m build

# ── upload ------------------------------------------------------------------
log "Uploading to PyPI"; python3 -m twine upload -r pypi dist/*

log "🎉  $PKG $VERSION published on PyPI"
