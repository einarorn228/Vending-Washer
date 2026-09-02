"""Search tokens for the Help Hub.

Icelandic inflection is suffixal, so the stem is stable at the front. Folding plus
prefix matching (done in the browser) absorbs definite forms, plurals, genitives and
head-initial compounds without a stemmer. This module only produces the folded
tokens; scoring lives in frontend/src/dev-admin/help/helpSearch.js.
"""

import re
import unicodedata

MIN_TOKEN_LEN = 4

_FOLD_MAP = {"þ": "th", "ð": "d", "æ": "ae", "ö": "o"}
_TOKEN_RE = re.compile(r"[a-z0-9]+")

STOPWORDS = frozenset({
    "og", "eda", "sem", "thad", "their", "ekki", "vera", "verdur", "thegar", "meira",
    "the", "and", "for", "with", "that", "this", "from", "your", "should", "when",
})


def fold(text):
    lowered = (text or "").lower()
    expanded = "".join(_FOLD_MAP.get(char, char) for char in lowered)
    decomposed = unicodedata.normalize("NFD", expanded)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def tokenise(text):
    return [token for token in _TOKEN_RE.findall(fold(text)) if len(token) >= 2]


def _significant(text):
    return sorted({t for t in tokenise(text) if len(t) >= MIN_TOKEN_LEN and t not in STOPWORDS})


def _inline_text(inlines):
    parts = []
    for inline in inlines or []:
        if "text" in inline:
            parts.append(inline["text"])
        if "value" in inline:
            parts.append(inline["value"])
        if "inlines" in inline:
            parts.append(_inline_text(inline["inlines"]))
    return " ".join(parts)


def _block_text(blocks):
    parts = []
    for block in blocks or []:
        kind = block.get("type")
        if kind in ("paragraph", "heading"):
            parts.append(block.get("text") or _inline_text(block.get("inlines")))
        elif kind in ("ordered_list", "unordered_list"):
            for item in block.get("items", []):
                parts.append(_block_text(item))
        elif kind == "callout":
            parts.append(_block_text(block.get("blocks")))
        elif kind == "table":
            for row in [block.get("header", [])] + block.get("rows", []):
                for cell in row:
                    parts.append(_inline_text(cell))
    return " ".join(p for p in parts if p)


def build_index_record(locale_payload, sections):
    return {
        "title": _significant(locale_payload.get("title", "")),
        "summary": _significant(locale_payload.get("summary", "")),
        "aliases": _significant(" ".join(locale_payload.get("search_aliases") or [])),
        "headings": _significant(" ".join(s.get("heading") or "" for s in sections or [])),
        "body": _significant(" ".join(_block_text(s.get("blocks")) for s in sections or [])),
    }
