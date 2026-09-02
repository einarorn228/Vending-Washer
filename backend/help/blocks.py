"""Convert guide Markdown into our strict, allowlisted block schema.

mistune parses; this module decides what is allowed to exist. Any node type we do
not explicitly map raises CompileError, so unsupported syntax fails the build
instead of silently disappearing from a guide an operator is relying on.
"""

import re

import mistune

from backend.help.schema import CompileError

ANCHOR_RE = re.compile(r"\s*\{#([a-z0-9][a-z0-9-]*)\}\s*$")
_ALERT_RE = re.compile(r"^\[!(NOTE|WARNING|DANGER)\]\s*$", re.IGNORECASE)
_GUIDE_SCHEME = "guide:"

_markdown = mistune.create_markdown(renderer=None, plugins=["table"])


def _raw(nodes):
    result = []
    for n in nodes:
        raw = n.get("raw", "")
        if raw:
            result.append(raw)
        elif n.get("type") == "softbreak":
            result.append("\n")
        else:
            result.append(_raw(n.get("children", [])))
    return "".join(result)


def _inlines(nodes, known_settings):
    out = []
    for node in nodes:
        kind = node.get("type")
        if kind == "text":
            out.append({"type": "text", "text": node.get("raw", "")})
        elif kind == "softbreak":
            out.append({"type": "text", "text": " "})
        elif kind == "codespan":
            value = node.get("raw", "")
            out.append(
                {"type": "setting_ref", "value": value}
                if value in known_settings
                else {"type": "code", "text": value}
            )
        elif kind == "strong":
            out.append({"type": "strong", "inlines": _inlines(node.get("children", []), known_settings)})
        elif kind == "emphasis":
            out.append({"type": "em", "inlines": _inlines(node.get("children", []), known_settings)})
        elif kind == "link":
            url = (node.get("attrs") or {}).get("url", "")
            text = _raw(node.get("children", []))
            if url.startswith(_GUIDE_SCHEME):
                out.append({"type": "guide_link", "guide_id": url[len(_GUIDE_SCHEME):], "text": text})
            else:
                out.append({"type": "external_link", "url": url, "text": text})
        elif kind in ("block_html", "inline_html"):
            raise CompileError("raw HTML is not allowed in guide content")
        else:
            raise CompileError(f"unsupported inline node: {kind!r}")
    return out


def _list_items(node, known_settings):
    items = []
    for item in node.get("children", []):
        blocks = []
        for child in item.get("children", []):
            if child.get("type") in ("block_text", "paragraph"):
                blocks.append({"type": "paragraph",
                               "inlines": _inlines(child.get("children", []), known_settings)})
            elif child.get("type") == "list":
                blocks.append(_block(child, known_settings))
            else:
                raise CompileError(f"unsupported list child: {child.get('type')!r}")
        items.append(blocks)
    return items


def _block(node, known_settings):
    kind = node.get("type")
    if kind == "paragraph":
        return {"type": "paragraph", "inlines": _inlines(node.get("children", []), known_settings)}
    if kind == "block_code":
        return {"type": "code_block",
                "language": (node.get("attrs") or {}).get("info") or "",
                "text": node.get("raw", "").rstrip("\n")}
    if kind == "list":
        ordered = bool((node.get("attrs") or {}).get("ordered"))
        return {"type": "ordered_list" if ordered else "unordered_list",
                "items": _list_items(node, known_settings)}
    if kind == "table":
        # mistune 3 shape (verified): table_head holds table_cell nodes DIRECTLY,
        # while table_body -> table_row -> table_cell. Treating the head like a
        # body would emit one empty "row" per header cell.
        header, rows = [], []
        for part in node.get("children", []):
            if part.get("type") == "table_head":
                header = [_inlines(c.get("children", []), known_settings)
                          for c in part.get("children", [])]
            elif part.get("type") == "table_body":
                for row in part.get("children", []):
                    rows.append([_inlines(c.get("children", []), known_settings)
                                 for c in row.get("children", [])])
            else:
                raise CompileError(f"unsupported table part: {part.get('type')!r}")
        return {"type": "table", "header": header, "rows": rows}
    if kind == "block_quote":
        children = node.get("children", [])
        level = "note"
        if children:
            first = _raw(children[0].get("children", [])).strip()
            match = _ALERT_RE.match(first.splitlines()[0] if first else "")
            if match:
                level = match.group(1).lower()
        blocks = []
        for child in children:
            block = _block(child, known_settings)
            if block["type"] == "paragraph":
                block["inlines"] = [
                    i for i in block["inlines"]
                    if not (i["type"] == "text" and _ALERT_RE.match(i["text"].strip()))
                ]
                if not block["inlines"]:
                    continue
            blocks.append(block)
        return {"type": "callout", "level": level, "blocks": blocks}
    if kind in ("block_html", "inline_html"):
        raise CompileError("raw HTML is not allowed in guide content")
    raise CompileError(f"unsupported block node: {kind!r}")


def parse_body(markdown_text, known_settings):
    ast = _markdown(markdown_text)
    sections = [{"anchor": None, "heading": None, "blocks": []}]
    for node in ast:
        kind = node.get("type")
        if kind == "blank_line":
            continue
        if kind == "heading":
            level = (node.get("attrs") or {}).get("level", 1)
            text = _raw(node.get("children", []))
            if level == 2:
                match = ANCHOR_RE.search(text)
                if not match:
                    raise CompileError(f"H2 heading needs a stable anchor: {text!r}")
                sections.append({"anchor": match.group(1),
                                 "heading": text[: match.start()].strip(),
                                 "blocks": []})
                continue
            sections[-1]["blocks"].append(
                {"type": "heading", "level": level, "text": ANCHOR_RE.sub("", text).strip()}
            )
            continue
        sections[-1]["blocks"].append(_block(node, known_settings))
    if not sections[0]["blocks"]:
        sections.pop(0)
    return sections
