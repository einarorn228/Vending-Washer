#!/usr/bin/env bash
export DISPLAY=:0
export XAUTHORITY=/home/hamrar/.Xauthority
export XDG_RUNTIME_DIR=/run/user/$(id -u)

chromium-browser \
  --no-first-run \
  --no-default-browser-check \
  --password-store=basic \
  --test-type \
  --disable-features=Translate,OptimizationHints,PushMessaging \
  --disable-infobars \
  --noerrdialogs \
  --kiosk http://localhost:3000/ \
  --user-data-dir=/home/hamrar/.config/chromium-kiosk \
  --disk-cache-dir=/home/hamrar/.cache/chromium-kiosk \
  --log-level=3 >/dev/null 2>&1 &

# Kiosk flags optional; remove --kiosk if you want windowed
chromium-browser --noerrdialogs --disable-infobars --kiosk http://localhost:3000/ &

