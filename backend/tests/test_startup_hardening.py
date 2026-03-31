import importlib
import sys
import unittest
from unittest.mock import Mock, patch

from backend.controllers import machine_control, telemetry
from backend.models import init_db, session
from backend.models.setting_model import Settings, is_backend_relay_enabled


class RelaySettingSafetyTests(unittest.TestCase):
    def setUp(self):
        init_db()
        session.query(Settings).filter_by(key="backend_relay_enabled").delete()
        session.commit()

    def test_missing_backend_relay_setting_defaults_to_false(self):
        self.assertFalse(is_backend_relay_enabled(session))


class ScannerImportSafetyTests(unittest.TestCase):
    def test_importing_scanner_module_does_not_open_serial(self):
        with patch("serial.Serial") as serial_ctor:
            import backend.controllers.qr_scanner as qr_scanner

            importlib.reload(qr_scanner)

        serial_ctor.assert_not_called()

    def test_start_scanner_listener_initializes_serial_on_demand(self):
        import backend.controllers.qr_scanner as qr_scanner

        qr_scanner._serial_initialized = False
        qr_scanner.SERIAL_AVAILABLE = False
        qr_scanner.ser = None
        qr_scanner._scanner_thread = None

        fake_thread = Mock()
        fake_thread.is_alive.return_value = False

        with patch("backend.controllers.qr_scanner.serial.Serial") as serial_ctor, patch(
            "backend.controllers.qr_scanner.threading.Thread", return_value=fake_thread
        ):
            qr_scanner.start_scanner_listener()

        serial_ctor.assert_called_once()
        fake_thread.start.assert_called_once()


class SeedModuleImportSafetyTests(unittest.TestCase):
    def setUp(self):
        init_db()

    def _reload_module_without_cache(self, module_name: str):
        sys.modules.pop(module_name, None)
        return importlib.import_module(module_name)

    def test_importing_seed_settings_does_not_initialize_db(self):
        with patch("backend.models.init_db") as init_db_mock:
            self._reload_module_without_cache("backend.setup.seed_settings")

        init_db_mock.assert_not_called()

    def test_importing_seed_machines_does_not_initialize_db(self):
        with patch("backend.models.init_db") as init_db_mock:
            self._reload_module_without_cache("backend.setup.seed_machines")

        init_db_mock.assert_not_called()

    def test_bootstrap_settings_initializes_db_explicitly(self):
        import backend.setup.seed_settings as seed_settings

        with patch("backend.setup.seed_settings.init_db") as init_db_mock:
            seed_settings.bootstrap_settings()

        self.assertGreaterEqual(init_db_mock.call_count, 1)

    def test_bootstrap_devices_and_machines_initializes_db_explicitly(self):
        import backend.setup.seed_machines as seed_machines

        with patch("backend.setup.seed_machines.init_db") as init_db_mock:
            seed_machines.bootstrap_devices_and_machines()

        self.assertGreaterEqual(init_db_mock.call_count, 1)


class StartupIdempotencyTests(unittest.TestCase):
    def test_telemetry_start_is_idempotent(self):
        telemetry._poll_thread = None

        fake_thread = Mock()
        fake_thread.is_alive.return_value = True

        with patch("backend.controllers.telemetry.threading.Thread", return_value=fake_thread) as thread_ctor:
            telemetry.start_telemetry_poll()
            telemetry.start_telemetry_poll()

        thread_ctor.assert_called_once()
        fake_thread.start.assert_called_once()

    def test_machine_control_listener_registration_is_idempotent(self):
        store = machine_control.MachineStateStore.instance()
        machine_control._listeners_registered = False
        store._listeners = {"runstate_started": [], "runstate_stopped": [], "device_offline": []}

        machine_control.register_store_listeners()
        machine_control.register_store_listeners()

        self.assertEqual(len(store._listeners["runstate_started"]), 1)
        self.assertEqual(len(store._listeners["runstate_stopped"]), 1)
        self.assertEqual(len(store._listeners["device_offline"]), 1)


if __name__ == "__main__":
    unittest.main()
