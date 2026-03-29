import importlib
import unittest

from backend.models import init_db, session
from backend.models.device_model import Device
from backend.models.machine_model import Machine, MachineConfig


class FlaskStartupBootstrapTests(unittest.TestCase):
    def test_flask_server_import_bootstraps_devices_and_machines(self):
        init_db()

        session.query(MachineConfig).delete()
        session.query(Machine).delete()
        session.query(Device).delete()
        session.commit()

        import backend.flask_server as flask_server

        importlib.reload(flask_server)

        self.assertGreater(session.query(Device).count(), 0)
        self.assertGreater(session.query(Machine).count(), 0)
        self.assertGreater(session.query(MachineConfig).count(), 0)


if __name__ == "__main__":
    unittest.main()
