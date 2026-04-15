#!/usr/bin/env bash
# Step-by-step Reisa + vending flow using curl (and optional browser on :3000).
# Prerequisite: backend on :5000, Reisa settings in codes.db.
#
# Usage:
#   chmod +x tools/reisa_walkthrough.sh
#   ./tools/reisa_walkthrough.sh              # interactive pauses
#   ./tools/reisa_walkthrough.sh --auto       # no pauses
#
# Override UUID:
#   REISA_TEST_UUID='your-uuid' ./tools/reisa_walkthrough.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

AUTO=false
[[ "${1:-}" == "--auto" ]] && AUTO=true

pause() {
  if ! $AUTO; then
    read -r -p ">>> Ýttu á Enter fyrir næsta skref... " _
  fi
}

CODE="${REISA_TEST_UUID:-6b85048b-bf6f-4451-9a2b-3b55fdb80b86}"
BASE="${BACKEND_URL:-http://127.0.0.1:5000}"

if [[ ! -d "$ROOT/.venv" ]]; then
  echo "Vantar .venv í $ROOT — búðu til venv og pip install -r requirements.txt"
  exit 1
fi

API_KEY="$(source "$ROOT/.venv/bin/activate" && python "$ROOT/backend/scripts/get_api_key.py")"
export API_KEY

hdr_api=(-H "X-API-KEY: $API_KEY" -H "Content-Type: application/json")

echo "=========================================="
echo "Reisa walkthrough (CLI)"
echo "CODE (UUID)=$CODE"
echo "BASE=$BASE"
echo "API_KEY len=${#API_KEY}"
echo "=========================================="
echo ""
echo "Frontend: opnaðu http://localhost:3000 og í DevTools Console:"
echo "  localStorage.setItem('API_KEY', '$API_KEY');"
echo "  location.reload()"
echo ""
pause

echo ""
echo "=== Skref 1: Sækja /api/ui_state (bíð eftir skönnun) ==="
curl -sS "${hdr_api[@]}" "$BASE/api/ui_state" | python3 -m json.tool || true
pause

echo ""
echo "=== Skref 2: Skanna = senda UUID í /api/scan_code ==="
curl -sS -X POST "${hdr_api[@]}" -d "{\"code\":\"$CODE\"}" "$BASE/api/scan_code" | python3 -m json.tool || true
pause

echo ""
echo "=== Skref 3: ui_state á eftir skönnun (veldu vél) ==="
curl -sS "${hdr_api[@]}" "$BASE/api/ui_state" | python3 -m json.tool || true
pause

echo ""
echo "Veldu MACHINE_ID sem er available=true í skrefi 3 (oftast washer1)."
MACHINE_ID="${MACHINE_ID:-washer1}"
echo "Nota machine_id=$MACHINE_ID (stilltu MACHINE_ID=... um þarf)"
pause

echo ""
echo "=== Skref 4: Ræsa vél /api/start_machine ==="
curl -sS -X POST "${hdr_api[@]}" -d "{\"code\":\"$CODE\",\"machine_id\":\"$MACHINE_ID\"}" "$BASE/api/start_machine" | python3 -m json.tool || true
pause

echo ""
echo "=== Skref 5: ui_state á eftir start ==="
curl -sS "${hdr_api[@]}" "$BASE/api/ui_state" | python3 -m json.tool || true
pause

echo ""
echo "=== Skref 6 (valfrjálst): i4 takki — aðeins ef þú notar i4-flæði ==="
echo "Slepptu þessu ef þú notar aðeins skjával (start_machine)."
echo "Dæmi: curl ... /api/i4_event?button=0"
pause

echo ""
echo "=== Skref 7: Reisa beint — GET /uuid (staðfesting án bakenda) ==="
BASE_URL="$(sqlite3 "$ROOT/codes.db" "select value from settings where key='reisa_base_url';")"
TOKEN="$(sqlite3 "$ROOT/codes.db" "select value from settings where key='reisa_bearer_token';")"
curl -sS -H "Authorization: Bearer ${TOKEN}" -H "Accept: application/json" "${BASE_URL%/}/uuid/${CODE}" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); d.pop('pinCode',None); print(json.dumps(d, indent=2, ensure_ascii=False))" || true

echo ""
echo "=========================================="
echo "Lokið CLI hluta."
echo ""
echo "Ath: Fullt Reisa 'commit' (deduct + status) og lokun keyra oft eftir að"
echo "Shelly/telemetry staðfestir raunverulegan gang. Á skrifborði getur UI staða"
echo "haldist í machine_starting án véla — það þýðir ekki endilega að Reisa hafi brostið."
echo "=========================================="
