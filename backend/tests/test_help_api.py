# backend/tests/test_help_api.py
import base64
import hashlib
import unittest
from unittest.mock import patch

from backend.flask_server import app
from backend.models import init_db, session
from backend.models.setting_model import Settings, update_setting_value
from backend.services import help_service

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin-pass"


def _basic_auth_headers(username: str, password: str) -> dict:
    """The dev/admin blueprint authenticates with HTTP Basic, not X-API-KEY."""

    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _seed_admin():
    session.query(Settings).delete()
    session.commit()
    update_setting_value(session, "api_key", "test-key")
    update_setting_value(session, "dev_admin_enabled", "true")
    update_setting_value(session, "admin_username", ADMIN_USERNAME)
    update_setting_value(
        session, "admin_password_hash",
        hashlib.sha256(ADMIN_PASSWORD.encode("utf-8")).hexdigest(),
    )
    update_setting_value(session, "backend_relay_enabled", "false")


class HelpApiContractTests(unittest.TestCase):
    def setUp(self):
        init_db()
        _seed_admin()
        help_service.reset_cache()
        self.client = app.test_client()
        self.headers = _basic_auth_headers(ADMIN_USERNAME, ADMIN_PASSWORD)
        self.known_guide = next(iter(help_service.get_manifest()["guides"]))

    def tearDown(self):
        help_service.reset_cache()

    # ----- authentication contract, identical to the rest of /api/dev_admin -----

    def test_no_auth_is_rejected(self):
        for path in ("/api/dev_admin/help/manifest", "/api/dev_admin/help/status"):
            self.assertEqual(self.client.get(path).status_code, 401, path)
        self.assertEqual(self.client.post("/api/dev_admin/support_report", json={}).status_code, 401)

    def test_wrong_password_is_rejected(self):
        bad = _basic_auth_headers(ADMIN_USERNAME, "wrong")
        self.assertEqual(self.client.get("/api/dev_admin/help/manifest", headers=bad).status_code, 401)

    def test_kill_switch_returns_403_like_every_other_dev_admin_route(self):
        update_setting_value(session, "dev_admin_enabled", "false")
        for path in ("/api/dev_admin/help/manifest", "/api/dev_admin/help/status"):
            resp = self.client.get(path, headers=self.headers)
            self.assertEqual(resp.status_code, 403, path)
            self.assertTrue(resp.get_json()["disabled"])
        resp = self.client.post("/api/dev_admin/support_report", json={}, headers=self.headers)
        self.assertEqual(resp.status_code, 403)

    def test_authenticated_and_enabled_succeeds(self):
        payload = self.client.get("/api/dev_admin/help/manifest", headers=self.headers).get_json()
        self.assertTrue(payload["success"])
        self.assertIn("guides", payload["manifest"])
        status = self.client.get("/api/dev_admin/help/status", headers=self.headers).get_json()
        self.assertTrue(status["status"]["available"])

    # ----- cache headers -----

    def test_help_responses_are_no_store(self):
        for resp in (
            self.client.get("/api/dev_admin/help/manifest", headers=self.headers),
            self.client.get("/api/dev_admin/help/status", headers=self.headers),
            self.client.post("/api/dev_admin/support_report", json={}, headers=self.headers),
            self.client.post("/api/dev_admin/support_report", json=[], headers=self.headers),
        ):
            self.assertIn("no-store", resp.headers.get("Cache-Control", ""), resp.request.path)

    # ----- request validation: HTTP is stricter than the service -----

    def _post(self, body):
        return self.client.post("/api/dev_admin/support_report", json=body, headers=self.headers)

    def test_omitted_guide_id_is_a_generic_report(self):
        resp = self._post({})
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.get_json()["report"]["guide_id"])

    def test_known_guide_id_is_a_contextual_report(self):
        resp = self._post({"guide_id": self.known_guide})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["report"]["guide_id"], self.known_guide)

    def test_unknown_guide_id_is_404_not_a_silent_generic_report(self):
        resp = self._post({"guide_id": "no-such-guide"})
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(resp.get_json()["success"])

    def test_malformed_guide_id_is_400(self):
        for bad in (7, {"a": 1}, ["x"], "", "x" * 200):
            with self.subTest(guide_id=bad):
                self.assertEqual(self._post({"guide_id": bad}).status_code, 400)

    def test_malformed_machine_id_type_is_400(self):
        for bad in (7, {"a": 1}, ["x"], "x" * 200):
            with self.subTest(machine_id=bad):
                self.assertEqual(self._post({"machine_id": bad}).status_code, 400)

    def test_unsupported_locale_is_400(self):
        for bad in ("de", "", 7, None):
            with self.subTest(locale=bad):
                self.assertEqual(self._post({"locale": bad}).status_code, 400)

    def test_non_object_json_body_is_400_not_500(self):
        for body in ([], "text", 42, None):
            with self.subTest(body=body):
                resp = self._post(body)
                self.assertEqual(resp.status_code, 400)
                self.assertFalse(resp.get_json()["success"])

    def test_checks_must_be_a_list_and_bounded(self):
        self.assertEqual(self._post({"checks": {"a": 1}}).status_code, 400)
        self.assertEqual(self._post({"checks": "ok"}).status_code, 400)
        flood = [{"check_id": "c", "result": "ok"}] * 500
        self.assertEqual(self._post({"checks": flood}).status_code, 400)

    # ----- boundary: client cannot widen scope or forge provenance -----

    def test_client_groups_and_locale_shown_are_ignored(self):
        resp = self._post({"groups": ["machine.mapping", "secrets"], "locale_shown": "xx",
                           "fields": ["api_key"], "locale": "is"})
        report = resp.get_json()["report"]
        self.assertNotIn("machine.mapping", report["groups"])
        self.assertEqual(report["locale_shown"], "is")

    def test_report_carries_provenance(self):
        report = self._post({"locale": "is"}).get_json()["report"]
        self.assertEqual(report["help"], help_service.get_provenance())
        self.assertEqual(report["locale_requested"], "is")

    def test_response_includes_rendered_text(self):
        payload = self._post({"locale": "is"}).get_json()
        self.assertIn("help_manifest_digest", payload["text"])

    # ----- read-only at the route level -----

    def test_support_report_route_is_read_only(self):
        before = sorted((s.key, s.value) for s in session.query(Settings).all())
        with patch("backend.utils.shelly_control.send_shelly_pulse") as pulse, \
             patch("backend.utils.shelly_control.shelly_switch_on") as on, \
             patch("backend.utils.shelly_control.shelly_switch_off") as off, \
             patch("requests.get") as http_get, patch("requests.post") as http_post:
            self.assertEqual(self._post({"guide_id": self.known_guide}).status_code, 200)
        session.expire_all()
        after = sorted((s.key, s.value) for s in session.query(Settings).all())
        self.assertEqual(before, after)
        for mock in (pulse, on, off, http_get, http_post):
            mock.assert_not_called()


class HelpFailureIsolationTests(unittest.TestCase):
    """Help may fail; the kiosk may not fail because Help failed — at the app level."""

    def setUp(self):
        init_db()
        _seed_admin()
        self.client = app.test_client()
        self.headers = _basic_auth_headers(ADMIN_USERNAME, ADMIN_PASSWORD)

    def tearDown(self):
        help_service.reset_cache()

    def _broken(self, **kwargs):
        help_service.reset_cache()
        return patch.object(help_service, "_read_artifact", **kwargs)

    def _assert_kiosk_unaffected(self):
        resp = self.client.get("/api/ui_state", headers={"X-API-KEY": "test-key"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("state", resp.get_json())

    def _assert_help_unavailable(self, reason):
        resp = self.client.get("/api/dev_admin/help/manifest", headers=self.headers)
        self.assertEqual(resp.status_code, 503)
        body = resp.get_json()
        self.assertEqual(body["reason"], reason)
        self.assertEqual(set(body), {"success", "message", "reason"})
        text = resp.get_data(as_text=True)
        for leak in ("Traceback", "Error:", "/home/", "backend/help/generated"):
            self.assertNotIn(leak, text)
        self.assertIn("no-store", resp.headers.get("Cache-Control", ""))

    def test_missing_manifest(self):
        with self._broken(side_effect=FileNotFoundError):
            self._assert_help_unavailable("manifest_missing")
            self._assert_kiosk_unaffected()

    def test_malformed_manifest(self):
        with self._broken(return_value="{not json"):
            self._assert_help_unavailable("manifest_unreadable")
            self._assert_kiosk_unaffected()

    def test_unsupported_schema(self):
        with self._broken(return_value='{"schema_version": 999, "guides": {}}'):
            self._assert_help_unavailable("schema_version_unsupported")
            self._assert_kiosk_unaffected()

    def test_support_report_still_answers_when_help_is_broken(self):
        with self._broken(side_effect=OSError("io")):
            resp = self.client.post("/api/dev_admin/support_report", json={}, headers=self.headers)
            self.assertEqual(resp.status_code, 200)
            self.assertIsNone(resp.get_json()["report"]["help"]["manifest_digest"])

    def test_other_dev_admin_tabs_still_work_while_help_is_broken(self):
        with self._broken(side_effect=OSError("io")):
            for path in ("/api/dev_admin/status", "/api/dev_admin/settings", "/api/dev_admin/machines"):
                self.assertEqual(self.client.get(path, headers=self.headers).status_code, 200, path)


if __name__ == "__main__":
    unittest.main()
