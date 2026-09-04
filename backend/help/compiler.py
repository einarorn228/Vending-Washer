"""Compile a guide tree into one deterministic manifest.

One implementation serves both trust classes; the security boundary is the caller's
choice of root plus the snapshot test over public guide ids, never a flag inside a
guide file.
"""

from pathlib import Path

from backend.help.blocks import parse_body
from backend.help.frontmatter import split_frontmatter
from backend.help.schema import (
    CANONICAL_ONLY_FIELDS, CATEGORIES, KINDS, LOCALES, LOCALISED_OPTIONAL_FIELDS,
    REQUIRED_FIELDS, RISKS, SCHEMA_VERSION, STATUSES, TRANSLATION_STATUSES, CompileError,
)
from backend.help.search_index import build_index_record

DIAGNOSTIC_GROUPS = frozenset({
    "core", "machine.identity", "machine.telemetry", "machine.thresholds",
    "machine.mapping", "settings.telemetry", "settings.relay", "settings.scanner",
    "settings.provider", "provider.reisa", "scanner.status", "kiosk.state",
})
KNOWN_ACTIONS = frozenset({"restart_backend"})

_LIST_FIELDS = ("related_guides", "related_settings", "diagnostics", "actions", "search_aliases")


def _as_list(value):
    return list(value) if value else []


def _validate_list_fields(meta, path):
    for field in _LIST_FIELDS:
        if field in meta and not isinstance(meta[field], list):
            raise CompileError(
                f"{path}: {field} must be a list (use '- item' syntax), got {meta[field]!r}"
            )
        if field in meta and not all(isinstance(item, str) and item for item in meta[field]):
            raise CompileError(f"{path}: {field} items must be non-empty strings")


# With list-typed fields validated strictly before this is ever called, `_as_list`
# can no longer return a single-item wrap for a scalar, so the scalar-vs-list
# asymmetry this used to guard against cannot arise; sorting a list is always correct.
def _normalised(value):
    return sorted(_as_list(value)) if isinstance(value, list) else value


def _validate_neutral(meta, path, known_settings):
    if meta.get("category") not in CATEGORIES:
        raise CompileError(f"{path}: unknown category {meta.get('category')!r}")
    if meta.get("kind") not in KINDS:
        raise CompileError(f"{path}: unknown kind {meta.get('kind')!r}")
    if meta.get("risk") not in RISKS:
        raise CompileError(f"{path}: unknown risk {meta.get('risk')!r}")
    if meta.get("status") not in STATUSES:
        raise CompileError(f"{path}: unknown status {meta.get('status')!r}")
    if not isinstance(meta.get("last_reviewed"), str) or not meta.get("last_reviewed"):
        raise CompileError(f"{path}: last_reviewed is required (ISO date string)")
    for group in _as_list(meta.get("diagnostics")):
        if group not in DIAGNOSTIC_GROUPS:
            raise CompileError(f"{path}: unknown diagnostic group {group!r}")
    for action in _as_list(meta.get("actions")):
        if action not in KNOWN_ACTIONS:
            raise CompileError(f"{path}: unknown action {action!r}")
    for key in _as_list(meta.get("related_settings")):
        if key not in known_settings:
            raise CompileError(f"{path}: unknown setting key {key!r}")


def _validate_checks(meta, path):
    checks = meta.get("checks")
    if checks is None:
        return
    if not isinstance(checks, list):
        raise CompileError(f"{path}: checks must be a list")
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            raise CompileError(f"{path}: checks[{index}] must be a mapping")
        if not isinstance(check.get("id"), str) or not check["id"]:
            raise CompileError(f"{path}: checks[{index}] needs a non-empty string id")
        # Spec 5.2 applies to every declared diagnostics group, not only the
        # guide-level list: a mistyped group on a check must fail the build too.
        groups = check.get("diagnostics")
        if groups is None:
            continue
        if isinstance(groups, str):
            groups = [groups]
        if not isinstance(groups, list):
            raise CompileError(
                f"{path}: check {check['id']!r} diagnostics must be a group name or a list of them"
            )
        for group in groups:
            if group not in DIAGNOSTIC_GROUPS:
                raise CompileError(
                    f"{path}: check {check['id']!r} names unknown diagnostic group {group!r}"
                )


# Authoring documentation lives beside the content it documents. `README.md` is the
# one reserved filename in a guide tree: it is prose for whoever writes guides, not a
# guide, so it is skipped rather than being required to carry frontmatter.
RESERVED_FILENAMES = frozenset({"README.md"})


def compile_help(root, trust_class, known_settings, build_id=None):
    root = Path(root)
    files = sorted(
        (p for p in root.rglob("*.md") if p.name not in RESERVED_FILENAMES),
        key=lambda p: str(p.relative_to(root)),
    )
    by_id, canonical = {}, {}

    for path in files:
        meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
        missing = REQUIRED_FIELDS - set(meta)
        if missing:
            raise CompileError(f"{path}: missing required field(s) {sorted(missing)}")
        # Spec §5.2: an UNKNOWN field fails the build too. Without this, a mistyped or
        # mis-indented key (e.g. `problem_guide` escaping its check) would be silently
        # accepted and then silently ignored.
        unknown = set(meta) - REQUIRED_FIELDS - CANONICAL_ONLY_FIELDS - LOCALISED_OPTIONAL_FIELDS
        if unknown:
            raise CompileError(f"{path}: unknown field(s) {sorted(unknown)}")
        _validate_checks(meta, path)
        _validate_list_fields(meta, path)
        if not isinstance(meta["id"], str) or not meta["id"]:
            raise CompileError(f"{path}: id must be a non-empty string, got {meta['id']!r}")
        if meta["locale"] not in LOCALES:
            raise CompileError(f"{path}: unknown locale {meta['locale']!r}")
        guide_id, locale = meta["id"], meta["locale"]
        entry = by_id.setdefault(guide_id, {})
        if locale in entry:
            raise CompileError(f"{path}: duplicate id {guide_id!r} for locale {locale!r}")
        if meta.get("canonical"):
            if guide_id in canonical:
                raise CompileError(f"{path}: guide {guide_id!r} has more than one canonical locale")
            canonical[guide_id] = locale
            _validate_neutral(meta, path, known_settings)
        entry[locale] = (meta, body, path)

    guides, search, excluded = {}, {}, []
    for guide_id in sorted(by_id):
        locales = by_id[guide_id]
        if guide_id not in canonical:
            raise CompileError(f"guide {guide_id!r} has no canonical locale")
        canonical_locale = canonical[guide_id]
        canonical_meta = locales[canonical_locale][0]

        record = {
            "id": guide_id,
            "canonical_locale": canonical_locale,
            "category": canonical_meta["category"],
            "kind": canonical_meta["kind"],
            "risk": canonical_meta["risk"],
            "status": canonical_meta["status"],
            "last_reviewed": str(canonical_meta["last_reviewed"]),
            "related_guides": sorted(_as_list(canonical_meta.get("related_guides"))),
            "related_settings": sorted(_as_list(canonical_meta.get("related_settings"))),
            "diagnostics": sorted(_as_list(canonical_meta.get("diagnostics"))),
            "actions": sorted(_as_list(canonical_meta.get("actions"))),
            "common_problem_rank": canonical_meta.get("common_problem_rank"),
            "locales": {},
        }

        for locale in LOCALES:
            if locale not in locales:
                continue
            meta, body, path = locales[locale]
            for field in CANONICAL_ONLY_FIELDS & set(meta):
                if locale != canonical_locale and _normalised(meta[field]) != _normalised(canonical_meta.get(field)):
                    raise CompileError(
                        f"{path}: translation overrides inherited field {field!r}"
                    )
            # A translation ships only when explicitly reviewed. The canonical locale is
            # the source text, so it is always considered published; every other locale
            # must say so, which is what stops unreviewed Icelandic reaching an operator.
            translation_status = meta.get("translation_status")
            if locale == canonical_locale:
                translation_status = "published"
            elif translation_status is None:
                translation_status = "draft"
            if translation_status not in TRANSLATION_STATUSES:
                raise CompileError(
                    f"{path}: unknown translation_status {translation_status!r}"
                )
            if translation_status != "published":
                excluded.append({"guide_id": guide_id, "locale": locale,
                                 "translation_status": translation_status})
                continue

            payload = {
                "title": meta["title"],
                "summary": meta["summary"],
                "search_aliases": sorted(_as_list(meta.get("search_aliases"))),
                "stub": bool(meta.get("stub")),
                "translation_status": translation_status,
            }
            sections = []
            if not payload["stub"]:
                sections = parse_body(body, known_settings)
                payload["sections"] = sections
                if meta.get("checks"):
                    payload["checks"] = meta["checks"]
            record["locales"][locale] = payload
            search.setdefault(guide_id, {})[locale] = build_index_record(payload, sections)

        guides[guide_id] = record

    return {
        "schema_version": SCHEMA_VERSION,
        "trust_class": trust_class,
        "build_id": build_id,
        "default_locale": LOCALES[0],
        "locales": list(LOCALES),
        "guide_count": len(guides),
        "guides": guides,
        "search": search,
        # Visible rather than silent: an unreviewed translation is withheld, not lost,
        # and the list is asserted in tests so a withheld guide cannot go unnoticed.
        "excluded_translations": sorted(
            excluded, key=lambda e: (e["guide_id"], e["locale"])
        ),
    }
