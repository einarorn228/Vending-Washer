import base64
import hashlib
import unittest

from backend.flask_server import app
from backend.models import Session, init_db, session
from backend.models.code_model import Code
from backend.models.setting_model import update_setting_value


class AdminAuthTests(unittest.TestCase):
    def setUp(self):
        init_db()
        session.query(Code).delete()
        session.commit()

        update_setting_value(session, "api_key", "test-api-key")
        update_setting_value(session, "admin_username", "admin")
        update_setting_value(
            session,
            "admin_password_hash",
            hashlib.sha256("secret".encode("utf-8")).hexdigest(),
        )

        session.add(Code(code="TESTCODE", order_id="ORD-1", usage_limit=1, current_usage=0))
        session.commit()

        app.config["TESTING"] = True
        self.client = app.test_client()

    @staticmethod
    def _auth_header(username: str, password: str) -> str:
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
        return f"Basic {token}"

    def test_admin_delete_requires_both_api_key_and_basic_auth(self):
        # Missing both
        resp = self.client.delete("/admin/codes/TESTCODE")
        self.assertEqual(resp.status_code, 401)

        # Invalid Basic + valid API key
        resp = self.client.delete(
            "/admin/codes/TESTCODE",
            headers={
                "X-API-KEY": "test-api-key",
                "Authorization": self._auth_header("admin", "wrong-password"),
            },
        )
        self.assertEqual(resp.status_code, 401)

        # Basic only
        resp = self.client.delete(
            "/admin/codes/TESTCODE",
            headers={"Authorization": self._auth_header("admin", "secret")},
        )
        self.assertEqual(resp.status_code, 401)

        # API key only
        resp = self.client.delete(
            "/admin/codes/TESTCODE",
            headers={"X-API-KEY": "test-api-key"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_admin_delete_succeeds_with_api_key_and_basic_auth(self):
        resp = self.client.delete(
            "/admin/codes/TESTCODE",
            headers={
                "X-API-KEY": "test-api-key",
                "Authorization": self._auth_header("admin", "secret"),
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(session.query(Code).filter_by(code="TESTCODE").first())

    def test_other_admin_route_also_requires_api_key(self):
        resp = self.client.get(
            "/admin/codes",
            headers={"Authorization": self._auth_header("admin", "secret")},
        )
        self.assertEqual(resp.status_code, 401)

    def test_admin_delete_by_order_id_requires_both_api_key_and_basic_auth(self):
        # Missing both
        resp = self.client.delete("/admin/codes/by_order_id/ORD-1")
        self.assertEqual(resp.status_code, 401)

        # API key only
        resp = self.client.delete(
            "/admin/codes/by_order_id/ORD-1",
            headers={"X-API-KEY": "test-api-key"},
        )
        self.assertEqual(resp.status_code, 401)

        # Basic only
        resp = self.client.delete(
            "/admin/codes/by_order_id/ORD-1",
            headers={"Authorization": self._auth_header("admin", "secret")},
        )
        self.assertEqual(resp.status_code, 401)

        # Both valid
        resp = self.client.delete(
            "/admin/codes/by_order_id/ORD-1",
            headers={
                "X-API-KEY": "test-api-key",
                "Authorization": self._auth_header("admin", "secret"),
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(session.query(Code).filter_by(order_id="ORD-1").all())

    def test_session_factory_creates_distinct_sessions(self):
        s1 = Session()
        s2 = Session()
        try:
            self.assertIsNot(s1, s2)
        finally:
            s1.close()
            s2.close()

    def test_teardown_removes_scoped_session_between_app_contexts(self):
        with app.app_context():
            first = session()
            first_id = id(first)

        with app.app_context():
            second = session()
            second_id = id(second)

        self.assertNotEqual(first_id, second_id)


if __name__ == "__main__":
    unittest.main()
