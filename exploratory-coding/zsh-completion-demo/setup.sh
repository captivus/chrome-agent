#!/usr/bin/env bash
# Build a real chrome-agent entry point for the demo shell, from this checkout.
# Editable, so edits to the completion take effect without reinstalling.
#
# Not a `uv run` wrapper named chrome-agent: that shadows itself on PATH and,
# measured, ended up executing the globally installed tool instead of this
# build -- so the demo silently tested the wrong binary. A venv with a real
# console script has no such ambiguity, and saves ~50 ms per Tab.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
uv venv --quiet --allow-existing "$HERE/.venv"
uv pip install --quiet --python "$HERE/.venv/bin/python" --editable "$REPO"
"$HERE/.venv/bin/chrome-agent" --version
