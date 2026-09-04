// Client-side mirror of the hysteresis invariant enforced in
// backend/services/dev_admin_service.py:_validate_threshold_hysteresis.
//
// telemetry._classify_band returns "high" for value >= on_threshold and "low" for
// value <= off_threshold, in that order, so the "mid" band that keeps a machine from
// flapping only exists while off < on. The backend is the authority and rejects a bad
// pair outright; this exists so the operator sees it next to the field instead of
// after a round trip. It must never be more permissive than the backend.

// Number('') is 0, not NaN, so a blank input would otherwise read as a real 0 and
// trip the invariant against a populated sibling field.
function toNumber(raw) {
  if (raw === null || raw === undefined) return NaN;
  if (typeof raw === 'string' && raw.trim() === '') return NaN;
  return Number(raw);
}

export function validateThresholdPair(technical) {
  const on = toNumber(technical?.on_threshold);
  const off = toNumber(technical?.off_threshold);
  // Blank or non-numeric input is the range check's business, not this one's.
  if (!Number.isFinite(on) || !Number.isFinite(off)) return null;
  if (off < on) return null;
  return {
    'technical.off_threshold':
      `Off threshold must be below on threshold (currently off=${off}, on=${on}). ` +
      'Equal or inverted thresholds collapse the hysteresis band and make run ' +
      'detection unreliable.',
  };
}
