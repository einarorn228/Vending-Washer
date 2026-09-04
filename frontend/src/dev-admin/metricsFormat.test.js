import test from 'node:test';
import assert from 'node:assert/strict';

import { formatHistogramEntry, HISTOGRAM_FIELDS } from './metricsFormat.js';

// Shaped exactly like a backend/services/diagnostics_service.py histogram entry.
const realEntry = {
  name: 'scan_latency_ms',
  labels: { provider: 'local' },
  count: 42,
  avg_ms: 18.666666666666668,
  p95_ms: 40,
  p99_ms: 55,
  max_ms: 61,
};

test('renders every field the backend actually emits', () => {
  const out = formatHistogramEntry(realEntry);
  assert.equal(out, 'count=42 · avg=18.7ms · p95=40ms · p99=55ms · max=61ms');
});

test('the field keys match the backend contract, not the old guesses', () => {
  // Regression guard: these four names were what the panel used to filter for and none
  // of them exist in the payload, so the row rendered as 'count=42' and nothing else.
  const keys = HISTOGRAM_FIELDS.map((f) => f.key);
  assert.deepEqual(keys, ['count', 'avg_ms', 'p95_ms', 'p99_ms', 'max_ms']);
  for (const stale of ['avg', 'p50', 'p95', 'max']) {
    assert.ok(!keys.includes(stale), `${stale} is not a backend field name`);
  }
});

test('an entry missing every value field says so instead of rendering blank', () => {
  assert.equal(formatHistogramEntry({ name: 'x', labels: {} }), 'no samples');
});

test('a whole-number average drops the pointless trailing zero', () => {
  assert.equal(formatHistogramEntry({ count: 2, avg_ms: 20 }), 'count=2 · avg=20ms');
});

test('non-numeric or absent values are skipped rather than printed', () => {
  assert.equal(
    formatHistogramEntry({ count: 1, avg_ms: null, p95_ms: undefined, max_ms: NaN }),
    'count=1',
  );
});

test('a missing or malformed entry degrades to a dash', () => {
  assert.equal(formatHistogramEntry(null), '—');
  assert.equal(formatHistogramEntry('nope'), '—');
});
