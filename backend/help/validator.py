"""Cross-guide rules. Every violation fails the build.

A broken cross-reference is worse here than in ordinary docs: an operator hits it
mid-incident, so it must never reach a manifest.
"""

from backend.help.schema import CompileError


def _walk_inlines(inlines, sink):
    for inline in inlines or []:
        if inline.get("type") == "guide_link":
            sink.append(inline["guide_id"])
        _walk_inlines(inline.get("inlines"), sink)


def _walk_blocks(blocks, sink):
    for block in blocks or []:
        _walk_inlines(block.get("inlines"), sink)
        _walk_blocks(block.get("blocks"), sink)
        for item in block.get("items", []) or []:
            _walk_blocks(item, sink)
        for row in [block.get("header", [])] + (block.get("rows") or []):
            for cell in row or []:
                _walk_inlines(cell, sink)


def validate_manifest(manifest):
    guides = manifest["guides"]
    known = set(guides)

    for guide_id, guide in sorted(guides.items()):
        if guide.get("status") != "published":
            raise CompileError(f"{guide_id}: status must be 'published' to ship, got "
                               f"{guide.get('status')!r}")
        for ref in guide.get("related_guides", []):
            if ref not in known:
                raise CompileError(f"{guide_id}: related_guides references unknown {ref!r}")

        anchor_sets, check_id_sets = {}, {}
        for locale, payload in sorted(guide["locales"].items()):
            if payload.get("stub"):
                continue
            anchors = [s["anchor"] for s in payload.get("sections", []) if s.get("anchor")]
            if len(anchors) != len(set(anchors)):
                raise CompileError(f"{guide_id} [{locale}]: duplicate section anchor")
            anchor_sets[locale] = set(anchors)

            refs = []
            for section in payload.get("sections", []):
                _walk_blocks(section.get("blocks"), refs)
            for ref in refs:
                if ref not in known:
                    raise CompileError(f"{guide_id} [{locale}]: guide_link to unknown {ref!r}")

            checks = payload.get("checks") or []
            check_id_sets[locale] = [c["id"] for c in checks]
            for check in checks:
                target = check.get("problem_guide")
                if target and target not in known:
                    raise CompileError(
                        f"{guide_id} [{locale}]: check {check['id']!r} problem_guide "
                        f"references unknown {target!r}"
                    )

        distinct_anchors = {frozenset(v) for v in anchor_sets.values()}
        if len(distinct_anchors) > 1:
            raise CompileError(f"{guide_id}: section anchors differ between full translations")
        distinct_checks = {tuple(v) for v in check_id_sets.values()}
        if len(distinct_checks) > 1:
            raise CompileError(f"{guide_id}: check ids differ between full translations")
