#!/usr/bin/env bash
# Open the Vite UI in Chromium kiosk mode on the Pi display.
# KIOSK_URL: page to open (default http://localhost:3000/)
# KIOSK_DISABLE_GPU: set to 1 to add --disable-gpu (default 0; use only for blank/white kiosk windows on some Pi stacks)

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

KIOSK_WINDOW_SIZE="${KIOSK_WINDOW_SIZE:-1920,1080}"
# Keep scale baseline deterministic across Pi models.
# If physical panel calibration needs it, test: 1.05, 1.1, or 1.15 explicitly.
KIOSK_DEVICE_SCALE_FACTOR="${KIOSK_DEVICE_SCALE_FACTOR:-1}"

CHROME_FLAGS=(
  --no-first-run
  --no-default-browser-check
  --password-store=basic
  --test-type
  --disable-features=Translate,OptimizationHints,PushMessaging
  --disable-infobars
  --noerrdialogs
  --incognito
  --kiosk
  --start-fullscreen
  --window-size=${KIOSK_WINDOW_SIZE}
  --force-device-scale-factor=${KIOSK_DEVICE_SCALE_FACTOR}
  --high-dpi-support=1
  --enable-gpu-rasterization
  --ignore-gpu-blocklist
  --enable-zero-copy
  --restore-last-session=false
  --user-data-dir=/home/hamrar/.config/chromium-kiosk
  --disk-cache-dir=/home/hamrar/.cache/chromium-kiosk
  "$KIOSK_URL"
)

# Set KIOSK_DISABLE_GPU=1 only if your Pi build shows a white/blank window.
if [[ "${KIOSK_DISABLE_GPU:-0}" == "1" ]]; then
  CHROME_FLAGS+=(--disable-gpu)
fi

# Run a single kiosk instance; do not discard stderr (hidden failures were hard to debug).
"$CHROME" "${CHROME_FLAGS[@]}" "$@" &


# Debug checklist (Pi):
# 1) Navigate to chrome://gpu and confirm "Hardware accelerated" where available.
# 2) In DevTools console run:
#    window.innerWidth, window.innerHeight
#    window.devicePixelRatio
# 3) Compare values with laptop Chrome at the same URL/layout state.
