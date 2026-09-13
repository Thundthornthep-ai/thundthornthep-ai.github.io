#!/usr/bin/env python3
"""Public, release-scoped LAS citation gate.

This verifier checks that every statutory section cited by a public article is
present in the release's official-source registry. When the surrounding phrase
names a statute, the section must be registered under that statute — so
``PDPA Section 118`` does not pass on Labour Protection Act 118. Bare lecture
numbers still pass if any official statute file lists them.

It stores no private source text. A missing verifier, missing registry,
malformed file, unmatched citation, or named-statute mismatch is a hard failure.

Official PDF lawquote boxes use Thai numerals. The gate normalizes Thai digits
to Arabic, ignores HTML outline comments, and splits slash-lists such as
``มาตรา 36/37`` or ``FBA มาตรา 36 / 37`` into 36 and 37. Plural slash lists
(``Sections 36 / 37``) are included; comma lists are not, so unrelated
``Sections 102, 105`` cites stay out of this release's registry. Inserted
sections (``41/1``, ``193/30``) stay one identifier. Lawquote boxes and
lecture cites remain in scope.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# Singular section / มาตรา, plus plural only when it is a slash-list.
SECTION_RE = re.compile(
    r"(?:มาตรา|\bsection)\s+(\d+(?:\s*/\s*\d+)?)|\bsections\s+(\d+\s*/\s*\d+)",
    re.IGNORECASE,
)
STATUTE_HEADER_RE = re.compile(r"(?im)^statute:\s*([a-z][a-z0-9_-]*)\s*$")
SOURCE_URL_RE = re.compile(r"https?://", re.IGNORECASE)
# Prefix covers ``Personal Data Protection Act B.E. 2562 (2019), Section``.
# Trailing covers ``Section 118 of the Personal Data Protection Act``.
PREFIX_LIMIT = 80
TRAILING_LIMIT = 60
# `` B.E. 2562 (2019), `` sits between the act name and Section.
PREFIX_ALIAS_GAP = 24
# `` of the `` / ``พ.ร.บ.`` sit between the number and a trailing act name.
TRAILING_ALIAS_AT = 9

# Official inserted-section identifiers. Other a/b tokens with both sides >= 10
# are treated as a list of two sections (FBA 36/37, CCC 159/164).
INSERTED_SECTIONS = {
    "4/1",
    "23/1",
    "41/1",
    "59/1",
    "59/2",
    "81/1",
    "85/1",
    "91/2",
    "1111/1",
    "681/1",
    "685/1",
}

# Longer aliases first so PDPA wins over a bare "คุ้มครอง" and LPA over "แรงงาน".
STATUTE_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pdpa", ("คุ้มครองข้อมูลส่วนบุคคล", "personal data protection act", "pdpa")),
    ("lpa", ("คุ้มครองแรงงาน", "labour protection act", "labor protection act")),
    ("ucta", ("ข้อสัญญาที่ไม่เป็นธรรม", "unfair contract terms")),
    ("fba", ("ประกอบธุรกิจของคนต่างด้าว", "foreign business act", "fba")),
    ("revenue", ("ประมวลรัษฎากร", "revenue code")),
    ("competition", ("แข่งขันทางการค้า", "trade competition act")),
    ("bankruptcy", ("พระราชบัญญัติล้มละลาย", "bankruptcy act")),
    ("trademark", ("เครื่องหมายการค้า", "trademark act")),
    ("consumer", ("คุ้มครองผู้บริโภค", "consumer protection act")),
    ("ccc", ("ประมวลกฎหมายแพ่งและพาณิชย์", "ประมวลกฎหมายแพ่ง", "ป.พ.พ.", "ปพพ.", "tccc", "civil and commercial code")),
)


def prepare_text(text: str) -> str:
    """Normalize published citation text without dropping official recitations."""
    return HTML_COMMENT.sub(" ", text).translate(THAI_DIGITS)


def normalize_section_token(token: str) -> str:
    return re.sub(r"\s*/\s*", "/", token.strip())


def section_token(match: re.Match[str]) -> str:
    return next(group for group in match.groups() if group is not None)


def expand_section_token(token: str) -> list[str]:
    token = normalize_section_token(token)
    if "/" not in token:
        return [token]
    if token in INSERTED_SECTIONS or token.startswith("193/"):
        return [token]
    left, right = token.split("/", 1)
    if left.isdigit() and right.isdigit() and int(left) >= 10 and int(right) >= 10:
        return [left, right]
    return [token]


def statute_in(window: str) -> str | None:
    text = window.lower()
    best_key = None
    best_at = -1
    for key, aliases in STATUTE_ALIASES:
        for alias in aliases:
            found = text.rfind(alias)
            if found > best_at:
                best_at = found
                best_key = key
    return best_key


def phrase_before(prefix: str) -> str:
    """Citation phrase after the previous section token."""
    last_end = 0
    for match in SECTION_RE.finditer(prefix):
        last_end = match.end()
    return prefix[last_end:][-PREFIX_LIMIT:]


def phrase_after(trailing: str) -> str:
    """Immediate trailing phrase, cut at the next section token."""
    nxt = SECTION_RE.search(trailing)
    window = trailing[: nxt.start()] if nxt else trailing
    return window[:TRAILING_LIMIT]


def _alias_span(window: str, key: str) -> tuple[int, int] | None:
    text = window.lower()
    start = -1
    end = -1
    for name, aliases in STATUTE_ALIASES:
        if name != key:
            continue
        for alias in aliases:
            found = text.rfind(alias)
            if found > start:
                start = found
                end = found + len(alias)
    if start < 0:
        return None
    return start, end


def prefix_statute(prefix: str) -> str | None:
    window = phrase_before(prefix)
    key = statute_in(window)
    if key is None:
        return None
    span = _alias_span(window, key)
    if span is None:
        return None
    if len(window) - span[1] > PREFIX_ALIAS_GAP:
        return None
    return key


def trailing_statute(trailing: str) -> str | None:
    window = phrase_after(trailing)
    key = statute_in(window)
    if key is None:
        return None
    span = _alias_span(window, key)
    if span is None or span[0] > TRAILING_ALIAS_AT:
        return None
    return key


def attached_statute(prefix: str, trailing: str = "") -> str | None:
    """Bind a statute when its name sits immediately before or after this token.

    A prior ``มาตรา`` / ``section`` cuts the prefix so
    ``ปพพ. มาตรา 577 + มาตรา 118`` does not mark 118 as CCC. Trailing names
    such as ``Section 118 of the Personal Data Protection Act`` still bind.
    A later act in the same sentence does not.
    """
    return prefix_statute(prefix) or trailing_statute(trailing)


def extract_citations(text: str) -> list[tuple[str | None, str]]:
    prepared = prepare_text(text)
    found: list[tuple[str | None, str]] = []
    for match in SECTION_RE.finditer(prepared):
        trailing = prepared[match.end() : match.end() + TRAILING_LIMIT]
        statute = attached_statute(prepared[: match.start()], trailing)
        if statute == "bankruptcy" and "ไม่ใช่บทล้มละลาย" in trailing:
            statute = None
        for section in expand_section_token(section_token(match)):
            found.append((statute, section))
    return found


def cited_sections(text: str) -> list[str]:
    """Section numbers only — used by tests and the number-level view."""
    return [section for _statute, section in extract_citations(text)]


def load_registry(path: Path) -> dict[str, set[str]]:
    """Return {statute: {section, ...}} from Markdown files that declare statute:."""
    if not path.is_dir():
        raise RuntimeError(f"citation registry is missing: {path}")
    files = sorted(path.glob("*.md"))
    if not files:
        raise RuntimeError(f"citation registry has no Markdown files: {path}")
    by_statute: dict[str, set[str]] = {}
    for file in files:
        try:
            text = file.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"cannot read citation registry {file}: {exc}") from exc
        if not SOURCE_URL_RE.search(text):
            raise RuntimeError(f"citation registry {file.name} contains no official source URL")
        header = STATUTE_HEADER_RE.search(text)
        if not header:
            raise RuntimeError(f"citation registry {file.name} is missing a 'statute:' key")
        statute = header.group(1)
        sections = {section for _bound, section in extract_citations(text)}
        if not sections:
            raise RuntimeError(f"citation registry {file.name} contains no section identifiers")
        by_statute.setdefault(statute, set()).update(sections)
    if not by_statute:
        raise RuntimeError("citation registry contains no section identifiers")
    return by_statute


def resolve_key(statute: str | None, section: str, registry: dict[str, set[str]]) -> str | None:
    if statute:
        if section in registry.get(statute, ()):
            return f"{statute}:{section}"
        return None
    for name, sections in registry.items():
        if section in sections:
            return f"{name}:{section}"
    return None


def missing_citations(
    citations: list[tuple[str | None, str]],
    registry: dict[str, set[str]],
) -> list[str]:
    missing: list[str] = []
    seen: set[str] = set()
    for statute, section in citations:
        if resolve_key(statute, section, registry):
            continue
        if statute:
            label = f"{statute}:{section}"
        else:
            owners = sorted(name for name, sections in registry.items() if section in sections)
            if owners:
                label = f"{section} (ambiguous; registered under {', '.join(owners)})"
            else:
                label = section
        if label not in seen:
            seen.add(label)
            missing.append(label)
    return missing


def _sort_missing(label: str) -> tuple[int, str]:
    number = re.search(r"(\d+)", label)
    return (int(number.group(1)) if number else 0, label)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--kb", required=True)
    parser.add_argument("--mode", default="hard-gate")
    parser.add_argument("--no-pinecone", action="store_true")
    args = parser.parse_args()
    if args.mode not in {"hard-gate", "soft-warn", "report"}:
        print(f"[PUBLIC-CITATION-GATE] invalid mode: {args.mode}", file=sys.stderr)
        return 1
    source = Path(args.input)
    if not source.is_file():
        print(f"[PUBLIC-CITATION-GATE] input is missing: {source}", file=sys.stderr)
        return 3
    try:
        text = source.read_text(encoding="utf-8")
        registry = load_registry(Path(args.kb))
    except (OSError, RuntimeError) as exc:
        print(f"[PUBLIC-CITATION-GATE] ERROR: {exc}", file=sys.stderr)
        return 3
    citations = extract_citations(text)
    if not citations:
        print("[PUBLIC-CITATION-GATE] No statutory citations detected.")
        return 2
    unique_sections = {section for _statute, section in citations}
    missing = sorted(missing_citations(citations, registry), key=_sort_missing)
    print(f"[PUBLIC-CITATION-GATE] citations={len(citations)} unique={len(unique_sections)}")
    if missing:
        for label in missing:
            print(f"[PUBLIC-CITATION-GATE] BLOCK section {label}: not in official registry", file=sys.stderr)
        print("[PUBLIC-CITATION-GATE] FAIL — every citation must be registry-backed", file=sys.stderr)
        return 1
    print("[PUBLIC-CITATION-GATE] PASS — all citations are registry-backed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
