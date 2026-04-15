"""Apply Reisa provider settings to the local SQLite database (one-shot ops helper).

Usage:
  export REISA_BEARER_TOKEN='your-token'
  python -m backend.setup.configure_reisa

Optional:
  python -m backend.setup.configure_reisa --token 'your-token'
  python -m backend.setup.configure_reisa --base-url 'https://...' --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys

from backend.models import Session, init_db
from backend.models.setting_model import get_setting_value, update_setting_value

DEFAULT_BASE_URL = "https://backend.dev.reisa.is/hamrar/api/service"
ACTION_START = "WASHING_MACHINE_START"
ACTION_COMPLETE = "WASHING_MACHINE_COMPLETE"


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure Reisa integration settings in codes.db")
    parser.add_argument(
        "--token",
        default="",
        help="Bearer token (otherwise REISA_BEARER_TOKEN env var)",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Reisa API base URL")
    parser.add_argument("--dry-run", action="store_true", help="Print values only, do not write DB")
    args = parser.parse_args()

    token = (args.token or os.environ.get("REISA_BEARER_TOKEN") or "").strip()
    if not token and not args.dry_run:
        print("Error: set REISA_BEARER_TOKEN or pass --token", file=sys.stderr)
        return 1

    init_db()
    session = Session()
    try:
        updates = {
            "provider_default": "reisa",
            "provider_reisa_enabled": "true",
            "reisa_base_url": (args.base_url or "").rstrip("/"),
            "reisa_bearer_token": token,
            "reisa_action_start": ACTION_START,
            "reisa_action_completion": ACTION_COMPLETE,
        }
        if args.dry_run:
            print("Dry run — would set:")
            for k, v in updates.items():
                if k == "reisa_bearer_token":
                    print(f"  {k}={'(set)' if v else '(empty)'}")
                else:
                    print(f"  {k}={v!r}")
            return 0

        for key, value in updates.items():
            update_setting_value(session, key, value)

        print("Reisa settings updated:")
        print(f"  provider_default=reisa provider_reisa_enabled=true")
        print(f"  reisa_base_url={updates['reisa_base_url']!r}")
        print(f"  reisa_action_start={ACTION_START!r} reisa_action_completion={ACTION_COMPLETE!r}")
        print(f"  reisa_bearer_token={'(set, len=' + str(len(token)) + ')'}")

        # sanity: read back URL
        url = get_setting_value(session, "reisa_base_url", "")
        if url != updates["reisa_base_url"]:
            print("Warning: read-back reisa_base_url mismatch", file=sys.stderr)
            return 1
    finally:
        session.close()

    print("\nNext: restart the backend (python -m backend.app).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
