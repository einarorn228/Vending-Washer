#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH=$PWD
if [[ -f .venv/bin/activate ]]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
elif [[ -f backend/.venv/bin/activate ]]; then
  # shellcheck source=/dev/null
  source backend/.venv/bin/activate
else
  echo "No virtualenv found. Create one at repo root: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
  exit 1
fi
# canonical full-runtime entrypoint:
python -m backend.app
