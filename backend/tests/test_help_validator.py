import copy
import unittest

from backend.help.schema import CompileError
from backend.help.validator import validate_manifest


def _guide(**over):
    base = {
        "id": "a", "canonical_locale": "en", "category": "machines_telemetry",
        "kind": "troubleshooting", "risk": "low", "status": "published",
        "last_reviewed": "2026-09-02", "related_guides": [], "related_settings": [],
        "diagnostics": [], "actions": [], "common_problem_rank": None,
        "locales": {
            "en": {"title": "A", "summary": "S", "search_aliases": [], "stub": False,
                   "sections": [{"anchor": "one", "heading": "One", "blocks": []}]},
        },
    }
    base.update(over)
    return base


def _manifest(guides):
    return {"schema_version": 1, "trust_class": "admin", "build_id": None,
            "default_locale": "is", "locales": ["is", "en"],
            "guide_count": len(guides), "guides": guides, "search": {}}


class ValidatorTests(unittest.TestCase):
    def test_valid_manifest_passes(self):
        validate_manifest(_manifest({"a": _guide()}))

    def test_unresolvable_related_guide_fails(self):
        with self.assertRaises(CompileError):
            validate_manifest(_manifest({"a": _guide(related_guides=["ghost"])}))

    def test_duplicate_anchor_fails(self):
        guide = _guide()
        guide["locales"]["en"]["sections"].append({"anchor": "one", "heading": "Dup", "blocks": []})
        with self.assertRaises(CompileError):
            validate_manifest(_manifest({"a": guide}))

    def test_anchor_parity_between_full_translations_enforced(self):
        guide = _guide()
        guide["locales"]["is"] = {
            "title": "A", "summary": "S", "search_aliases": [], "stub": False,
            "sections": [{"anchor": "different", "heading": "Annad", "blocks": []}],
        }
        with self.assertRaises(CompileError):
            validate_manifest(_manifest({"a": guide}))

    def test_stub_is_exempt_from_anchor_parity(self):
        guide = _guide()
        guide["locales"]["is"] = {"title": "A", "summary": "S", "search_aliases": [], "stub": True}
        validate_manifest(_manifest({"a": guide}))

    def test_check_id_drift_between_locales_fails(self):
        guide = _guide()
        guide["locales"]["en"]["checks"] = [{"id": "c1", "question": "q"}]
        guide["locales"]["is"] = copy.deepcopy(guide["locales"]["en"])
        guide["locales"]["is"]["checks"] = [{"id": "c2", "question": "s"}]
        with self.assertRaises(CompileError):
            validate_manifest(_manifest({"a": guide}))

    def test_unpublished_guide_fails(self):
        with self.assertRaises(CompileError):
            validate_manifest(_manifest({"a": _guide(status="draft")}))

    def test_broken_guide_link_in_body_fails(self):
        guide = _guide()
        guide["locales"]["en"]["sections"][0]["blocks"] = [
            {"type": "paragraph", "inlines": [{"type": "guide_link", "guide_id": "ghost", "text": "x"}]}
        ]
        with self.assertRaises(CompileError):
            validate_manifest(_manifest({"a": guide}))


if __name__ == "__main__":
    unittest.main()
