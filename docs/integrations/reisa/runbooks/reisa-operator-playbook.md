# Reisa Operator Playbook

## Purpose
This is the practical, incident-oriented guide for operating Reisa integration in this repo.

Use this playbook for:
- diagnosing Reisa sync failures,
- inspecting audit/retry state,
- safely running replay/retry actions,
- understanding what not to do during incidents.

For historical implementation details, see Reisa `completed/phases/` docs.

---

## Plain-English: what Reisa integration does
When Reisa mode is enabled, the app:
1. looks up scanned identifiers against Reisa (UUID/PIN/auto),
2. authorizes local start flow based on remaining usage,
3. after telemetry confirms start, commits external Reisa actions (start status + deduct),
4. on run completion, posts completion status,
5. records audit logs and creates retry jobs for retryable failures.

Local machine control still runs through the same backend state machine; Reisa mainly replaces entitlement/usage sync behavior.

---

## Relevant modules/files
- Provider selection: `backend/providers/provider_selector.py`
- Reisa provider: `backend/providers/reisa_provider.py`
- Reisa client/service: `backend/integrations/reisa_client.py`, `backend/integrations/reisa_service.py`
- Contract constants/helpers: `backend/integrations/reisa_contract.py`
- Orchestration: `backend/services/start_orchestrator.py`
- Durable audit logs: `backend/services/reisa_audit_service.py`
- Retry queue: `backend/services/reisa_retry_service.py`
- Replay execution: `backend/services/reisa_replay_service.py`
- Diagnostics payloads: `backend/services/reisa_diagnostics_service.py`
- Admin routes: `backend/flask_server.py` (`/admin/reisa/*`)

---

## Reisa must-have settings
At minimum:
- `provider_default = reisa`
- `provider_reisa_enabled = true`
- `reisa_base_url = <valid URL>`
- `reisa_bearer_token = <valid token>`

Optional but important:
- `reisa_action_start`
- `reisa_action_completion`
- retry worker settings (`reisa_retry_worker_*`)

If provider settings are invalid, lookup/commit paths fail with audit/error traces.

---

## Key operational flows

### Flow A: scan/authorize/start/commit
1. scan enters orchestrator
2. provider lookup + authorize
3. user chooses machine / i4 event
4. telemetry confirms run start
5. Reisa commit start status + deduct
6. usage session marked committed

### Flow B: completion sync
1. telemetry detects run stopped
2. provider completion action posts to Reisa
3. usage session marked completed (or flagged with sync failure)

### Flow C: failure + recovery
1. failed retryable action recorded in `reisa_audit_logs`
2. retry job created/updated in `reisa_retry_jobs`
3. operator (or optional worker) replays jobs
4. repair markers update usage session state

---

## Safe triage order (recommended)
1. Confirm current provider mode/settings.
2. Inspect session diagnostics for target session.
3. Inspect retry jobs (pending/retrying/exhausted/skipped).
4. Inspect failed audit events and failure categories.
5. Replay one job deliberately; re-check diagnostics.
6. Only then consider bulk replay (`retry_due`) or worker enablement.

---

## Diagnostic endpoints (admin auth + API key required)

### 1) Global sync diagnostics
```bash
curl -u admin:<password> -H "X-API-KEY: <API_KEY>" \
  http://127.0.0.1:5000/admin/reisa/sync_failures
```
Returns:
- failed sessions,
- failed audit events,
- retry jobs snapshot.

### 2) Session diagnostics
```bash
curl -u admin:<password> -H "X-API-KEY: <API_KEY>" \
  "http://127.0.0.1:5000/admin/reisa/session/<SESSION_UID>?limit=100"
```
Includes likely next operator action and recovery state counters.

### 3) Audit + retry view for one session
```bash
curl -u admin:<password> -H "X-API-KEY: <API_KEY>" \
  "http://127.0.0.1:5000/admin/reisa/audit/<SESSION_UID>?limit=100"
```

### 4) Retry jobs list
```bash
curl -u admin:<password> -H "X-API-KEY: <API_KEY>" \
  "http://127.0.0.1:5000/admin/reisa/retry_jobs?limit=100"
```

---

## Replay/retry actions

### Replay one explicit job
```bash
curl -X POST -u admin:<password> -H "X-API-KEY: <API_KEY>" \
  http://127.0.0.1:5000/admin/reisa/retry/<JOB_ID>
```

### Replay due jobs batch
```bash
curl -X POST -u admin:<password> -H "X-API-KEY: <API_KEY>" \
  "http://127.0.0.1:5000/admin/reisa/retry_due?limit=20"
```

### Worker mode (optional, settings-gated)
- `reisa_retry_worker_enabled=true` lets background loop process due jobs.
- Use cautiously; ensure single-operator ownership and monitoring.

---

## Typical failure categories you will see
Derived via `classify_reisa_failure`:
- `network_timeout`
- `network_unreachable`
- `auth_failed`
- `invalid_reference`
- `invalid_action`
- `server_5xx`
- `unexpected_response`
- `manual_skip`
- `already_synced`

Use category + status code + message together; category alone is a guide, not full root cause proof.

---

## What not to do blindly
1. Do not spam replay on same job without checking resulting state/audit entries.
2. Do not enable retry worker in unstable environment without observability.
3. Do not treat `skipped` replay status as failure automatically (may indicate idempotency guard).
4. Do not clear error markers manually without confirming successful external sync.
5. Do not change action constants (`reisa_action_*`) casually in production windows.

---

## Quick “if X, do Y”
- **Many `auth_failed` events**: verify bearer token + upstream permissions first.
- **`invalid_action` spikes**: verify `reisa_action_start` / `reisa_action_completion` values.
- **Persistent pending jobs**: inspect due-only job list + worker enabled state + upstream reachability.
- **Session failed but some actions succeeded**: use per-session diagnostics/audit to avoid duplicate side effects.
- **Exhausted jobs increasing**: switch to manual replay triage and pause automated worker if needed.

---

## Links to historical and planning docs
- Reisa docs entry: [`../README.md`](../README.md)
- Completed summary: [`../completed/README.md`](../completed/README.md)
- Phase notes: [`../completed/phases/`](../completed/phases/)
- Future backlog: [`../future/README.md`](../future/README.md)
