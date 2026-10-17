#!/usr/bin/env python3
"""LAS Knowledge Hub content-rules gate (fail closed).

Enforces the owner's article standard where a machine check has no false positives on the published site (system
audit of 17 ตุลาคม 2569, findings G4, CS-3, CS-4, CS-9 and AUTO-02; R70 findings TPL-05, TPL-06, TPL-07 and VF-3).
Scope comes from scripts/las_public_pages.py: every articles/*.html and en/articles/*.html page plus the blog pages
registered as legally reviewed in learning-hub/legal-reviews.json. Redirect stubs (meta refresh) are skipped. Two rules
(CR2, CR5) apply to every tracked HTML page of the site, because a wrong title or a broken character is wrong on any
page. CR14 applies to the tracked js/*.js files, whose tooltip titles readers see on the article pages.

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
  CR11 faq-hidden        a page with FAQPage JSON-LD shows a FAQ: a visible FAQ section (class "faq…" or a heading
                         คำถามที่พบบ่อย / FAQ / Frequently Asked) or at least one of the questions in the visible text
                         (template v1.0.0 sections 7.1 and 7.17: FAQPage only for a FAQ the reader sees)
  CR12 free-hedge        no free-form Thai section hedge ("… ต้องยืนยันมาตราที่ถูกต้อง …"): an unchecked section is marked
                         only with the standard flag "[ต้องยืนยันมาตรา]" / "[ต้องยืนยันมาตรา: …]", and a section the corpus
                         answers is looked up at once (owner rule, 13 ตุลาคม 2569)
  CR13 company-name      worked examples name companies by role or letter ("บริษัท A จำกัด (ผู้รับเหมาก่อสร้าง)"), never
                         an invented trading name that may match a real company ("บริษัท ก่อสร้างมั่นคง จำกัด")
  CR14 script-title      tooltip titles in js/*.js write "มาตรา" in full and use neither "vs" nor the retired term
                         "หนี้ลำพัง" (terminology.json: หนี้ส่วนตัว)

Warnings (printed, never failing; promote to a rule once the pages are clean)
  W11  faq-parity        a FAQPage question whose exact wording is not in the visible text of a page that has a FAQ
  W12  free-hedge-en     a free-form English section hedge ("section to be verified", "provisions to be confirmed")
                         outside the standard "[unconfirmed — …]" / "[must verify section number]" flag

Usage
  python3 scripts/validate-content-rules.py                 # whole scope
  python3 scripts/validate-content-rules.py FILE.html ...   # selected pages (all rules that apply to them); js/*.js: CR14
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

# FAQPage JSON-LD and what the reader sees (CR11, W11). Reader text drops every script, JSON-LD included.
LD_JSON = re.compile(r"<script[^>]*ld\+json[^>]*>(.*?)</script>", re.DOTALL | re.IGNORECASE)
ANY_SCRIPT = re.compile(r"<script\b[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
FAQ_CLASS = re.compile(r"class\s*=\s*[\"'][^\"']*\bfaq", re.IGNORECASE)
FAQ_HEADING = re.compile(r"<h[2-4]\b[^>]*>(?:(?!</h[2-4]>).)*?(?:คำถามที่พบบ่อย|\bFAQs?\b|frequently\s+asked)",
                         re.DOTALL | re.IGNORECASE)
# CR12: the standard flag opens a bracket with the words; anywhere else the words are a free-form hedge.
FREE_HEDGE_TH = re.compile(r"(?<!\[)(?<!\[ )ต้องยืนยันมาตรา")
STANDARD_FLAG_EN = re.compile(r"\[\s*(?:unconfirmed\b|must\s+verify\b)[^\[\]]*\]", re.IGNORECASE)
FREE_HEDGE_EN = re.compile(
    r"\b(?:section|paragraph|sub-paragraph|provision|chapter|number)s?(?:\s+(?:number|numbering)s?)?\s+"
    r"(?:is\s+|are\s+)?(?:still\s+)?(?:to\s+be|needs?\s+to\s+be|must\s+be)\s+(?:verified|confirmed)\b"
    r"|\bverify\s+the\s+(?:correct|exact)\s+section",
    re.IGNORECASE,
)
# CR13: "บริษัท <name> จำกัด" written with spaces, as a company name is (a name of up to ten words: the check reads the
# page as plain text, so an unbounded name would run on across sentences to a later "จำกัด"). A name passes when its last word is a letter
# placeholder (A, B, ก, เอ, เอบีซี …), a blank (____, ……), a role (ผู้ว่าจ้าง), "มหาชน", or an official name below.
COMPANY_NAME = re.compile(
    r"บริษัท\s+((?:[^\s<>\[\]]+\s+){0,9}?[^\s<>\[\]]+)\s+จำกัด(?=$|[\s()<>,.;:!?\"'“”‘’—–-])"
)
NAME_PLACEHOLDER = re.compile(
    r"^(?:[A-Z]\d{0,2}|[ก-ฮ]|เอ|บี|ซี|ดี|อี|เอฟ|เอกซ์|วาย|แซด|เอบีซี|มหาชน|\(มหาชน\)|ผู้\S+|[_.…·\-–—]+)$"
)
# the firm's own name and other real names a page may cite as such (add an official name here, with a test)
OFFICIAL_COMPANY_NAMES = frozenset({"Legal Advance Solution"})
# CR14: a quoted title: '…' / title: "…" property in a site script
SCRIPT_TITLE = re.compile(r"\btitle\s*:\s*(?:'((?:[^'\\\n]|\\.)*)'|\"((?:[^\"\\\n]|\\.)*)\")")
SCRIPT_TITLE_BANNED = re.compile(r"(?<![ก-๎])ม\.\s?\d|\bvs\.?(?=\s)|หนี้ลำพัง")

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
    "CR11": "FAQPage JSON-LD but no FAQ the reader can see (remove the block or show the FAQ word for word)",
    "CR12": "free-form section hedge instead of a lookup or the standard flag '[ต้องยืนยันมาตรา]'",
    "CR13": "invented company name in an example (use a role or A, B, C: 'บริษัท A จำกัด (ผู้รับเหมาก่อสร้าง)')",
    "CR14": "tooltip title in a site script uses 'ม.<number>', 'vs' or 'หนี้ลำพัง'",
    "W11": "FAQPage question not shown word for word on the page",
    "W12": "free-form English section hedge outside the standard '[unconfirmed — …]' flag",
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


def reader_text(raw: str) -> str:
    """Text a reader sees on the page: no comments, no scripts (JSON-LD included), no styles; whitespace collapsed."""
    text = ANY_SCRIPT.sub(" ", COMMENT.sub(" ", raw))
    text = TAG.sub(" ", STYLE.sub(" ", text))
    return re.sub(r"\s+", " ", htmllib.unescape(text).translate(THAI_DIGITS)).strip()


def _faq_pages(node):
    if isinstance(node, dict):
        kind = node.get("@type")
        if kind == "FAQPage" or (isinstance(kind, list) and "FAQPage" in kind):
            yield node
        for value in node.values():
            yield from _faq_pages(value)
    elif isinstance(node, list):
        for value in node:
            yield from _faq_pages(value)


def faq_questions(raw: str) -> list[str]:
    """Question names of every FAQPage object in the page's JSON-LD (a block that does not parse is skipped)."""
    names: list[str] = []
    for block in LD_JSON.findall(COMMENT.sub(" ", raw)):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for faq in _faq_pages(data):
            entities = faq.get("mainEntity") or []
            for question in entities if isinstance(entities, list) else [entities]:
                if isinstance(question, dict) and isinstance(question.get("name"), str):
                    name = re.sub(r"\s+", " ", htmllib.unescape(question["name"]).translate(THAI_DIGITS)).strip()
                    if name:
                        names.append(name)
    return names


def check_faq(raw: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(CR11 failures, W11 warnings) for the page's FAQPage JSON-LD."""
    questions = faq_questions(raw)
    if not questions:
        return [], []
    shown = reader_text(raw)
    hidden = [question for question in questions if question not in shown]
    markup = STYLE.sub(" ", ANY_SCRIPT.sub(" ", COMMENT.sub(" ", raw)))
    has_section = bool(FAQ_CLASS.search(markup) or FAQ_HEADING.search(markup))
    if len(hidden) == len(questions) and not has_section:
        return [("CR11", f"{len(questions)} FAQPage question(s), none visible and no FAQ section: {questions[0][:80]}")], []
    return [], [("W11", question[:120]) for question in hidden]


def company_name_allowed(name: str) -> bool:
    if name in OFFICIAL_COMPANY_NAMES:
        return True
    return NAME_PLACEHOLDER.match(name.split()[-1]) is not None


def check_warnings(raw: str) -> list[tuple[str, str]]:
    """Report-only findings (W11, W12) for an article page."""
    warnings = check_faq(raw)[1]
    shown = reader_text(raw)
    flags = [match.span() for match in STANDARD_FLAG_EN.finditer(shown)]
    for match in FREE_HEDGE_EN.finditer(shown):
        if not any(start <= match.start() < end for start, end in flags):
            warnings.append(("W12", snippet(shown, match.start(), match.end())))
    return warnings


def check_script(raw: str) -> list[tuple[str, str]]:
    """CR14 for a site script: banned forms in its title strings (patterns and comments are not titles)."""
    found: list[tuple[str, str]] = []
    for match in SCRIPT_TITLE.finditer(raw):
        title = match.group(1) if match.group(1) is not None else match.group(2)
        if SCRIPT_TITLE_BANNED.search(title):
            found.append(("CR14", title[:160]))
    return found


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

    found.extend(check_faq(raw)[0])
    shown = reader_text(raw)
    for match in FREE_HEDGE_TH.finditer(shown):
        found.append(("CR12", snippet(shown, match.start(), match.end(), pad=80)))
    for match in COMPANY_NAME.finditer(shown):
        if not company_name_allowed(match.group(1)):
            found.append(("CR13", f"{match.group(0)}: {snippet(shown, match.start(), match.end(), pad=30)}"))
    return found


def check_page(rel: str, root: Path, verified: set[str], article: bool,
               warnings: dict[str, list[tuple[str, str]]] | None = None) -> list[tuple[str, str]]:
    raw = (root / rel).read_text(encoding="utf-8", errors="replace")
    if rel.endswith(".js"):
        return check_script(raw)
    found = check_site_wide(raw)
    if article and not pages.is_redirect_stub(raw):
        found.extend(check_article(raw, verified))
        if warnings is not None:
            noted = check_warnings(raw)
            if noted:
                warnings[rel] = noted
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
        site = set(pages.tracked(root, "*.html", "js/*.js")) if not args.files else set()
    except RuntimeError as exc:
        print(f"[CONTENT-RULES] ERROR: {exc}", file=sys.stderr)
        return 3
    targets = sorted({Path(rel).as_posix() for rel in args.files} or (scope | site))
    report: dict[str, list[tuple[str, str]]] = {}
    warnings: dict[str, list[tuple[str, str]]] = {}
    for rel in targets:
        if not (root / rel).is_file():
            report[rel] = [("CR0", "file does not exist")]
            continue
        # a named file is classified by its path, so a new untracked article still gets the article rules
        found = check_page(rel, root, verified, article=rel in scope or pages.in_citation_scope(rel, root),
                           warnings=warnings)
        if found:
            report[rel] = found
    if args.json:
        print(json.dumps({page: [{"rule": rule, "detail": detail} for rule, detail in items]
                          for page, items in report.items()}, ensure_ascii=False, indent=1))
    else:
        for page, items in warnings.items():
            for rule, detail in items:
                print(f"[WARN {rule}] {page}: {RULES[rule]} — {detail}")
        if warnings:
            noted = {rule for items in warnings.values() for rule, _detail in items}
            print(f"[CONTENT-RULES] warnings (report only): "
                  + ", ".join(f"{rule} {sum(1 for items in warnings.values() if any(r == rule for r, _ in items))} pages"
                              for rule in sorted(noted)))
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
