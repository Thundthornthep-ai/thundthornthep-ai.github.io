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
  CR14 script-title      the strings of js/*.js (tooltip titles and any other text, each concatenation as rendered)
                         write "มาตรา" in full and use neither "vs" nor the retired term
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
# opening tags are read with quoted attribute values whole (pages.TAG_BODY): '<script data-note="1 > 0" …>'
# a script element with its attributes (group 1) and body (group 2); JSON-LD is told apart by its attributes
SCRIPT_ELEMENT = re.compile(r"<script\b(" + pages.TAG_BODY + r")>(.*?)</script\s*>", re.DOTALL | re.IGNORECASE)
STYLE = re.compile(r"<style\b" + pages.TAG_BODY + r">.*?</style\s*>", re.DOTALL | re.IGNORECASE)
TAG = re.compile(r"<[^\s>]" + pages.TAG_BODY + ">")  # quoted attribute values read whole
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
ANY_SCRIPT = re.compile(r"<script\b" + pages.TAG_BODY + r">.*?</script\s*>", re.DOTALL | re.IGNORECASE)
# a class token that starts with "faq" (faq-item; not data-class, not "no-faq")
# a FAQ heading, read with inline tags removed ("<em>คำถาม</em>ที่พบบ่อย", "Frequently <em>Asked</em> Questions")
HEADING_ELEMENT = re.compile(r"<h([2-4])\b" + pages.TAG_BODY + r">(.*?)</h\1\s*>", re.DOTALL | re.IGNORECASE)
FAQ_HEADING_TEXT = re.compile(r"คำถามที่พบบ่อย|\bFAQs?\b|frequently\s+asked", re.IGNORECASE)
# CR12: the standard flag opens a bracket with the words; anywhere else the words are a free-form hedge.
FREE_HEDGE_TH = re.compile(r"ต้องยืนยันมาตรา")
# the standard flag, removed before the search: "[ต้องยืนยันมาตรา]" or "[ต้องยืนยันมาตรา: …]" / "[ต้องยืนยันมาตรา — …]"; a
# bracketed free-form hedge such as "[ต้องยืนยันมาตราที่ถูกต้อง]" is not the flag (Codex review of PR #80)
STANDARD_FLAG_TH = re.compile(r"\[\s*ต้องยืนยันมาตรา(?:\s*[:：–—-][^\]]*)?\s*\]")
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
    r"บริษัท\s+((?:[^\s<>\[\]]+\s+){0,9}?[^\s<>\[\]]+)\s+จำกัด(?=$|[\s()<>,.;:!?\"'“”‘’—–\-ฯ])"
)
# a role is one of the party roles below, not any word starting with ผู้: "บริษัท ผู้ชนะ จำกัด" is an invented trading
# name (Codex review of PR #80)
PARTY_ROLES = (
    "ผู้ว่าจ้าง", "ผู้รับจ้าง", "ผู้ให้บริการ", "ผู้รับบริการ", "ผู้ซื้อ", "ผู้ขาย", "ผู้จะซื้อ", "ผู้จะขาย",
    "ผู้ให้เช่า", "ผู้เช่า", "ผู้ให้เช่าซื้อ", "ผู้เช่าซื้อ", "ผู้ให้กู้", "ผู้กู้", "ผู้ค้ำประกัน", "ผู้รับเหมา",
    "ผู้รับเหมาก่อสร้าง", "ผู้รับเหมาช่วง", "ผู้ลงทุน", "ผู้ร่วมทุน", "ผู้ถือหุ้น", "ผู้ให้อนุญาต", "ผู้รับอนุญาต",
    "ผู้จัดจำหน่าย", "ผู้ผลิต", "ผู้ประกอบการ", "ผู้รับประกันภัย", "ผู้เอาประกันภัย", "ผู้ควบคุมข้อมูลส่วนบุคคล",
    "ผู้ประมวลผลข้อมูลส่วนบุคคล", "ผู้โอน", "ผู้รับโอน", "ผู้จำนอง", "ผู้รับจำนอง", "ผู้จำนำ", "ผู้รับจำนำ",
    "ผู้ให้สิทธิ", "ผู้รับสิทธิ", "ผู้ให้แฟรนไชส์", "ผู้รับแฟรนไชส์", "ผู้พัฒนาโครงการ", "ผู้บริหารโครงการ",
    "ผู้ขนส่ง", "ผู้ส่งสินค้า", "ผู้รับสินค้า", "ผู้นำเข้า", "ผู้ส่งออก", "ผู้ให้สัมปทาน", "ผู้รับสัมปทาน",
)
LETTER_PLACEHOLDER = r"[A-Z]\d{0,2}|[ก-ฮ]|เอ|บี|ซี|ดี|อี|เอฟ|เอกซ์|วาย|แซด|เอบีซี"
# a name ending in a letter placeholder may carry a descriptive word before it ("บริษัท โลจิสติกส์ เอ จำกัด"); a role,
# "มหาชน" or a blank must be the whole name: "บริษัท รุ่งเรือง ผู้รับเหมา จำกัด" is an invented name (Codex review of
# PR #80, round 36)
LETTER_LAST = re.compile(r"^(?:" + LETTER_PLACEHOLDER + r")$")
WHOLE_PLACEHOLDER = re.compile(
    r"^(?:" + LETTER_PLACEHOLDER + r"|มหาชน|\(มหาชน\)|"
    + "|".join(sorted(PARTY_ROLES, key=len, reverse=True)) + r"|[_.…·\-–—]+)$"
)
# the firm's own name and other real names a page may cite as such (add an official name here, with a test)
OFFICIAL_COMPANY_NAMES = frozenset({"Legal Advance Solution"})
# CR14: a quoted title: '…' / title: "…" property in a site script
# CR14 reads every string literal of a site script, with the concatenation it belongs to ('… ' + x + ' …'), wherever
# it stands: an assignment, setAttribute, an object key, a conditional branch (Codex review of PR #80: reading only the
# title forms missed one form after another). Regex literals (/ม\.?\s*291/) and comments are not strings.
# an escape may be a line continuation (a backslash before a newline)
# a template literal may hold ${…} expressions with their own strings, nested template literals included
JS_TEMPLATE_BODY = r"""(?:[^`\\$]|\\[\s\S]|\$(?!\{)|\$\{(?:[^{}`]|`(?:[^`\\]|\\[\s\S])*`|\{[^{}]*\})*\})*"""
JS_LITERAL = r"""(?:'(?:[^'\\\n]|\\[\s\S])*'|"(?:[^"\\\n]|\\[\s\S])*"|`""" + JS_TEMPLATE_BODY + r"""`)"""
# an operand: a name with its member and call suffixes, a number, or a parenthesized expression ('ม.' + (100 + 18))
JS_OPERAND = r"""(?:[A-Za-z_$][\w$.]*(?:\[[^\]\n]*\]|\([^()\n]*(?:\([^()\n]*\)[^()\n]*)*\))*|\d[\w.]*|\([^()\n]*(?:\([^()\n]*\)[^()\n]*)*\))"""
SCRIPT_STRING = re.compile(
    rf"""(?:{JS_OPERAND}\s*\+\s*)?{JS_LITERAL}(?:\s*\+\s*(?:{JS_LITERAL}|{JS_OPERAND}))*"""
)
SCRIPT_LITERAL = re.compile(r"""'((?:[^'\\\n]|\\[\s\S])*)'|"((?:[^"\\\n]|\\[\s\S])*)"|`(""" + JS_TEMPLATE_BODY + r""")`""")
def template_expressions(text: str) -> list[str]:
    """The source of each ${…} expression of a template literal's body (nested braces included)."""
    found: list[str] = []
    i = 0
    while i < len(text):
        if text.startswith("${", i):
            depth, j = 1, i + 2
            while j < len(text) and depth:
                depth += {"{": 1, "}": -1}.get(text[j], 0)
                j += 1
            found.append(text[i + 2:j - 1])
            i = j
        else:
            i += 1
    return found


def template_static(text: str) -> str:
    """The static text of a template literal, each ${…} expression (nested braces included) read as a digit, so
    "ม.${n}" is the abbreviation it renders as."""
    out: list[str] = []
    i = 0
    while i < len(text):
        if text.startswith("${", i):
            depth, j = 1, i + 2
            while j < len(text) and depth:
                depth += {"{": 1, "}": -1}.get(text[j], 0)
                j += 1
            out.append("0")
            i = j
        else:
            out.append(text[i])
            i += 1
    return "".join(out)
# JavaScript string escapes, decoded as the browser renders them ('ม.\x31' is "ม.1")
JS_ESCAPE = re.compile(r"\\(?:x([0-9A-Fa-f]{2})|u([0-9A-Fa-f]{4})|u\{([0-9A-Fa-f]{1,6})\}|(.))", re.DOTALL)
JS_SIMPLE = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0", "\n": ""}


def js_unescape(text: str) -> str:
    def one(match: re.Match[str]) -> str:
        code = match.group(1) or match.group(2) or match.group(3)
        if code:
            value = int(code, 16)
            return chr(value) if value <= 0x10FFFF else ""
        return JS_SIMPLE.get(match.group(4), match.group(4))
    return JS_ESCAPE.sub(one, text)
# "vs" as a word, whatever follows it ("vs ", "vs.", "(vs.)", "vs/B")
SCRIPT_TITLE_BANNED = re.compile(r"(?<![ก-๎])ม\.\s?\d|(?<![A-Za-z])vs(?![A-Za-z])|หนี้ลำพัง", re.IGNORECASE)

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
    text = SCRIPT_ELEMENT.sub(lambda m: m.group(0) if is_ld_json(m) else " ", text)
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
    """Text a reader sees on the page: no comments, no scripts (JSON-LD included), no styles, no <template> contents;
    whitespace collapsed."""
    # inert <template> contents are never rendered (they are left in the markup the citation rules read)
    text = pages.strip_unrendered(ANY_SCRIPT.sub(" ", COMMENT.sub(" ", raw)))
    text = TAG.sub(" ", STYLE.sub(" ", text))
    return re.sub(r"\s+", " ", htmllib.unescape(text).translate(THAI_DIGITS)).strip()


FAQ_TYPE = re.compile(r"(?:https?://schema\.org/|schema:)?FAQPage")


def is_faq_type(kind) -> bool:
    """FAQPage as a compact term or its full IRI ("https://schema.org/FAQPage", "schema:FAQPage")."""
    return isinstance(kind, str) and FAQ_TYPE.fullmatch(kind.strip()) is not None


def _faq_pages(node):
    if isinstance(node, dict):
        kind = node.get("@type")
        kinds = kind if isinstance(kind, list) else [kind]
        if any(is_faq_type(item) for item in kinds):
            yield node
        for value in node.values():
            yield from _faq_pages(value)
    elif isinstance(node, list):
        for value in node:
            yield from _faq_pages(value)


page_body = pages.page_body


def is_ld_json(script: re.Match[str]) -> bool:
    # the script's own decoded type attribute, not "ld+json" anywhere in the tag (data-note="ld+json"), and
    # type="application/ld&#43;json" counts (Codex review of PR #80)
    return pages.attributes(script.group(1)).get("type", "").strip().lower() == "application/ld+json"


def faq_objects(raw: str) -> list[dict]:
    """Every FAQPage object in the page's JSON-LD (a block that does not parse is skipped)."""
    found: list[dict] = []
    for block in (m.group(2) for m in SCRIPT_ELEMENT.finditer(COMMENT.sub(" ", raw)) if is_ld_json(m)):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        found.extend(_faq_pages(data))
    return found


def faq_questions(raw: str, faqs: list[dict] | None = None) -> list[str]:
    """Question names of every FAQPage object in the page's JSON-LD."""
    names: list[str] = []
    for faq in faq_objects(raw) if faqs is None else faqs:
        entities = faq.get("mainEntity") or []
        for question in entities if isinstance(entities, list) else [entities]:
            if isinstance(question, dict) and isinstance(question.get("name"), str):
                name = re.sub(r"\s+", " ", htmllib.unescape(question["name"]).translate(THAI_DIGITS)).strip()
                if name:
                    names.append(name)
    return names


def check_faq(raw: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(CR11 failures, W11 warnings) for the page's FAQPage JSON-LD."""
    faqs = faq_objects(raw)
    if not faqs:
        return [], []
    # an FAQPage with no named question is never a FAQ the reader sees, whatever other FAQPage objects hold
    # (Codex review of PR #80)
    if any(not faq_questions(raw, [faq]) for faq in faqs):
        return [("CR11", "FAQPage JSON-LD with no named question")], []
    questions = faq_questions(raw, faqs)
    # whitespace is ignored on both sides: a tag inside a question ("What is a <em>lease</em>?") becomes a space in
    # the reader text, and Thai text has no word spaces to lose
    # only the page body is read: a <title> that repeats a question is not a FAQ (Codex review of PR #80)
    # comments, scripts and styles go before the body start is looked for, so a "<body>" in a head comment does not
    # start the body (Codex review of PR #80)
    shown = re.sub(r"\s+", "", reader_text(page_body(STYLE.sub(" ", ANY_SCRIPT.sub(" ", COMMENT.sub(" ", raw))))))
    hidden = [question for question in questions if re.sub(r"\s+", "", question) not in shown]
    # the FAQ section is looked for in the body only: <html class="faq-page"> is no FAQ section (Codex review of PR #80)
    # markup written inside an attribute value (title="<h2>FAQ</h2>") is no heading
    markup = pages.mask_attribute_markup(
        pages.strip_unrendered(page_body(STYLE.sub(" ", ANY_SCRIPT.sub(" ", COMMENT.sub(" ", raw))))))
    # a FAQ class is a token of an element's own class attribute starting with "faq" ("faq-item", not "no-faq"), not
    # text inside another attribute's value (title="x class=faq-item"; Codex review of PR #80)
    # (a void element such as <input class="faq"> holds no section)
    has_section = bool(any(token.startswith("faq") for tag in pages.START_TAG.finditer(markup)
                           if tag.group(1).lower() not in pages.VOID_TAGS
                           for token in pages.class_tokens(tag.group(2))) or any(
        FAQ_HEADING_TEXT.search(htmllib.unescape(pages.untag(heading.group(2))))
        for heading in HEADING_ELEMENT.finditer(markup)))
    if len(hidden) == len(questions) and not has_section:
        return [("CR11", f"{len(questions)} FAQPage question(s), none visible and no FAQ section: {questions[0][:80]}")], []
    return [], [("W11", question[:120]) for question in hidden]


def company_name_allowed(name: str) -> bool:
    # the name is what follows the last "บริษัท" of the match: "เอกชน / บริษัท มหาชน" and "ข้อเท็จจริงสมมติ: บริษัท A"
    # (a match that starts at an earlier "บริษัท" with no "จำกัด" of its own) name "มหาชน" and "A"
    name = name.rsplit("บริษัท", 1)[-1].strip()
    if not name:
        return False
    if name in OFFICIAL_COMPANY_NAMES or WHOLE_PLACEHOLDER.match(name):
        return True
    return LETTER_LAST.match(name.split()[-1]) is not None


def check_warnings(raw: str) -> list[tuple[str, str]]:
    """Report-only findings (W11, W12) for an article page."""
    warnings = check_faq(raw)[1]
    shown = reader_text(raw)
    flags = [match.span() for match in STANDARD_FLAG_EN.finditer(shown)]
    for match in FREE_HEDGE_EN.finditer(shown):
        if not any(start <= match.start() < end for start, end in flags):
            warnings.append(("W12", snippet(shown, match.start(), match.end())))
    return warnings


REGEX_PREFIX = re.compile(r"(?:^|[(,=:\[!&|?{};+\-*%~^<>]|\breturn|\btypeof)\s*$")


def regex_may_start(before: str) -> bool:
    return REGEX_PREFIX.search(before[-40:]) is not None


def regex_end(raw: str, start: int) -> int:
    """The end of the regex literal opening at `start` (its flags included), or 0 when it does not close on its line."""
    j, in_class = start + 1, False
    while j < len(raw):
        c = raw[j]
        if c == "\\":
            j += 2
            continue
        if c == "\n":
            return 0
        if in_class:
            in_class = c != "]"
        elif c == "[":
            in_class = True
        elif c == "/":
            j += 1
            while j < len(raw) and raw[j].isalpha():
                j += 1
            return j
        j += 1
    return 0


def strip_js_comments(raw: str) -> str:
    """The script with its // and /* */ comments and its regex literals (/"A vs B"/, /มาตรา\\s*291/) blanked, leaving
    string literals alone ('https://…' is neither). A "/" starts a regex where an expression may begin (after "(", ",",
    "=", ":", an operator, a bracket or "return"); elsewhere it is division. A regex that does not close on its line is
    left as it is (fail closed)."""
    out: list[str] = []
    i, n, quote = 0, len(raw), ""
    while i < n:
        ch = raw[i]
        if quote:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                out.append(raw[i + 1])
                i += 2
                continue
            if ch == quote or (ch == "\n" and quote != "`"):
                quote = ""
        elif ch in "'\"`":
            quote = ch
            out.append(ch)
        elif raw.startswith("//", i) and (i == 0 or raw[i - 1] != "\\"):
            end = raw.find("\n", i)
            end = n if end < 0 else end
            out.append(" " * (end - i))
            i = end
            continue
        elif raw.startswith("/*", i):
            end = raw.find("*/", i + 2)
            end = n if end < 0 else end + 2
            out.append("".join(c if c == "\n" else " " for c in raw[i:end]))
            i = end
            continue
        elif ch == "/" and regex_may_start("".join(out)):
            end = regex_end(raw, i)
            if end:
                out.append(" " * (end - i))
                i = end
                continue
            out.append(ch)
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def concatenation_text(value: str) -> str:
    """The text a concatenated title renders: each literal's static text, and each non-literal operand ('ม.' + n)
    read as a digit, as a ${…} expression is."""
    pieces: list[str] = []
    pos = 0
    for literal in SCRIPT_LITERAL.finditer(value):
        if re.sub(r"[\s+()]", "", value[pos:literal.start()]):
            pieces.append("0")
        pieces.append(js_unescape(template_static(next(part for part in literal.groups() if part is not None))))
        pos = literal.end()
    if re.sub(r"[\s+()]", "", value[pos:]):
        pieces.append("0")
    return "".join(pieces)


def check_script(raw: str) -> list[tuple[str, str]]:
    """CR14 for a site script: banned forms in its strings, as rendered (regex patterns and comments are not strings)."""
    found: list[tuple[str, str]] = []
    for match in SCRIPT_STRING.finditer(strip_js_comments(raw)):
        title = concatenation_text(match.group(0))
        if SCRIPT_TITLE_BANNED.search(title):
            found.append(("CR14", title[:160]))
        # the strings inside a template literal's expressions render too: `${`ม.118`}` (Codex review of PR #80)
        for literal in SCRIPT_LITERAL.finditer(match.group(0)):
            if literal.group(3) is not None:
                for expression in template_expressions(literal.group(3)):
                    found.extend(check_script(expression))
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
    unflagged = STANDARD_FLAG_TH.sub(lambda flag: " " * len(flag.group(0)), shown)
    for match in FREE_HEDGE_TH.finditer(unflagged):
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
