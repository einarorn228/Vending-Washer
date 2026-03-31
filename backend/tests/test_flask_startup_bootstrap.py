import importlib
import unittest

import backend.app as backend_app
import backend.flask_server as flask_server
from backend.models import init_db, session
from backend.models.device_model import Device
from backend.models.machine_model import Machine, MachineConfig
from backend.models.setting_model import Settings


class FlaskStartupBootstrapTests(unittest.TestCase):
    def setUp(self):
        init_db()
        session.query(MachineConfig).delete()
        session.query(Machine).delete()
        session.query(Device).delete()
        session.query(Settings).delete()
        session.commit()

    def test_flask_server_import_does_not_bootstrap_devices_or_machines(self):
        importlib.reload(flask_server)

        self.assertEqual(session.query(Device).count(), 0)
        self.assertEqual(session.query(Machine).count(), 0)
        self.assertEqual(session.query(MachineConfig).count(), 0)

    def test_initialize_runtime_bootstraps_settings_devices_and_machines(self):
        backend_app.initialize_runtime()

        self.assertIsNotNone(session.query(Settings).filter_by(key="api_key").first())
        self.assertEqual(
            session.query(Settings).filter_by(key="backend_relay_enabled").first().value,
            "false",
        )
        self.assertGreater(session.query(Device).count(), 0)
        self.assertGreater(session.query(Machine).count(), 0)
        self.assertGreater(session.query(MachineConfig).count(), 0)


if __name__ == "__main__":
    unittest.main()
