#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH=$PWD
source backend/.venv/bin/activate
# canonical full-runtime entrypoint:
python -m backend.app
