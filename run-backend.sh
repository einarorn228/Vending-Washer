#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH=$PWD
source backend/.venv/bin/activate
# choose the right entry:
python -m backend.app         # or: python -m backend.flask_server
