"""The offered metric sources must always be ones the telemetry reader can serve.

A metric source that ``_read_metric`` has no branch for falls through to ``None``.
``_handle_poll`` then scores every poll as a read failure, the machine never records a
value, and it sits permanently offline with no error the operator can act on. That is
what shipping ``pulse`` in the dev-admin picker did. These tests make the three lists
(reader, backend picker, drawer picker) provably agree so it cannot happen again.
"""

import json
import pathlib
import re
import unittest
from unittest import mock

from backend.controllers import telemetry
from backend.controllers.telemetry import (
    IMPLEMENTED_METRIC_SOURCES,
    SELECTABLE_METRIC_SOURCES,
    DeviceInfo,
)
from backend.services.dev_admin_service import METRIC_SOURCES

_DRAWER = (
    pathlib.Path(__file__).resolve().parents[2]
    / "frontend/src/dev-admin/components/MachineDetailDrawer.jsx"
)

# Payloads a Shelly device returns for each source, keyed by the field the reader wants.
# No network is touched; requests.get is replaced wholesale.
_FAKE_BODIES = {
    "power": {"apower": 12.5},
    "adc": {"voltage": 1.5},
    "digital": {"state": True},
    "voltage": {"voltage": 7.5},
    "voltmeter": {"voltage": 7.5},
}


class _FakeResponse:
    def __init__(self, body):
        self.status_code = 200
        self._body = body

    def json(self):
        return self._body


def _device(metric_source):
    return DeviceInfo(
        id=1,
        name="test-uni",
        role="washer_uni",
        model="shelly-uni",
        ip="192.0.2.50",
        relay_channel=0,
        input_channel=0,
        metric_source=metric_source,
    )


class MetricSourceContractTests(unittest.TestCase):
    def test_every_offered_source_is_one_the_reader_implements(self):
        """The safety invariant. Offering an unreadable source = permanent offline."""
        offered = set(SELECTABLE_METRIC_SOURCES) - {"none"}
        unreadable = offered - set(IMPLEMENTED_METRIC_SOURCES)
        self.assertEqual(
            unreadable,
            set(),
            f"SELECTABLE_METRIC_SOURCES offers {sorted(unreadable)}, which _read_metric "
            "has no branch for. Any machine set to it stays permanently offline. Either "
            "implement a branch in _read_metric or stop offering the value.",
        )

    def test_reader_actually_returns_a_value_for_each_implemented_source(self):
        """Guards the constant itself: a stale name in it would pass the subset check."""
        for source in sorted(IMPLEMENTED_METRIC_SOURCES):
            with self.subTest(metric_source=source):
                with mock.patch.object(
                    telemetry.requests,
                    "get",
                    return_value=_FakeResponse(_FAKE_BODIES[source]),
                ) as fake_get:
                    value = telemetry._read_metric(_device(source))
                self.assertIsNotNone(
                    value,
                    f"_read_metric returned None for {source!r}, so it is listed in "
                    "IMPLEMENTED_METRIC_SOURCES but has no working branch.",
                )
                self.assertIsInstance(value, float)
                self.assertTrue(fake_get.called)

    def test_unimplemented_source_still_reads_as_none(self):
        """Characterises the failure being guarded against, using the old 'pulse' value."""
        with mock.patch.object(telemetry.requests, "get") as fake_get:
            self.assertIsNone(telemetry._read_metric(_device("pulse")))
        self.assertFalse(
            fake_get.called, "an unknown metric source must not issue any HTTP request"
        )

    def test_backend_validator_offers_exactly_the_selectable_set(self):
        self.assertEqual(METRIC_SOURCES, set(SELECTABLE_METRIC_SOURCES))

    def test_drawer_picker_offers_exactly_the_selectable_set(self):
        """The drawer duplicates the list in JS; catch it drifting from the backend."""
        source = _DRAWER.read_text(encoding="utf-8")
        match = re.search(r"const\s+METRIC_SOURCES\s*=\s*(\[[^\]]*\])\s*;", source)
        self.assertIsNotNone(
            match, f"could not find the METRIC_SOURCES array literal in {_DRAWER}"
        )
        offered = json.loads(match.group(1).replace("'", '"'))
        self.assertEqual(
            offered,
            list(SELECTABLE_METRIC_SOURCES),
            "MachineDetailDrawer.jsx offers a different metric-source list than "
            "SELECTABLE_METRIC_SOURCES in backend/controllers/telemetry.py.",
        )


if __name__ == "__main__":
    unittest.main()
