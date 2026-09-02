// frontend/src/dev-admin/help/checklistState.js
// "not sure" and "not checked" are evidence, not absences: a developer reading an
// escalation report needs to know which steps the operator could not complete.
export const CHECK_RESULTS = ['ok', 'problem', 'unsure', 'not_checked'];

export function initialCheckState(checks) {
  const state = {};
  for (const check of checks || []) state[check.id] = 'not_checked';
  return state;
}

export function setCheckResult(state, checkId, result) {
  if (!CHECK_RESULTS.includes(result)) return state;
  return { ...state, [checkId]: result };
}

export function toReportChecks(state) {
  return Object.entries(state).map(([check_id, result]) => ({ check_id, result }));
}

// The exact wire shape for POST /support_report. `locale_shown` is server-owned
// (Task 10) and deliberately absent here — the backend derives it from the
// resolved guide, never from the client. Keeping this as one pure function
// (rather than an inline object literal in SupportReportButton) means the
// request body's shape is asserted by a test instead of only by reading the
// component.
export function buildSupportReportBody({ guideId, machineId, checks, locale }) {
  return {
    guide_id: guideId,
    machine_id: machineId ?? null,
    checks: checks || [],
    locale,
  };
}
