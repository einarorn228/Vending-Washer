#!/usr/bin/env bash
set -euo pipefail

# Move into the frontend directory
cd "$(dirname "$0")/frontend"

# Ensure display and X authority are set for Chromium on Pi
export DISPLAY=:0
export XAUTHORITY=/home/hamrar/.Xauthority
export XDG_RUNTIME_DIR=/run/user/$(id -u)

# Start the frontend dev server
# (If you built in kiosk mode earlier, this will also open Chromium on the Pi)
npm run dev
