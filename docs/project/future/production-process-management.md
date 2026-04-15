# Production process management (future work)

## Does this require code changes?

**Not for a baseline.** Keeping backend and frontend running across reboots, logout, and SSH disconnect is primarily **operational**: `systemd` units (or another supervisor) that invoke the same commands you already use (`run-backend.sh`, `python -m backend.app`, static frontend build + web server, or `npm run` in a controlled way). No application code has to change for that.

**Optional code / packaging improvements** (only if you want a more polished field deployment):

- Turn off Flask `debug=True` for production (`backend/app.py` / server startup path).
- Add a dedicated `npm` script for production that **does not** run the Pi Chromium opener (`frontend/package.json` — today `npm run dev` bundles kiosk side effects).
- Optional HTTP **health** route used only for `systemd` `ExecStartPost` / load balancers.
- Ship **example** `systemd` unit files in-repo (still “ops”, but versioned with the project).

Canonical operational checklist (session scope, lingering, buyer handoff):  
[`docs/operations/runbooks/runtime-and-process-management.md`](../../operations/runbooks/runtime-and-process-management.md)

## Backlog link

Tracked at a high level as **“Service packaging for kiosk deployments”** in [`backlog.md`](./backlog.md).
