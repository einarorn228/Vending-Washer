#!/usr/bin/env bash
# Open the Vite UI in Chromium kiosk mode on the Pi display.
# KIOSK_URL: page to open (default http://localhost:3000/)
# KIOSK_DISABLE_GPU: set to 0 to skip --disable-gpu (default 1; helps blank white kiosk windows on some Pi/GPU stacks)

export DISPLAY=:0
export XAUTHORITY="${XAUTHORITY:-/home/hamrar/.Xauthority}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

CHROME=""
if command -v chromium >/dev/null 2>&1; then
  CHROME=chromium
elif command -v chromium-browser >/dev/null 2>&1; then
  CHROME=chromium-browser
else
  echo "open-pi-browser: no chromium or chromium-browser in PATH" >&2
  exit 1
fi

KIOSK_URL="${KIOSK_URL:-http://localhost:3000/}"

CHROME_FLAGS=(
  --no-first-run
  --no-default-browser-check
  --password-store=basic
  --test-type
  --disable-features=Translate,OptimizationHints,PushMessaging
  --disable-infobars
  --noerrdialogs
  --kiosk
  "$KIOSK_URL"
  --user-data-dir=/home/hamrar/.config/chromium-kiosk
  --disk-cache-dir=/home/hamrar/.cache/chromium-kiosk
)

if [[ "${KIOSK_DISABLE_GPU:-1}" != "0" ]]; then
  CHROME_FLAGS+=(--disable-gpu)
fi

# Run a single kiosk instance; do not discard stderr (hidden failures were hard to debug).
"$CHROME" "${CHROME_FLAGS[@]}" "$@" &
