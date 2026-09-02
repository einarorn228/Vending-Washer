"""Minimal frontmatter parser for the Help Hub subset.

Supports exactly what guides are allowed to use: `key: value` scalars, `- item`
string lists, and one list-of-mappings (`checks`). Anything else raises, which is
the intended behaviour -- guides must not carry arbitrary YAML.
"""

from backend.help.schema import CompileError

DELIMITER = "---"
_TRUE = {"true", "yes"}
_FALSE = {"false", "no"}


def _coerce(raw: str):
    text = raw.strip()
    if text.lower() in _TRUE:
        return True
    if text.lower() in _FALSE:
        return False
    if text and (text.lstrip("-").isdigit()):
        return int(text)
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    return text


def split_frontmatter(text: str):
    lines = text.splitlines()
    if not lines or lines[0].strip() != DELIMITER:
        raise CompileError("file must start with a '---' frontmatter block")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == DELIMITER)
    except StopIteration:
        raise CompileError("frontmatter block is not terminated by '---'")

    meta = {}
    key = None            # current list-valued key
    entry = None          # current mapping inside a list-of-mappings
    for lineno, line in enumerate(lines[1:end], start=2):
        if "\t" in line:
            raise CompileError(f"line {lineno}: tabs are not allowed in frontmatter")
        if not line.strip():
            continue
        stripped = line.strip()

        # Check if line is indented (starts with space)
        if line and line[0] == ' ':
            # Indented line: only valid for list items or field continuations
            if stripped.startswith("- "):
                # List item under open list key
                if key is None:
                    raise CompileError(f"line {lineno}: list item outside any key")
                item = stripped[2:].strip()
                if ":" in item and not item.startswith(("http://", "https://")):
                    field, _, value = item.partition(":")
                    entry = {field.strip(): _coerce(value)}
                    meta[key].append(entry)
                else:
                    entry = None
                    meta[key].append(_coerce(item))
            elif entry is not None and ":" in stripped:
                # Field continuation in mapping entry
                field, _, value = stripped.partition(":")
                entry[field.strip()] = _coerce(value)
            else:
                # Indented but no valid context
                raise CompileError(f"line {lineno}: unexpected indentation")
        else:
            # Non-indented line: must be key:value
            if ":" not in stripped:
                raise CompileError(f"line {lineno}: expected 'key: value'")
            raw_key, _, raw_value = stripped.partition(":")
            key = raw_key.strip()
            entry = None
            if raw_value.strip() == "":
                meta[key] = []
            else:
                meta[key] = _coerce(raw_value)
                key = None

    return meta, "\n".join(lines[end + 1:])
