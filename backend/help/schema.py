"""Frozen vocabularies for the Help Hub content model.

These are deliberately closed sets. Adding a value is a source change plus a test
change, which is the point: content must not invent categories, kinds, or block
types that the renderer has never seen.
"""

SCHEMA_VERSION = 1

LOCALES = ("is", "en")
DEFAULT_LOCALE = "is"

CATEGORIES = frozenset({
    "daily_operation", "machines_telemetry", "codes_reisa", "scanner",
    "hardware_network", "admin_recovery", "kiosk_display",
})
KINDS = frozenset({"troubleshooting", "procedure", "concept", "recovery"})
RISKS = frozenset({"low", "medium", "high"})
STATUSES = frozenset({"draft", "review", "published"})
CHECK_RESULTS = frozenset({"ok", "problem", "unsure", "not_checked"})

BLOCK_TYPES = frozenset({
    "paragraph", "heading", "ordered_list", "unordered_list",
    "code_block", "table", "callout", "guide_link", "external_link",
})
INLINE_TYPES = frozenset({
    "text", "strong", "em", "code", "setting_ref", "guide_link", "external_link",
})

# `STATUSES` above is the canonical publication state of the guide as a whole.
# Review state of ONE translation. Deliberately separate from the canonical `status`:
# a guide can be published while its Icelandic translation is still being reviewed.
TRANSLATION_STATUSES = frozenset({"draft", "review", "published"})

REQUIRED_FIELDS = frozenset({"id", "locale", "title", "summary"})
CANONICAL_ONLY_FIELDS = frozenset({
    "category", "kind", "risk", "status", "last_reviewed",
    "related_guides", "related_settings", "diagnostics", "actions",
    "common_problem_rank",
})
LOCALISED_OPTIONAL_FIELDS = frozenset({
    "search_aliases", "stub", "canonical", "checks", "translation_status",
})


class CompileError(Exception):
    """Raised for any content defect. Always fails the build; never swallowed."""
