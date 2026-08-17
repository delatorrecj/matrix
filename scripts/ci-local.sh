#!/usr/bin/env bash
# Reproduce GitHub CI locally from a fresh clone of this repo.
#
# A clone contains exactly what CI checks out: data/processed/ is present;
# data/raw/ and the SUMO net/demand files are absent (gitignored). That is
# strictly better than overriding MATRIX_NET_PATH, which produces false
# failures: test_config.py asserts the *default* config paths.
#
# Usage (from anywhere in the repo):
#   bash scripts/ci-local.sh
#   CLONE=/tmp/ci-clone bash scripts/ci-local.sh
#
# Reuses the source tree's venvs when they exist so you don't re-download
# the CUDA torch stack. Point Redis + Postgres at dead ports so the
# integration tests skip exactly as CI does.

set -euo pipefail

SOURCE="$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)"
BRANCH="$(git -C "$SOURCE" rev-parse --abbrev-ref HEAD)"
CLONE="${CLONE:-/tmp/ci-clone}"

pick_python() {
  local venv="$1"
  if [[ -x "$venv/Scripts/python.exe" ]]; then
    echo "$venv/Scripts/python.exe"
  elif [[ -x "$venv/bin/python" ]]; then
    echo "$venv/bin/python"
  else
    echo ""
  fi
}

KVENV="$(pick_python "$SOURCE/app/packages/kernel/.venv")"
AVENV="$(pick_python "$SOURCE/app/apps/api/.venv")"

if [[ -z "$KVENV" ]]; then
  echo "kernel venv not found at $SOURCE/app/packages/kernel/.venv" >&2
  echo "Create it first: cd app/packages/kernel && uv sync --extra dev" >&2
  exit 1
fi
if [[ -z "$AVENV" ]]; then
  echo "api venv not found at $SOURCE/app/apps/api/.venv" >&2
  echo "Create it first: cd app/apps/api && uv sync" >&2
  exit 1
fi

echo "==> cloning $BRANCH into $CLONE"
rm -rf "$CLONE"
git clone --branch "$BRANCH" "$SOURCE" "$CLONE"

export MATRIX_REDIS_URL="redis://localhost:59998/0"
export MATRIX_PG_DSN="postgresql://matrix:matrix@localhost:59999/matrix"

echo "==> kernel pytest (expect: SUMO-net and Redis tests skip)"
cd "$CLONE/app/packages/kernel"
"$KVENV" -m pytest -q -rs

echo "==> sanity: imports resolve inside the clone, not the source tree"
PYTHONPATH="$CLONE/app/packages/kernel" "$KVENV" -c \
  "import matrix_kernel, matrix_kernel.datasets as d; print(matrix_kernel.__file__); print(d._REPO_ROOT)"

echo "==> api pytest (exclude live WS integration, as CI does)"
cd "$CLONE/app/apps/api"
"$AVENV" -m pytest -q -k "not test_ws_stream_all_modules" -rs

echo "==> web vitest + build"
cd "$CLONE/app/apps/web"
npm ci
npm run test -- --run
npm run build

echo "==> ci-local finished"
