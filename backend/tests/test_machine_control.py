import unittest
from unittest.mock import patch

from backend.controllers import machine_control
from backend.controllers.telemetry import (
    DeviceInfo,
    MachineConfigInfo,
    MachineRuntime,
    MachineStateStore,
    RUNSTATE_AVAILABLE,
)
from backend.models import Session, init_db
from backend.models.scan_log_model import ScanLog


class ScanGateTests(unittest.TestCase):
    def setUp(self):
        self._original_state = machine_control.UI_STATE.copy()
        machine_control.cancel_reset_timer()
        machine_control.update_ui_state(
            {"state": "waiting_for_code", "message": "Scan your code to start"}
        )
        init_db()
        self.db = Session()
        self.db.query(ScanLog).delete()
        self.db.commit()
        self._store = MachineStateStore.instance()
        self._store.update_definitions({}, {})

    def tearDown(self):
        machine_control.cancel_reset_timer()
        machine_control.update_ui_state(self._original_state)
        self._store.update_definitions({}, {})
        self.db.close()

    def test_can_accept_scan_only_when_waiting(self):
        self.assertTrue(machine_control.can_accept_scan())
        machine_control.update_ui_state(
            {"state": "choose_machine", "message": machine_control.SELECT_MACHINE_MESSAGE}
        )
        self.assertFalse(machine_control.can_accept_scan())

    def test_handle_scanned_code_rejects_when_not_ready(self):
        machine_control.update_ui_state(
            {"state": "machine_starting", "message": "Testing busy gate"}
        )
        with patch("backend.controllers.machine_control.validate_code") as mock_validate, patch(
            "backend.controllers.machine_control.inc"
        ) as mock_inc:
            success, message, code_info = machine_control.handle_scanned_code(
                "ABCDEFGH", source="test"
            )
        self.assertFalse(success)
        self.assertEqual(message, machine_control.SCAN_BUSY_MESSAGE)
        self.assertIsNone(code_info)
        mock_validate.assert_not_called()
        mock_inc.assert_called()

        latest = self.db.query(ScanLog).order_by(ScanLog.id.desc()).first()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.result, "invalid")
        self.assertIn("busy_state_machine_starting", latest.details)


class SelectionTimeoutTests(unittest.TestCase):
    def setUp(self):
        self._original_state = machine_control.UI_STATE.copy()
        machine_control.cancel_reset_timer()
        machine_control.update_ui_state(
            {"state": "waiting_for_code", "message": "Scan your code to start"}
        )
        init_db()
        self.store = MachineStateStore.instance()
        self.store.update_definitions({}, {})
        device = DeviceInfo(
            id=1,
            name="dev1",
            role="washer",
            model=None,
            ip="0.0.0.0",
            relay_channel=0,
            input_channel=0,
            metric_source="none",
        )
        config = MachineConfigInfo(
            on_threshold=1,
            off_threshold=0,
            on_confirm_ms=0,
            off_confirm_ms=0,
            poll_interval_ms=1000,
        )
        runtime = MachineRuntime(
            db_id=1,
            slug="washer-1",
            ui_name="Washer 1",
            uni_device=device,
            config=config,
            i4_device_id=None,
            i4_button_index=None,
            is_enabled=True,
            run_state=RUNSTATE_AVAILABLE,
        )
        self.store.update_definitions({"washer-1": runtime}, {})
        self.store.mark_pending_start("washer-1")
        machine_control._pending_starts.pop("washer-1", None)

    def tearDown(self):
        machine_control.cancel_reset_timer()
        machine_control.update_ui_state(self._original_state)
        self.store.update_definitions({}, {})

    def test_selection_timeout_clears_store_pending_when_missing_local_pending(self):
        runtime_before = self.store.get_machine("washer-1")
        self.assertTrue(runtime_before.pending_start)
        self.assertFalse(runtime_before.available)

        machine_control._selection_timeout("washer-1")

        runtime_after = self.store.get_machine("washer-1")
        self.assertFalse(runtime_after.pending_start)
        self.assertTrue(runtime_after.available)


if __name__ == "__main__":  # pragma: no cover - convenience
    unittest.main()
