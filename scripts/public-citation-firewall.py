#!/usr/bin/env python3
"""Public, release-scoped LAS citation gate.

This verifier checks that every statutory section cited by a public article is
present in the release's official-source registry. When the surrounding phrase
names a statute, the section must be registered under that statute — so
``PDPA Section 118`` does not pass on Labour Protection Act 118. A named
statute that is not in the alias map is blocked instead of falling back to
any registry number. Bare lecture numbers still pass if any official
statute file lists them. Amendment clauses and coordinated
``Section 36 and Section 37`` forms keep the same statute.

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
PREFIX_LIMIT = 100
TRAILING_LIMIT = 60
UNRECOGNIZED = "unrecognized"
CITATION_GLUE = re.compile(
    r"^(?:\s|[.,;:()\[\]'\"“”‘’/-]|B\.?E\.?|พ\.?ศ\.?|\d+|"
    r"แก้ไขเพิ่มเติม(?:โดย)?|ฉบับที่|as\s+amended(?:\s+by)?|amendment|"
    r"no\.?|and|of|the|under|ตาม)+$",
    re.IGNORECASE,
)
COORDINATION = re.compile(
    r"^\s*(?:and|or|และ|หรือ|ประกอบ)\s*$",
    re.IGNORECASE,
)
EN_NAMED_STATUTE = re.compile(
    r"\b((?:[A-Z][A-Za-z]+(?:-[A-Z][A-Za-z]+)*)"
    r"(?:\s+[A-Z][A-Za-z]+(?:-[A-Z][A-Za-z]+)*)*)\s+(Act|Code)\b"
)
TH_NAMED_START = re.compile(r"(?:พระราชบัญญัติ|พ\.ร\.บ\.)(?!นี้|ดังกล่าว)")
SKIP_NAMED_HEADS = {"the", "this", "that", "an"}
NAME_STOP = re.compile(r"\s*(?:พ\.?ศ\.?|B\.?E\.?|มาตรา|\bsection\b|,|$)", re.IGNORECASE)

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
    ("pdpa", ("คุ้มครองข้อมูลส่วนบุคคล", "คุ้มครองข้อมูล", "personal data protection act", "pdpa")),
    ("lpa", ("คุ้มครองแรงงาน", "labour protection act", "labor protection act")),
    ("ucta", ("ข้อสัญญาที่ไม่เป็นธรรม", "unfair contract terms")),
    ("fba", ("ประกอบธุรกิจของคนต่างด้าว", "ธุรกิจต่างด้าว", "foreign business act", "fba")),
    ("tradesecrets", ("ความลับทางการค้า", "trade secrets act")),
    ("revenue", ("ประมวลรัษฎากร", "revenue code")),
    ("competition", ("แข่งขันทางการค้า", "trade competition act")),
    ("bankruptcy", ("พระราชบัญญัติล้มละลาย", "bankruptcy act")),
    ("trademark", ("เครื่องหมายการค้า", "trademark act")),
    ("consumer", ("คุ้มครองผู้บริโภค", "consumer protection act")),
    ("ccc", ("ประมวลกฎหมายแพ่งและพาณิชย์", "ประมวลกฎหมายแพ่ง", "ป.พ.พ.", "ปพพ.", "tccc", "civil and commercial code", "thai civil code", "civil code")),
    ("landcode", ("ประมวลกฎหมายที่ดิน", "land code")),
    ("nacc", ("ป้องกันและปราบปรามการทุจริต", "organic act on counter corruption", "ป.ป.ช.", "ปปช.")),
    ("bidrigging", ("เสนอราคาต่อหน่วยงานของรัฐ", "bid rigging act", "anti-bid rigging")),
    ("boi", ("ส่งเสริมการลงทุน", "investment promotion act")),
    ("officialtort", ("ความรับผิดทางละเมิดของเจ้าหน้าที่", "tort liability of government officials act")),
    ("eec", ("เขตพัฒนาพิเศษภาคตะวันออก", "eastern economic corridor act", "eec act")),
    ("condo", ("อาคารชุด", "condominium act")),
    ("hotel", ("พระราชบัญญัติโรงแรม", "hotel act")),
    ("adminfines", ("ปรับเป็นพินัย", "administrative fines act")),
    ("plc", ("บริษัทมหาชนจำกัด", "public limited companies act", "public limited company act")),
    ("arbitration", ("อนุญาโตตุลาการ", "arbitration act")),
    ("foreignwork", ("การทำงานของคนต่างด้าว", "foreigners' working act", "foreign workers act")),
    ("ieat", ("การนิคมอุตสาหกรรม", "industrial estate authority")),
    ("copyright", ("พระราชบัญญัติลิขสิทธิ์", "copyright act")),
    ("labourcourt", ("จัดตั้งศาลแรงงาน", "labour court act", "labor court act")),
    ("securities", ("หลักทรัพย์และตลาดหลักทรัพย์", "securities and exchange act")),
    ("computercrime", ("กระทำความผิดเกี่ยวกับคอมพิวเตอร์", "computer crime act", "พ.ร.บ.คอมพิวเตอร์")),
    ("etransactions", ("ธุรกรรมทางอิเล็กทรอนิกส์", "electronic transactions act")),
    ("civilprocedure", ("วิธีพิจารณาความแพ่ง", "civil procedure code")),
    ("mediation", ("การไกล่เกลี่ยข้อพิพาท", "dispute mediation act")),
    ("ukbribery", ("uk bribery act",)),
)


def prepare_text(text: str) -> str:
    """Normalize published citation text without dropping official recitations."""
    return (
        HTML_COMMENT.sub(" ", text)
        .replace("&amp;", "and")
        .replace("&#38;", "and")
        .translate(THAI_DIGITS)
    )


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
    gap = window[span[1] :]
    if gap and not CITATION_GLUE.match(gap):
        return None
    return key


def _trailing_rest(window: str) -> str:
    """Drop of-the-Act / แห่งพระราชบัญญัติ introducers before the alias."""
    intro = re.match(
        r"^\s*(?:(?:of(?:\s+the)?|แห่ง|ของ|ตาม)\s*(?:พระราชบัญญัติ|พ\.ร\.บ\.)?"
        r"|(?:พระราชบัญญัติ|พ\.ร\.บ\.))",
        window,
        re.IGNORECASE,
    )
    if intro and intro.end() > 0 and not window[: intro.end()].isspace():
        return window[intro.end() :]
    return window


def trailing_statute(trailing: str) -> str | None:
    rest = _trailing_rest(phrase_after(trailing))
    key = statute_in(rest)
    if key is None:
        return None
    span = _alias_span(rest, key)
    if span is None or span[0] > 0:
        return None
    return key


def _has_unknown_named_statute(window: str) -> bool:
    """Unknown act name whose remaining gap to the section is citation glue only."""
    if statute_in(window):
        return False
    for match in EN_NAMED_STATUTE.finditer(window):
        if match.group(1).split()[0].lower() in SKIP_NAMED_HEADS:
            continue
        gap = window[match.end() :]
        if not gap or CITATION_GLUE.match(gap):
            return True
    for match in TH_NAMED_START.finditer(window):
        stop = NAME_STOP.search(window, match.end())
        name_end = stop.start() if stop else len(window)
        if name_end - match.end() < 3:
            continue
        name = window[match.end() : name_end]
        if re.match(r"^[\s.]*ฉบับ", name):
            continue
        gap = window[name_end:]
        if not gap or CITATION_GLUE.match(gap):
            return True
    return False


def unrecognized_named_statute(prefix: str, trailing: str = "") -> bool:
    """True when this citation phrase names an act missing from the alias map."""
    before = phrase_before(prefix)
    if _has_unknown_named_statute(before):
        return True
    after = phrase_after(trailing)
    rest = _trailing_rest(after)
    if rest == after:
        return False
    return _has_unknown_named_statute(rest)


def attached_statute(prefix: str, trailing: str = "") -> str | None:
    """Bind a statute when its name sits immediately before or after this token.

    A prior ``มาตรา`` / ``section`` cuts the prefix so
    ``ปพพ. มาตรา 577 + มาตรา 118`` does not mark 118 as CCC. Trailing names
    such as ``Section 118 of the Personal Data Protection Act`` still bind.
    A later act in the same sentence does not. Amendment-year glue and
    ``and`` / ``ประกอบ`` coordination keep the same statute. A named act
    that is missing from the alias map is ``unrecognized``, not bare.
    """
    return prefix_statute(prefix) or trailing_statute(trailing)


def extract_citations(text: str) -> list[tuple[str | None, str]]:
    prepared = prepare_text(text)
    found: list[tuple[str | None, str]] = []
    last_statute: str | None = None
    for match in SECTION_RE.finditer(prepared):
        prefix = prepared[: match.start()]
        trailing = prepared[match.end() : match.end() + TRAILING_LIMIT]
        statute = attached_statute(prefix, trailing)
        if statute is None and COORDINATION.match(phrase_before(prefix)):
            statute = last_statute
        if statute is None and unrecognized_named_statute(prefix, trailing):
            statute = UNRECOGNIZED
        if statute == "bankruptcy" and "ไม่ใช่บทล้มละลาย" in trailing:
            statute = None
        for section in expand_section_token(section_token(match)):
            found.append((statute, section))
            last_statute = statute
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
