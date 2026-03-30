# Project Backlog (Issues and Suggestions)

Canonical project-level backlog for non-Reisa work and cross-cutting improvements.

## How to use this file
- Keep items actionable and scoped.
- Move implemented items to **Resolved** with date and short note.
- Do not implement suggestion items without explicit owner approval.

## Open issues (important next work)

### 2) Duplicate settings bootstrap path
- **Location:** `backend/app.py`, `backend/flask_server.py`
- **Issue:** settings bootstrap was historically called from multiple startup paths.
- **Impact:** startup duplication/noise and side-effect risk.
- **Next action:** confirm current startup behavior and enforce one canonical bootstrap ownership path.

### 3) Shared SQLAlchemy session across threads
- **Location:** `backend/models/__init__.py`
- **Issue:** global session reuse was historically noted across Flask + background threads.
- **Impact:** thread-safety and transaction integrity risk.
- **Next action:** evaluate scoped/per-request session strategy and migration approach.

## Approved-later suggestions (not active work)

### A) Replace full page reload on result handling
- **Idea:** replace `window.location.reload()` style reset with explicit UI-state reset path.
- **Benefit:** smoother UX and fewer reload race conditions.

### B) Service packaging for kiosk deployments
- **Idea:** package backend launcher as system service (`systemd`/Windows service).
- **Benefit:** reliable reboot/start behavior in field deployments.

## Resolved
- **2026-03-29:** Admin DELETE endpoints auth gap item closed; both delete routes are protected by `@require_admin_auth` and covered by `backend/tests/test_admin_auth.py`.
- **2025-07-17:** Frontend idle-state rendering stabilized in `frontend/src/App.jsx` (switch ordering/default handling).
- **2025-07-17:** Removed hard-coded API key path in `frontend/src/api/backend.js`; now uses localStorage or `VITE_API_KEY`.
- **2025-07-19:** Machine definitions moved to DB-backed models + seed scripts (`device_model`, `machine_model`, `seed_machines`).
