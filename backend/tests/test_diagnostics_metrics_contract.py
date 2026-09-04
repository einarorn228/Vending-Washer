"""Pin the histogram field names the diagnostics API actually emits.

The dev-admin metrics table rendered histogram rows by filtering for
['count', 'avg', 'p50', 'p95', 'max']. Only 'count' ever matched: the backend emits
'avg_ms', 'p95_ms', 'p99_ms', 'max_ms', and 'p50' is produced nowhere in the codebase.
Latency numbers silently vanished from the panel. These tests fix the contract on the
backend side so a rename has to break a test instead of blanking the UI again.
"""

import unittest

from backend import metrics
from backend.services.diagnostics_service import metrics_snapshot

# The exact key set backend/metrics.py:snapshot() puts in a non-empty histogram bucket.
# frontend/src/dev-admin/metricsFormat.js renders these names; keep the two in step.
EXPECTED_HISTOGRAM_FIELDS = {"count", "avg_ms", "p95_ms", "p99_ms", "max_ms"}


class HistogramFieldContractTests(unittest.TestCase):
    def setUp(self):
        self._name = "test_contract_latency_ms"
        with metrics._lock:
            for key in [k for k in metrics._histo if k[0] == self._name]:
                del metrics._histo[key]

    tearDown = setUp

    def _entry(self):
        metrics.observe_ms(self._name, 10, stage="unit")
        metrics.observe_ms(self._name, 30, stage="unit")
        payload = metrics_snapshot()
        matches = [e for e in payload["histograms"] if e["name"] == self._name]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_histogram_entry_emits_exactly_the_documented_fields(self):
        entry = self._entry()
        self.assertEqual(set(entry) - {"name", "labels"}, EXPECTED_HISTOGRAM_FIELDS)

    def test_field_names_the_panel_used_to_look_for_do_not_exist(self):
        """Names the old frontend filtered on. If one ever appears, the fix is stale."""
        entry = self._entry()
        for absent in ("avg", "p50", "p95", "max"):
            with self.subTest(field=absent):
                self.assertNotIn(absent, entry)

    def test_labels_are_carried_through_and_not_flattened_into_fields(self):
        entry = self._entry()
        self.assertEqual(entry["labels"], {"stage": "unit"})

    def test_empty_histogram_bucket_has_no_value_fields_at_all(self):
        """A bucket whose samples all aged out yields {}; the panel must tolerate it."""
        metrics.observe_ms(self._name, 10)
        with metrics._lock:
            for key in [k for k in metrics._histo if k[0] == self._name]:
                metrics._histo[key].clear()
        entry = [e for e in metrics_snapshot()["histograms"] if e["name"] == self._name][0]
        self.assertEqual(set(entry), {"name", "labels"})


if __name__ == "__main__":
    unittest.main()
