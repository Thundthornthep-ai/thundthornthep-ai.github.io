#!/usr/bin/env python3
"""LAS Knowledge Hub content-rules gate (fail closed).

Enforces the owner's article standard where a machine check has no false positives on the published site (system
audit of 17 ตุลาคม 2569, findings G4, CS-3, CS-4, CS-9 and AUTO-02). Scope comes from scripts/las_public_pages.py:
every articles/*.html and en/articles/*.html page plus the blog pages registered as legally reviewed in
learning-hub/legal-reviews.json. Redirect stubs (meta refresh) are skipped. Two rules (CR2, CR5) apply to every
tracked HTML page of the site, because a wrong title or a broken character is wrong on any page.

Rules
  CR1  disclaimer        the page carries a disclaimer block (class *disclaimer* or ข้อสงวนสิทธิ์ / คำสงวนสิทธิ์ /
                         Disclaimer / "not legal advice" text)
  CR2  dr-prefix         no "ดร." (or "Dr.") before the owner's name — the credit is "ธันย์ธรณ์เทพ แย้มอุทัย, Ph.D."
  CR3  credit-form       every credit naming the owner reads "ธันย์ธรณ์เทพ แย้มอุทัย, Ph.D." or
                         "Thundthornthep Yamoutai, Ph.D." (meta keywords and JSON-LD keywords / alternateName are not credits)
  CR4  banned-source     no link to peeseri.com, thailaw.com or deka-online.com
  CR5  replacement-char  no U+FFFD (a corrupted Thai character)
  CR6  deka-flag         no bracketed Supreme Court verification flag ([ต้องยืนยันฎีกา], [ต้องยืนยันเลขคำพิพากษา],
                         [must verify Supreme Court case], [Supreme Court citation to be verified] …); decision R7
                         keeps such flags in drafts only
  CR7  deka-number       every Supreme Court judgment number is in scripts/legal-kb/supreme-court-verified.json
                         (decision R7: unverified numbers are removed, not published)
  CR8  lpa-version       the Labour Protection Act is not presented as amended only to No. 7 B.E. 2562: a page that
                         names that amendment also names No. 9 B.E. 2568, and never calls No. 7 the latest or current
  CR9  section-abbr      "มาตรา" is written in full, never "ม.<number>"
  CR10 month-abbr        Thai months are written in full, never "15 ม.ค. 2569"

Usage
  python3 scripts/validate-content-rules.py                 # whole scope
  python3 scripts/validate-content-rules.py FILE.html ...   # selected pages (all rules that apply to them)
  python3 scripts/validate-content-rules.py --json          # machine-readable report on stdout

Exit 0 when every page passes, 1 when any rule fails, 3 when the scope or the register cannot be read.
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import las_public_pages as pages  # noqa: E402

ROOT = pages.ROOT
DEKA_REGISTER = Path("scripts/legal-kb/supreme-court-verified.json")

THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
SCRIPT_NON_LD = re.compile(r"<script(?![^>]*ld\+json)[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
STYLE = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")
META_KEYWORDS = re.compile(r"<meta[^>]+name\s*=\s*[\"']keywords[\"'][^>]*>", re.IGNORECASE)
ALT_NAME = re.compile(r"\"(?:alternateName|keywords)\"\s*:\s*(?:\"[^\"]*\"|\[[^\]]*\])")

DISCLAIMER_CLASS = re.compile(r"class\s*=\s*[\"'][^\"']*disclaimer", re.IGNORECASE)
DISCLAIMER_TEXT = re.compile(
    r"ข้อสงวนสิทธิ์|คำสงวนสิทธิ์|\bdisclaimer\b|not\s+(?:constitute\s+)?legal\s+advice|does\s+not\s+constitute",
    re.IGNORECASE,
)
DR_PREFIX = re.compile(r"ดร\.\s*ธันย์ธรณ์เทพ|\bDr\.?\s*Thundthornthep", re.IGNORECASE)
OWNER_TH = "ธันย์ธรณ์เทพ แย้มอุทัย"
OWNER_EN = "Thundthornthep Yamoutai"
CREDIT_SUFFIX = ", Ph.D."
BANNED_SOURCE = re.compile(r"(?<=[/.@])(?:peeseri\.com|thailaw\.com|deka-online\.com)\b", re.IGNORECASE)
URL_ATTR = re.compile(r"\b(?:href|src|action|content)\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", re.IGNORECASE)
REPLACEMENT = "�"
# A bracketed draft flag about a Supreme Court judgment: "[ต้องยืนยันฎีกา]", "[ต้องยืนยันเลขคำพิพากษา]",
# "[must verify Supreme Court case]", "[Supreme Court citation to be verified]", "[unconfirmed — Supreme Court …]".
DEKA_FLAG = re.compile(
    r"\[(?=[^\[\]]{0,120}\])(?=[^\[\]]*(?:(?<!กฤษ)ฎีกา|เลขคำพิพากษา|supreme\s+court|\bdika\b))"
    r"(?=[^\[\]]*(?:ยืนยัน|verif|confirm))[^\[\]]*\]",
    re.IGNORECASE,
)
DEKA_NUMBER = re.compile(
    r"(?:(?<!กฤษ)ฎีกา|(?<![\u0E01-\u0E4E.])ฎ\.)\s*(?:ที่|เลขที่)?\s*(\d{1,5}/25\d\d)"
    r"|(?:Supreme\s+Court(?:\s+of\s+Thailand)?(?:'s)?(?:\s+(?:held|ruled|decided))?(?:\s+in)?"
    r"(?:\s+(?:Judgment|Judgement|Decision|Case|Ruling))?|\bDika|\bDeeka)"
    r"\s*(?:No\.?|Number)?\s*(\d{1,5}/25\d\d)",
    re.IGNORECASE,
)
# "Judgment No. 1521/2566" with no court named: a Supreme Court number when the Supreme Court is named shortly before
# or after it. The nouns are those DEKA_NUMBER accepts after "Supreme Court".
BARE_JUDGMENT = re.compile(
    r"(?:\b(?:Judge?ment|Decision|Case|Ruling)\s*(?:No\.?|Number)?|(?:คำพิพากษา|คำวินิจฉัย)\s*(?:ที่|เลขที่))"
    r"\s*(\d{1,5}/25\d\d)",
    re.IGNORECASE,
)
# The court that governs a bare "Judgment No. N/YYYY": one named right after it ("... of the Supreme Court"), else the
# last court named before it, else the first court named after it. Any other court (Constitutional, Administrative,
# Supreme Administrative, Court of Appeal ...) means the number is not the Supreme Court's.
SUPREME_COURT = r"supreme\s+court|\bdika\b|ศาลฎีกา"
OTHER_COURT = (
    r"(?:constitutional|administrative|appeals?|appellate|central|labou?r|tax|bankruptcy|juvenile|civil|criminal|"
    r"provincial|district|military|arbitral)\s+court|court\s+of\s+(?:appeals?|first\s+instance)|tribunal|"
    r"ศาลรัฐธรรมนูญ|ศาลปกครอง|ศาลอุทธรณ์|ศาลแรงงาน|ศาลภาษีอากร|ศาลล้มละลาย|ศาลทรัพย์สินทางปัญญา|ศาลชั้นต้น|"
    r"ศาลแพ่ง|ศาลอาญา"
)
COURT_NAMED = re.compile(r"(?P<other>" + OTHER_COURT + r")|(?P<supreme>" + SUPREME_COURT + r")", re.IGNORECASE)
COURT_RIGHT_AFTER = re.compile(r"^\s*,?\s*(?:(?:of|by|from)\s+(?:the\s+)?|ของ\s*)(?=\S)", re.IGNORECASE)


def governing_court(text: str, start: int, end: int) -> str | None:
    """'supreme', 'other' or None for the judgment number at text[start:end]."""
    after = text[end : end + 200]
    lead = COURT_RIGHT_AFTER.match(after)
    if lead:
        named = COURT_NAMED.match(after, lead.end())
        if named:
            return named.lastgroup
    before = list(COURT_NAMED.finditer(text[max(0, start - 400) : start]))
    if before:
        return before[-1].lastgroup
    named = COURT_NAMED.search(after)
    return named.lastgroup if named else None
LPA_NAMED = re.compile(r"คุ้มครองแรงงาน|labou?r\s+protection|\bLPA\b", re.IGNORECASE)
# Amendment No. 7 named with or without its year (2562 / 2019); counted only near the Act's name (lpa_context).
LPA_NO7 = re.compile(
    r"ฉบับที่\s*7\b(?:\s*\)?\s*(?:พ\.ศ\.\s*)?2562)?|No\.\s*7\b(?:\s*\)?\s*,?\s*(?:B\.E\.\s*)?(?:2562|\(?2019))?",
    re.IGNORECASE,
)
# How far from the Act's name an amendment number may stand and still be read as an amendment of that Act.
LPA_WINDOW = 160
# No. 9 must be named as such: a bare 2568 elsewhere on the page (a date) is not evidence of the amendment.
LPA_NO9 = re.compile(r"ฉบับที่\s*9|No\.\s*9\b", re.IGNORECASE)
LPA_CURRENT = re.compile(
    r"ฉบับล่าสุด|ฉบับปัจจุบัน|ที่ใช้บังคับในปัจจุบัน|latest\s+amendment|most\s+recent\s+amendment|current\s+version",
    re.IGNORECASE,
)
# The Act's name including a following "Act", so "Labour Protection Act Amendment No. 7" leaves no other "Act" between.
LPA_TITLE = re.compile(r"คุ้มครองแรงงาน|labou?r\s+protection(?:\s+act)?|\bLPA\b", re.IGNORECASE)
# Another statute named between the Act and the amendment number takes the number for itself.
OTHER_STATUTE = re.compile(r"พระราชบัญญัติ|พ\.ร\.บ\.|พระราชกำหนด|ประมวล|\b(?:Act|Code|Decree)\b", re.IGNORECASE)
LPA_AFTER = re.compile(
    r"^\s*\)?\s*,?\s*(?:(?:of|to)\s+(?:the\s+)?|ของ\s*|แห่ง\s*)(?:(?:thai\s+)?(?:พระราชบัญญัติ|พ\.ร\.บ\.\s*)?)"
    r"(?:คุ้มครองแรงงาน|labou?r\s+protection|LPA\b)",
    re.IGNORECASE,
)


def lpa_context(text: str, start: int, end: int) -> bool:
    """True when the amendment number at text[start:end] belongs to the Labour Protection Act: the Act is the last
    statute named before it (within LPA_WINDOW characters), or the number is followed by "of the Act" / "ของ…"."""
    before = text[max(0, start - LPA_WINDOW) : start]
    named = list(LPA_TITLE.finditer(before))
    if named and not OTHER_STATUTE.search(before[named[-1].end() :]):
        return True
    return bool(LPA_AFTER.match(text[end : end + LPA_WINDOW]))


SECTION_ABBR = re.compile(r"(?<![ก-๎])ม\.\s?\d")
MONTH_ABBR = re.compile(
    r"\d{1,2}\s*(?:ม\.ค|ก\.พ|มี\.ค|เม\.ย|พ\.ค|มิ\.ย|ก\.ค|ส\.ค|ก\.ย|ต\.ค|พ\.ย|ธ\.ค)\.\s*\d{2,4}"
)

RULES = {
    "CR1": "disclaimer block missing",
    "CR2": "'ดร.' / 'Dr.' before the owner's name",
    "CR3": "owner credit not in the exact form 'ธันย์ธรณ์เทพ แย้มอุทัย, Ph.D.' / 'Thundthornthep Yamoutai, Ph.D.'",
    "CR4": "link to a banned source (peeseri.com, thailaw.com, deka-online.com)",
    "CR5": "U+FFFD replacement character (corrupted text)",
    "CR6": "Supreme Court verification flag on a public page (decision R7)",
    "CR7": "Supreme Court number not in scripts/legal-kb/supreme-court-verified.json (decision R7)",
    "CR8": "Labour Protection Act presented as amended only to No. 7 B.E. 2562",
    "CR9": "abbreviated 'ม.<number>' instead of 'มาตรา'",
    "CR10": "abbreviated Thai month",
}
SITE_WIDE_RULES = ("CR2", "CR5")


def visible_text(raw: str) -> str:
    """Text a reader or a search engine sees: no comments, no code or styles; JSON-LD stays."""
    text = COMMENT.sub(" ", raw)
    text = SCRIPT_NON_LD.sub(" ", text)
    text = STYLE.sub(" ", text)
    text = TAG.sub(" ", text)
    return htmllib.unescape(text).translate(THAI_DIGITS)


def snippet(text: str, start: int, end: int, pad: int = 40) -> str:
    return re.sub(r"\s+", " ", text[max(0, start - pad) : end + pad]).strip()


def load_deka_register(root: Path = ROOT) -> set[str]:
    path = root / DEKA_REGISTER
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data["judgments"]
        numbers = {str(entry["number"]).translate(THAI_DIGITS) for entry in entries if entry.get("status") == "verified"}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(f"Supreme Court register is missing or malformed: {path}: {exc}") from exc
    return numbers


def check_site_wide(raw: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    no_comments = COMMENT.sub(" ", raw)
    # raw markup keeps metadata (meta, JSON-LD) covered; the tag-free text catches a prefix in its own element
    # ("<span>Dr.</span><span>Thundthornthep ...")
    spots = {snippet(no_comments, m.start(), m.end()) for m in DR_PREFIX.finditer(no_comments)}
    shown = htmllib.unescape(TAG.sub(" ", no_comments))
    if not spots and DR_PREFIX.search(shown):
        match = DR_PREFIX.search(shown)
        spots.add(snippet(shown, match.start(), match.end()))
    for spot in sorted(spots):
        found.append(("CR2", spot))
    at = raw.find(REPLACEMENT)
    while at >= 0:
        found.append(("CR5", snippet(raw, at, at + 1)))
        at = raw.find(REPLACEMENT, at + 1)
    return found


def check_article(raw: str, verified: set[str]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    text = visible_text(raw)
    no_comments = COMMENT.sub(" ", raw)

    if not DISCLAIMER_CLASS.search(no_comments) and not DISCLAIMER_TEXT.search(text):
        found.append(("CR1", "no element with a disclaimer class and no disclaimer text"))

    credits = ALT_NAME.sub(" ", META_KEYWORDS.sub(" ", no_comments))
    credits = htmllib.unescape(credits)
    for name in (OWNER_TH, OWNER_EN):
        at = credits.find(name)
        while at >= 0:
            end = at + len(name)
            if not credits.startswith(CREDIT_SUFFIX, end):
                found.append(("CR3", snippet(credits, at, end)))
            at = credits.find(name, end)

    for match in URL_ATTR.finditer(no_comments):
        if BANNED_SOURCE.search(match.group(1)):
            found.append(("CR4", match.group(0)[:160]))
    for match in re.finditer(r"https?://[^\s\"'<>]+", text):
        if BANNED_SOURCE.search(match.group(0)):
            found.append(("CR4", match.group(0)[:160]))

    for match in DEKA_FLAG.finditer(text):
        found.append(("CR6", snippet(text, match.start(), match.end())))
    seen_spans: list[tuple[int, int]] = []
    for match in DEKA_NUMBER.finditer(text):
        number = match.group(1) or match.group(2)
        seen_spans.append(match.span())
        if number not in verified:
            found.append(("CR7", f"{number}: {snippet(text, match.start(), match.end())}"))
    for match in BARE_JUDGMENT.finditer(text):
        if any(start <= match.start() < end for start, end in seen_spans):
            continue
        if governing_court(text, match.start(), match.end()) == "supreme" and match.group(1) not in verified:
            found.append(("CR7", f"{match.group(1)}: {snippet(text, match.start(), match.end())}"))

    if LPA_NAMED.search(text):
        # amendment numbers count only when they stand near the Act's name, so an unrelated statute's
        # "No. 7" or "No. 9" elsewhere on the page neither triggers nor satisfies the rule
        mentions = [m for m in LPA_NO7.finditer(text) if lpa_context(text, m.start(), m.end())]
        has_no9 = any(lpa_context(text, m.start(), m.end()) for m in LPA_NO9.finditer(text))
        if mentions and not has_no9:
            found.append(("CR8", f"names No. 7 but never No. 9: {snippet(text, mentions[0].start(), mentions[0].end())}"))
        for match in mentions:
            window = text[max(0, match.start() - 40) : match.end() + 40]
            if LPA_CURRENT.search(window) and not LPA_NO9.search(window):
                found.append(("CR8", f"No. 7 called current: {snippet(text, match.start(), match.end())}"))

    for match in SECTION_ABBR.finditer(text):
        found.append(("CR9", snippet(text, match.start(), match.end())))
    for match in MONTH_ABBR.finditer(text):
        found.append(("CR10", snippet(text, match.start(), match.end())))
    return found


def check_page(rel: str, root: Path, verified: set[str], article: bool) -> list[tuple[str, str]]:
    raw = (root / rel).read_text(encoding="utf-8", errors="replace")
    found = check_site_wide(raw)
    if article and not pages.is_redirect_stub(raw):
        found.extend(check_article(raw, verified))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", nargs="*", help="pages to check (default: the whole scope)")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)
    root = Path(args.root)
    try:
        verified = load_deka_register(root)
        scope = set(pages.citation_scope(root))
        site = set(pages.tracked(root, "*.html")) if not args.files else set()
    except RuntimeError as exc:
        print(f"[CONTENT-RULES] ERROR: {exc}", file=sys.stderr)
        return 3
    targets = sorted({Path(rel).as_posix() for rel in args.files} or (scope | site))
    report: dict[str, list[tuple[str, str]]] = {}
    for rel in targets:
        if not (root / rel).is_file():
            report[rel] = [("CR0", "file does not exist")]
            continue
        # a named file is classified by its path, so a new untracked article still gets the article rules
        found = check_page(rel, root, verified, article=rel in scope or pages.in_citation_scope(rel, root))
        if found:
            report[rel] = found
    if args.json:
        print(json.dumps({page: [{"rule": rule, "detail": detail} for rule, detail in items]
                          for page, items in report.items()}, ensure_ascii=False, indent=1))
    else:
        for page, items in report.items():
            for rule, detail in items:
                print(f"[{rule}] {page}: {RULES.get(rule, 'missing file')} — {detail}")
        counts: dict[str, int] = {}
        for items in report.values():
            for rule in {rule for rule, _detail in items}:
                counts[rule] = counts.get(rule, 0) + 1
        summary = ", ".join(f"{rule} {counts[rule]}" for rule in sorted(counts, key=lambda r: int(r[2:])))
        print(f"[CONTENT-RULES] pages checked={len(targets)} failing={len(report)}" + (f" ({summary} pages)" if summary else ""))
    if report:
        if not args.json:
            print("[CONTENT-RULES] FAIL — fix the pages or, if a rule is wrong, change the rule with a test", file=sys.stderr)
        return 1
    if not args.json:
        print("[CONTENT-RULES] PASS — all checked pages meet the content rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
