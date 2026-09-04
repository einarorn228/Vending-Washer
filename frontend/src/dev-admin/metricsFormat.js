// Rendering for the diagnostics histogram rows.
//
// The field names below are the ones backend/metrics.py:snapshot() actually emits, and
// they are pinned by backend/tests/test_diagnostics_metrics_contract.py. The panel used
// to filter for ['count', 'avg', 'p50', 'p95', 'max']; only 'count' matched, so every
// latency figure rendered as nothing at all. Do not rename these without changing the
// backend and that test together.

const HISTOGRAM_FIELDS = [
  { key: 'count', label: 'count', unit: null },
  { key: 'avg_ms', label: 'avg', unit: 'ms' },
  { key: 'p95_ms', label: 'p95', unit: 'ms' },
  { key: 'p99_ms', label: 'p99', unit: 'ms' },
  { key: 'max_ms', label: 'max', unit: 'ms' },
];

// avg_ms is a mean and arrives with a long fractional tail; the percentiles and max are
// already integers. One decimal is enough to read, and trailing '.0' is noise.
function formatMs(value) {
  const rounded = Math.round(value * 10) / 10;
  return `${Number.isInteger(rounded) ? rounded : rounded.toFixed(1)}ms`;
}

export function formatHistogramEntry(entry) {
  if (!entry || typeof entry !== 'object') return '—';
  const parts = [];
  for (const { key, label, unit } of HISTOGRAM_FIELDS) {
    const value = entry[key];
    if (typeof value !== 'number' || !Number.isFinite(value)) continue;
    parts.push(`${label}=${unit === 'ms' ? formatMs(value) : value}`);
  }
  // A bucket whose samples have all aged out comes back with name/labels only.
  return parts.length ? parts.join(' · ') : 'no samples';
}

export { HISTOGRAM_FIELDS };
