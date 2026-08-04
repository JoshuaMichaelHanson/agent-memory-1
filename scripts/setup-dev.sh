#!/usr/bin/env sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VENV_PATH="$PROJECT_ROOT/.venv"
PYTHON="$VENV_PATH/bin/python"
TMPDIR="$PROJECT_ROOT/tmp/python-temp"
export TMPDIR

mkdir -p "$TMPDIR"

if [ ! -x "$PYTHON" ]; then
    python3 -m venv "$VENV_PATH"
fi

cd "$PROJECT_ROOT"
"$PYTHON" -m ensurepip --upgrade --default-pip
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -e ".[dev]"
"$PYTHON" -m agent_memory --help >/dev/null
"$VENV_PATH/bin/agent-memory" --help >/dev/null
"$PYTHON" -m pytest

