"""Apply Reisa provider settings to the local SQLite database (one-shot ops helper).

Usage:
  export REISA_BEARER_TOKEN='your-token'
  python -m backend.setup.configure_reisa

Full stack (Reisa + Shelly/relay + telemetry + retry worker + CORS for Vite/kiosk):
  export REISA_BEARER_TOKEN='your-token'
  python -m backend.setup.configure_reisa --full-stack

Optional:
  python -m backend.setup.configure_reisa --token 'your-token'
  python -m backend.setup.configure_reisa --base-url 'https://...' --dry-run
  python -m backend.setup.configure_reisa --full-stack --cors-origins 'http://localhost:3000,http://192.168.1.106:3000'
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

# Browser origins allowed to call Flask directly (comma-separated in DB). Vite/kiosk on same host:
DEFAULT_FULL_STACK_CORS = (
    "http://localhost,http://localhost:3000,http://127.0.0.1:3000"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure Reisa integration settings in codes.db")
    parser.add_argument(
        "--token",
        default="",
        help="Bearer token (otherwise REISA_BEARER_TOKEN env var)",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Reisa API base URL")
    parser.add_argument(
        "--full-stack",
        action="store_true",
        help="Also enable hardware relay, telemetry, Reisa retry worker, and CORS for local UI/kiosk",
    )
    parser.add_argument(
        "--cors-origins",
        default="",
        help=f"Comma-separated CORS origins (default with --full-stack: {DEFAULT_FULL_STACK_CORS!r} + CORS_EXTRA_ORIGINS)",
    )
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
        if args.full_stack:
            cors = (args.cors_origins or "").strip()
            if not cors:
                extra = (os.environ.get("CORS_EXTRA_ORIGINS") or "").strip()
                parts = [p.strip() for p in DEFAULT_FULL_STACK_CORS.split(",") if p.strip()]
                if extra:
                    parts.extend([p.strip() for p in extra.split(",") if p.strip()])
                # de-dupe while preserving order
                seen: set[str] = set()
                cors = ",".join(p for p in parts if p not in seen and not seen.add(p))
            updates.update(
                {
                    "backend_relay_enabled": "true",
                    "telemetry_enabled": "true",
                    "reisa_retry_worker_enabled": "true",
                    "cors_allowed_origins": cors,
                }
            )
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
        if args.full_stack:
            print("  full-stack: backend_relay_enabled=true telemetry_enabled=true")
            print("            reisa_retry_worker_enabled=true")
            print(f"            cors_allowed_origins={updates['cors_allowed_origins']!r}")

        # sanity: read back URL
        url = get_setting_value(session, "reisa_base_url", "")
        if url != updates["reisa_base_url"]:
            print("Warning: read-back reisa_base_url mismatch", file=sys.stderr)
            return 1
    finally:
        session.close()

    print("\nNext: restart the backend (python -m backend.app).")
    if args.full_stack:
        print("Note: CORS origins are read when Flask starts — restart the backend to apply the new list.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
