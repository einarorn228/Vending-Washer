#!/usr/bin/env bash
set -euo pipefail

# Absolute paths
REPO_DIR="/home/hamrar/Documents/Vending-Washer"
BACKEND_LOG="$REPO_DIR/backend.log"
FRONTEND_LOG="$REPO_DIR/frontend.log"

stop_app() {
  echo "Stöðva alla ferla tengda Vending-Washer..."
  pkill -f "python -m backend.app" || true
  pkill -f "vite --host --port 3000" || true
  pkill -f "chromium" || true
  pkill -f "chromium-browser" || true
  pkill -f "run-backend.sh" || true
  pkill -f "run-frontend.sh" || true
  sleep 1
}

start_app() {
  stop_app
  echo "Ræsi bakenda..."
  cd "$REPO_DIR"
  nohup ./run-backend.sh > "$BACKEND_LOG" 2>&1 &
  
  echo "Bíð eftir að bakendi verði tilbúinn..."
  sleep 3
  
  echo "Ræsi framenda og kioskglugga..."
  nohup ./run-frontend.sh > "$FRONTEND_LOG" 2>&1 &
  echo "Vending-Washer hefur verið ræst!"
}

status_app() {
  echo "=== Vending-Washer Staða ==="
  if lsof -i :5000 >/dev/null 2>&1; then
    echo "Bakendi: Í gangi (port 5000)"
  else
    echo "Bakendi: EKKI í gangi"
  fi
  
  if lsof -i :3000 >/dev/null 2>&1; then
    echo "Framendi: Í gangi (port 3000)"
  else
    echo "Framendi: EKKI í gangi"
  fi

  if pgrep -f "chromium" >/dev/null 2>&1; then
    echo "Chromium Kiosk: Í gangi"
  else
    echo "Chromium Kiosk: EKKI í gangi"
  fi
}

case "${1:-}" in
  start)
    start_app
    ;;
  stop)
    stop_app
    ;;
  restart)
    start_app
    ;;
  status)
    status_app
    ;;
  *)
    echo "Notkun: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac
