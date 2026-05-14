"""Set SQLite settings for full hardware + telemetry (Shelly / button box / washer relays).

Does not touch Reisa credentials. Safe to re-run.

Usage:
  .venv/bin/python -m backend.setup.enable_hardware_e2e
  .venv/bin/python -m backend.setup.enable_hardware_e2e --dry-run
"""

from __future__ import annotations

import argparse
import sys

from backend.models import Session, init_db
from backend.models.setting_model import get_setting_value, update_setting_value

# Values tuned for on-device testing like a real user.
E2E_HARDWARE_SETTINGS = {
    "backend_relay_enabled": "true",
    "telemetry_enabled": "true",
    "scan_timeout": "3",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Enable hardware paths for end-to-end kiosk testing")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    init_db()
    session = Session()
    try:
        if args.dry_run:
            print("Dry run — would set:")
            for k, v in E2E_HARDWARE_SETTINGS.items():
                cur = get_setting_value(session, k, "")
                print(f"  {k}: {cur!r} -> {v!r}")
            return 0
        for k, v in E2E_HARDWARE_SETTINGS.items():
            update_setting_value(session, k, v)
        print("Hardware E2E settings applied:")
        for k, v in E2E_HARDWARE_SETTINGS.items():
            print(f"  {k}={v}")
    finally:
        session.close()

    print("\nRestart the backend so the serial scanner re-opens with scan_timeout if it changed.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
