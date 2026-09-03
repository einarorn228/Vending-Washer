# backend/tests/test_help_artifacts.py
import json
import unittest

from backend.help import cli


class ArtifactTests(unittest.TestCase):
    def test_committed_admin_manifest_is_current(self):
        fresh = cli.build_manifest(cli.ADMIN_ROOT, "admin")
        committed = json.loads(cli.ADMIN_ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(cli.serialise(fresh), cli.ADMIN_ARTIFACT.read_text(encoding="utf-8"),
                         msg="admin manifest is stale; run: python -m backend.help.cli")
        self.assertEqual(committed["trust_class"], "admin")

    def test_committed_public_manifest_is_current(self):
        fresh = cli.build_manifest(cli.PUBLIC_ROOT, "public_bootstrap")
        self.assertEqual(cli.serialise(fresh), cli.PUBLIC_ARTIFACT.read_text(encoding="utf-8"),
                         msg="public manifest is stale; run: python -m backend.help.cli")

    def test_public_manifest_guide_ids_are_snapshotted(self):
        committed = json.loads(cli.PUBLIC_ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(
            sorted(committed["guides"]),
            ["backend-unavailable", "kiosk-screen-blank", "network-unavailable"],
            msg="public help content changed: this list is a deliberate security review gate",
        )

    def test_admin_manifest_may_reference_secret_setting_identifiers(self):
        """`api_key` is a setting NAME, not a credential.

        An admin guide about credential rotation has to be able to say the word. The
        test that matters is that no credential VALUE is present, not that the
        identifier is banned -- banning it would make legitimate documentation
        impossible. Prove the identifier is permitted by compiling a guide that uses it.
        """
        import tempfile
        from pathlib import Path
        from backend.help.compiler import compile_help

        root = Path(tempfile.mkdtemp())
        guide = root / "en" / "admin_recovery" / "rotate-credentials.md"
        guide.parent.mkdir(parents=True)
        guide.write_text(
            "---\nid: rotate-credentials\nlocale: en\ncanonical: true\n"
            "title: Rotate credentials\nsummary: How to rotate the API key.\n"
            "category: admin_recovery\nkind: procedure\nrisk: high\nstatus: published\n"
            "last_reviewed: 2026-09-02\nrelated_settings:\n  - api_key\n---\n\n"
            "## Steps {#steps}\n\nRotate `api_key` from the Security panel.\n",
            encoding="utf-8",
        )
        manifest = compile_help(root, "admin", cli.known_setting_keys(), build_id=None)
        self.assertEqual(manifest["guides"]["rotate-credentials"]["related_settings"], ["api_key"])

    def test_admin_manifest_contains_no_credential_shaped_values(self):
        import re
        text = cli.ADMIN_ARTIFACT.read_text(encoding="utf-8")
        # 32+ hex chars covers api_key (64 hex) and sha256 password hashes;
        # 40+ base64-ish chars covers bearer tokens.
        for pattern in (r"[A-Fa-f0-9]{32,}", r"[A-Za-z0-9+/]{40,}={0,2}"):
            hits = re.findall(pattern, text)
            self.assertEqual(hits, [], msg=f"credential-shaped value in admin manifest: {hits[:1]}")

    def test_public_manifest_rejects_privileged_identifiers_entirely(self):
        """The public tier is stricter on purpose: it is readable by anyone on the LAN,
        so even naming a privileged setting or procedure is out of bounds."""
        text = cli.PUBLIC_ARTIFACT.read_text(encoding="utf-8").lower()
        for forbidden in ("api_key", "admin_password_hash", "reisa_bearer_token", "reisa",
                          "bearer", "dev_admin_enabled", "dev_admin", "backend_relay_enabled",
                          "relay", "shelly", "update_setting_value", ".venv/bin/activate",
                          "python -", "python3", "sqlite", "codes.db", "backend.models",
                          "session()", "<<'py'", "/dev/admin", "x-api-key", "basic auth",
                          "seed_settings", "get_api_key"):
            self.assertNotIn(forbidden, text,
                             msg=f"{forbidden!r} must never reach the public tier")

    def test_build_id_is_the_only_volatile_field(self):
        text = cli.ADMIN_ARTIFACT.read_text(encoding="utf-8")
        self.assertNotIn("generated_at", text)


if __name__ == "__main__":
    unittest.main()
