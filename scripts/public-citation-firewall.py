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
to Arabic, ignores HTML outline comments, treats tags and ordinary entities as
separators, and splits slash-lists such as
``มาตรา 36/37`` or ``FBA มาตรา 36 / 37`` into 36 and 37. Plural slash lists
(``Sections 36 / 37``) and plural dash ranges (``Sections 147–166``) are
included; comma lists are not, so unrelated ``Sections 102, 105`` cites stay
out of this release's registry. Dash ranges expand to their endpoints only.
English Constitution titles and Thai ``ประมวลกฎหมาย`` / ``รัฐธรรมนูญ``
names bind as named statutes (or ``unrecognized``), not bare numbers.
``ประกอบรัฐธรรมนูญ`` is the organic-act formula, not a Constitution title.
Inserted sections (``41/1``, ``193/30``) stay one identifier. Securities
``89/*`` inserts stay compound only when the cite is bound as that Act.
Lawquote boxes and lecture cites remain in scope.

Hardening after the system audit of 17 ตุลาคม 2569 (findings G2, G7, F1):

* Non-canonical forms parse like the canonical ones: ``มาตรา9999`` (no space), the abbreviation ``ม.9999``, and the
  English ``Sec. N`` / ``Secs. N–M`` and lower-case ``s. N`` / ``ss. N–M``.
* Comma / "and" lists (``Sections 1012, 1025 and 1064``, ``ss. 41, 71``) bound to a named statute are expanded and
  checked against that statute; an unbound list is still not a registry citation, but it is printed as a REVIEW line.
* Any other section-like text the parser cannot read is reported as UNPARSED and the file exits 4, which
  verify-legal-citations.sh blocks. Exit 2 now means the page has no section-like text at all.
* ``มาตรา N แห่ง / ของ / ตาม พระราชบัญญัติX`` binds X even when X's aliases carry the พระราชบัญญัติ / พ.ร.บ. prefix
  (the longest alias wins, so สถาบันอนุญาโตตุลาการ beats อนุญาโตตุลาการ).
* ``--input`` takes many files (``--batch``): the registry loads once and each file gets a [PASS] / [BLOCK] line.

Exit codes: 0 pass · 1 citation not in the registry · 2 no section-like text · 3 input or registry error ·
4 section-like text could not be parsed.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
HTML_TAG = re.compile(r"<[^>]+>")
SIBLING_GAP = re.compile(
    r"(?P<close></[a-zA-Z][^>]*>)\s*(?P<open><[a-zA-Z][^>]*>)",
    re.IGNORECASE,
)
HARD_CUT = " ·|· "
# ``ม.`` is the abbreviated มาตรา; a Thai letter before it is another word ("กม.01"), so it never starts a cite there.
THAI_SECTION_ABBR = r"(?<![\u0E01-\u0E4E])ม\.(?=\s*\d)"
SECTION_LEAD = re.compile(
    r"^\s*(?:มาตรา|" + THAI_SECTION_ABBR + r"|\bsections?\b|\bsecs?\.|(?-i:\bss?\.)(?=\s*\d))", re.IGNORECASE
)
SECTION_TOKEN_IN = re.compile(
    r"(?:มาตรา|" + THAI_SECTION_ABBR + r"|\bsections?\b|\bsecs?\.|(?-i:\bss?\.)(?=\s*\d))", re.IGNORECASE
)
HTML_ENTITY = re.compile(r"&(?:[a-zA-Z][a-zA-Z0-9]*|#\d+|#x[0-9a-fA-F]+);")
HTML_ENTITIES = {
    "&amp;": "and",
    "&#38;": "and",
    "&mdash;": "—",
    "&ndash;": "–",
    "&#8212;": "—",
    "&#8211;": "–",
    "&nbsp;": " ",
    "&#160;": " ",
    "&quot;": '"',
    "&apos;": "'",
    "&#39;": "'",
    "&lt;": " ",
    "&gt;": " ",
}
# Singular section / มาตรา (no dash ranges — ``มาตรา 32–65`` is not one cite).
# Plural ``Sections`` matches a slash-list or an en/em/ASCII dash range.
# Thai inserted-section suffixes ("มาตรา 32 ทวิ", "มาตรา 19 เตรส") are part of the section identifier; a suffix
# must end the word, so "มาตรา 5 ฉบับ…" or "มาตรา 5 นวัตกรรม" keep the bare number.
THAI_SECTION_SUFFIX = (
    r"(?:\s*(?:ทวาทศ|เอกาทศ|จตุทศ|ปัณรส|โสฬส|สัตตรส|อัฏฐารส|เตรส|จัตวา|เบญจ|สัตต|อัฏฐ|ทวิ|ตรี|นว|ทศ|ฉ)(?![\u0E01-\u0E4E]))?"
)
# Non-canonical forms are parsed too, so the gate cannot fail open on them: ``มาตรา9999`` (no space), the abbreviation
# ``ม.9999`` / ``ม. 40``, and the English ``Sec. N`` / ``Secs. N–M`` and lower-case ``s. N`` / ``ss. N–M`` forms. ``s.``
# and ``ss.`` are case-sensitive so ``U.S. 5`` and sentence ends never read as a section.
SECTION_RE = re.compile(
    r"(?:มาตรา\s*|" + THAI_SECTION_ABBR + r"\s*)(\d+(?:\s*/\s*\d+)?" + THAI_SECTION_SUFFIX + r")"
    r"|(?:\bsections\s+|\bsecs\.\s*|(?-i:\bss\.)\s*)(\d+\s*/\s*\d+(?:\s*/\s*\d+)*|\d+\s*[–—\-]\s*\d+)"
    r"|(?:\bsection\s+|\bsec\.\s*|(?-i:\bs\.)\s*)(\d+(?:\s*/\s*\d+)?)",
    re.IGNORECASE,
)
# Plural comma / "and" lists ("Sections 1012, 1025 and 1064", "ss. 5, 6"). A list bound to a named statute is expanded
# and checked against that statute's registry; an unbound list is not a registry citation (``Sections 102, 105`` may
# number anything) and is reported for review instead of passing silently.
# An item may carry a subsection ("40(1)", "193/14(3)") or a Latin insert suffix ("35 bis"); only its section number is
# checked, as for a singular "Section 35 bis". "A to B" is a range like "A–B"; "Sections 86 et seq." is one citation.
LIST_ITEM = (
    r"\d+(?:/\d+)?(?:\s*\(\d+\))*"
    r"(?:\s+(?:bis|ter|quater|quinquies|sexies|septies|octies|novies|decies)\b)?"
    r"(?:\s*\(\d+\))*(?:\s+para(?:graph)?\.?\s*\d+)?"
)
LIST_SEP = r"(?:\s*,\s*(?:and\s+|or\s+)?|\s+(?:and|or|&|to)\s+|\s*\+\s*|\s*[–—\-]\s*)"
SECTION_LIST_RE = re.compile(
    r"(?:\bsections\s+|\bsecs\.\s*|(?-i:\bss\.)\s*)"
    r"(" + LIST_ITEM + r"(?:" + LIST_SEP + LIST_ITEM + r")+|" + LIST_ITEM + r"\s+et\s+seq\.?)",
    re.IGNORECASE,
)
LIST_ITEM_RE = re.compile(
    r"(\d+(?:/\d+)?)(?:\s*\(\d+\))*"
    r"(?:\s+(?:bis|ter|quater|quinquies|sexies|septies|octies|novies|decies)\b)?"
    r"(?:\s*\(\d+\))*(?:\s+para(?:graph)?\.?\s*\d+)?"
    r"(\s+to\s+|\s*[–—\-]\s*)?",
    re.IGNORECASE,
)
# A singular head followed by bare numbers ("มาตรา 150, 9999", "มาตรา 51 และ 54", "Section 27 or 28") is a list too:
# every number after the head is checked. An item followed by a hyphen, letter or unit ("Section 183, 10-category",
# "มาตรา 5 และ 2 ปี") is not a section and ends the list.
SINGULAR_ID = r"\d+(?:\s*/\s*\d+)?" + THAI_SECTION_SUFFIX
SINGULAR_ITEM = (
    SINGULAR_ID + r"(?:\s+(?:bis|ter|quater|quinquies|sexies|septies|octies|novies|decies)\b)?(?:\s*\(\d+\))*"
)
SINGULAR_ITEM_END = (
    r"(?![\d/\-]|[A-Za-z]|\s*(?:วัน|ปี|เดือน|บาท|คน|ครั้ง|ชั่วโมง|เท่า|%|ร้อยละ)"
    r"|\s+(?:days?|weeks?|months?|years?|hours?|baht|percent|per\s+cent|times|categor(?:y|ies)|items?|persons?|people)\b)"
)
SINGULAR_SEP = r"(?:\s*,\s*(?:and\s+|or\s+|และ\s*|หรือ\s*)?|\s+(?:and|or|&)\s+|\s*(?:และ|หรือ)\s*)"
SINGULAR_LIST_RE = re.compile(
    r"(?:มาตรา\s*|" + THAI_SECTION_ABBR + r"\s*|\bsection\s+|\bsec\.\s*|(?-i:\bs\.)\s*)"
    r"(" + SINGULAR_ITEM + r"(?:" + SINGULAR_SEP + SINGULAR_ITEM + SINGULAR_ITEM_END + r")+)",
    re.IGNORECASE,
)
# the section identifier of one item: its number and Thai insert suffix, without subsections or Latin inserts
SINGULAR_ITEM_RE = re.compile(r"(" + SINGULAR_ID + r")" + SINGULAR_ITEM[len(SINGULAR_ID) :], re.IGNORECASE)
# Anything that looks like a section reference. A match that neither SECTION_RE nor SECTION_LIST_RE consumed is
# "could not parse": the gate reports it and exits 4 instead of treating the page as citation-free.
SECTION_LIKE_RE = re.compile(
    r"มาตรา\s*\d|" + THAI_SECTION_ABBR + r"|\bsec(?:tion)?s?\.?\s*\d|(?-i:\bss?\.)\s*\d",
    re.IGNORECASE,
)
DASH_RANGE_RE = re.compile(r"^(\d+)\s*[–—\-]\s*(\d+)$")
STATUTE_HEADER_RE = re.compile(r"(?im)^statute:\s*([a-z][a-z0-9_-]*)\s*$")
SOURCE_URL_RE = re.compile(r"https?://", re.IGNORECASE)
# Prefix covers ``Personal Data Protection Act B.E. 2562 (2019), Section``.
# Trailing covers ``Section 118 of the Personal Data Protection Act``.
PREFIX_LIMIT = 100
PHRASE_LOOKBACK = PREFIX_LIMIT + 500
TRAILING_LIMIT = 60
UNRECOGNIZED = "unrecognized"
CITATION_GLUE = re.compile(
    r"^(?:\s|[.,;:()\[\]'\"“”‘’/\-–—]|B\.?E\.?|พ\.?ศ\.?|พุทธศักราช|\d+|"
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
# Whole-word Constitution only — not "Constitutional Court".
EN_CONSTITUTION_TITLE = re.compile(
    r"\bConstitution\b(?:\s+of(?:\s+the)?(?:\s+[A-Z][A-Za-z]+)*)?",
    re.IGNORECASE,
)
# ``ประกอบรัฐธรรมนูญ`` is the organic-act formula (NACC, EC, …), not
# a Constitution title. A trailing ``มาตรา 36 ของพระราชบัญญัติประกอบ…``
# cite otherwise truncates into an unknown ``รัฐธรรมนูญ`` name.
TH_NAMED_START = re.compile(
    r"(?:พระราชบัญญัติ|พ\.ร\.บ\.|ประมวลกฎหมาย|(?<!ประกอบ)รัฐธรรมนูญ)(?!นี้|ดังกล่าว)"
)
SKIP_NAMED_HEADS = {"the", "this", "that", "an"}
# Words that may lead a capitalised English title without being part of it: the country, and function words that
# open a sentence or clause ("Under Revenue Code Section 71"). Any other capitalised word belongs to the title.
EN_TITLE_LEADS = {
    "thai", "thailand", "under", "per", "see", "pursuant", "in", "by", "of", "and", "or", "as", "with", "from",
    "according", "a", "an", "the", "this", "that", "its", "their", "both", "each", "also", "while", "where", "when",
    "if", "unlike", "like", "then", "but", "for", "to", "on", "at", "after", "before", "following", "is", "are",
}
NAME_STOP = re.compile(r"\s*(?:พ\.?ศ\.?|B\.?E\.?|มาตรา|\bsection\b|,|$)", re.IGNORECASE)

# Official inserted-section identifiers. Other a/b tokens with both sides >= 10
# are treated as a list of two sections (FBA 36/37, CCC 159/164, PDPA 89/90).
# Securities 89/* compounds are kept only when the bound statute is SEA —
# they are not in this global set, so ``PDPA Sections 89 / 18`` splits.
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
    ("criminal", ("ประมวลกฎหมายอาญา", "criminal code")),
    ("constitution", ("รัฐธรรมนูญแห่งราชอาณาจักรไทย", "constitution of the kingdom of thailand")),
    ("landcode", ("ประมวลกฎหมายที่ดิน", "land code")),
    ("nacc", ("ป้องกันและปราบปรามการทุจริต", "organic act on counter corruption", "ป.ป.ช.", "ปปช.")),
    ("bidrigging", ("เสนอราคาต่อหน่วยงานของรัฐ", "bid rigging act", "anti-bid rigging")),
    ("boi", ("ส่งเสริมการลงทุน", "investment promotion act")),
    ("officialtort", ("ความรับผิดทางละเมิดของเจ้าหน้าที่", "tort liability of government officials act")),
    ("eec", ("เขตพัฒนาพิเศษภาคตะวันออก", "eastern economic corridor act", "eec act")),
    ("condo", ("อาคารชุด", "condominium act")),
    ("hotel", ("พระราชบัญญัติโรงแรม", "พ.ร.บ.โรงแรม", "hotel act")),
    ("adminfines", ("ปรับเป็นพินัย", "administrative fines act")),
    ("plc", ("บริษัทมหาชนจำกัด", "public limited companies act", "public limited company act")),
    ("arbitration", ("อนุญาโตตุลาการ", "arbitration act")),
    ("foreignwork", ("การทำงานของคนต่างด้าว", "foreigners' working act", "foreign workers act")),
    ("ieat", ("การนิคมอุตสาหกรรมแห่งประเทศไทย", "การนิคมอุตสาหกรรม", "industrial estate authority")),
    ("copyright", ("พระราชบัญญัติลิขสิทธิ์", "พ.ร.บ.ลิขสิทธิ์", "copyright act")),
    ("patent", ("พระราชบัญญัติสิทธิบัตร", "พ.ร.บ.สิทธิบัตร", "patent act")),
    ("accounting", ("พระราชบัญญัติการบัญชี", "พ.ร.บ.การบัญชี", "accounting act")),
    ("alcohol", ("ควบคุมเครื่องดื่มแอลกอฮอล์", "alcoholic beverage control act")),
    ("conflictlaws", ("การขัดกันแห่งกฎหมาย", "conflict of laws act")),
    ("socialsecurity", ("พระราชบัญญัติประกันสังคม", "พ.ร.บ.ประกันสังคม", "social security act")),
    ("labourcourt", ("จัดตั้งศาลแรงงาน", "labour court act", "labor court act")),
    ("securities", ("หลักทรัพย์และตลาดหลักทรัพย์", "securities and exchange act")),
    ("computercrime", ("กระทำความผิดเกี่ยวกับคอมพิวเตอร์", "computer crime act", "พ.ร.บ.คอมพิวเตอร์")),
    ("etransactions", ("ธุรกรรมทางอิเล็กทรอนิกส์", "electronic transactions act")),
    ("civilprocedure", ("วิธีพิจารณาความแพ่ง", "ป.วิ.พ.", "civil procedure code")),
    # Owner-supplied OCS consolidated texts (3 October 2026). The Criminal Procedure Code is matched by its full
    # prefixed title or ป.วิ.อ., so "ประมวลกฎหมายอาญา" keeps binding the Criminal Code; the Labour Relations Act only
    # with its พระราชบัญญัติ / พ.ร.บ. prefix, so "คุ้มครองแรงงาน" keeps binding the Labour Protection Act.
    ("criminalprocedure", ("ประมวลกฎหมายวิธีพิจารณาความอาญา", "ป.วิ.อ.", "criminal procedure code")),
    ("lawyers", ("พระราชบัญญัติทนายความ", "พ.ร.บ.ทนายความ", "lawyers act")),
    ("cosmetics", ("พระราชบัญญัติเครื่องสำอาง", "พ.ร.บ.เครื่องสำอาง", "cosmetics act")),
    ("directsales", ("พระราชบัญญัติขายตรงและตลาดแบบตรง", "พ.ร.บ.ขายตรงและตลาดแบบตรง", "พ.ร.บ.ขายตรง",
                     "direct sales and direct marketing act")),
    ("labourrelations", ("พระราชบัญญัติแรงงานสัมพันธ์", "พ.ร.บ.แรงงานสัมพันธ์", "labour relations act")),
    ("mediation", ("การไกล่เกลี่ยข้อพิพาท", "dispute mediation act")),
    # Master plan item 9 (3 October 2026): Acts verified against the Office of the Council of State database. Each
    # alias carries the Act's own title with its พระราชบัญญัติ / พ.ร.บ. prefix, so a phrase that only describes the
    # subject ("กฎหมายว่าด้วยการรับขนของทางทะเลตามมาตรา 609" of the Civil and Commercial Code) never binds.
    ("customs", ("พระราชบัญญัติศุลกากร", "พ.ร.บ.ศุลกากร", "customs act",)),
    ("aircarriage", ("พระราชบัญญัติการรับขนทางอากาศระหว่างประเทศ", "พ.ร.บ.การรับขนทางอากาศระหว่างประเทศ", "international carriage by air act",)),
    ("seacarriage", ("พระราชบัญญัติการรับขนของทางทะเล", "พ.ร.บ.การรับขนของทางทะเล", "carriage of goods by sea act",)),
    ("landtransport", ("พระราชบัญญัติการขนส่งทางบก", "พ.ร.บ.การขนส่งทางบก", "land transport act",)),
    ("warehouse", ("พระราชบัญญัติคลังสินค้า ไซโล และห้องเย็น", "พ.ร.บ.คลังสินค้า ไซโล และห้องเย็น", "warehouses, silos and cold storages act",)),
    ("multimodal", ("พระราชบัญญัติการขนส่งต่อเนื่องหลายรูปแบบ", "พ.ร.บ.การขนส่งต่อเนื่องหลายรูปแบบ", "multimodal transport act",)),
    ("unsafeproducts", ("พระราชบัญญัติความรับผิดต่อความเสียหายที่เกิดขึ้นจากสินค้าที่ไม่ปลอดภัย", "พ.ร.บ.ความรับผิดต่อความเสียหายที่เกิดขึ้นจากสินค้าที่ไม่ปลอดภัย", "liability for damages arising from unsafe products act",)),
    ("factory", ("พระราชบัญญัติโรงงาน", "พ.ร.บ.โรงงาน", "factory act",)),
    ("enqa", ("พระราชบัญญัติส่งเสริมและรักษาคุณภาพสิ่งแวดล้อมแห่งชาติ", "พ.ร.บ.ส่งเสริมและรักษาคุณภาพสิ่งแวดล้อมแห่งชาติ", "national environmental quality act",)),
    ("building", ("พระราชบัญญัติควบคุมอาคาร", "พ.ร.บ.ควบคุมอาคาร", "building control act",)),
    ("minerals", ("พระราชบัญญัติแร่", "พ.ร.บ.แร่", "minerals act",)),
    ("energy", ("พระราชบัญญัติการประกอบกิจการพลังงาน", "พ.ร.บ.การประกอบกิจการพลังงาน", "energy industry act",)),
    ("hazardous", ("พระราชบัญญัติวัตถุอันตราย", "พ.ร.บ.วัตถุอันตราย", "hazardous substance act", "hazardous substances act",)),
    ("forest", ("พระราชบัญญัติป่าสงวนแห่งชาติ", "พ.ร.บ.ป่าสงวนแห่งชาติ", "national reserved forest act",)),
    ("food", ("พระราชบัญญัติอาหาร", "พ.ร.บ.อาหาร", "food act",)),
    ("drug", ("พระราชบัญญัติยา พ.ศ.", "พ.ร.บ.ยา พ.ศ.", "drug act",)),
    ("healthfacility", ("พระราชบัญญัติสถานพยาบาล พ.ศ.", "พ.ร.บ.สถานพยาบาล พ.ศ.", "medical facilities act", "healthcare facilities act",)),
    ("landtax", ("พระราชบัญญัติภาษีที่ดินและสิ่งปลูกสร้าง", "พ.ร.บ.ภาษีที่ดินและสิ่งปลูกสร้าง", "land and building tax act",)),
    ("aml", ("พระราชบัญญัติป้องกันและปราบปรามการฟอกเงิน", "พ.ร.บ.ป้องกันและปราบปรามการฟอกเงิน", "anti-money laundering act",)),
    ("payment", ("พระราชบัญญัติระบบการชำระเงิน", "พ.ร.บ.ระบบการชำระเงิน", "payment systems act",)),
    # The full title runs past the 100-character window before "มาตรา", so the title's own ending binds too
    # ("ความผิดเกี่ยวกับห้างหุ้นส่วนจดทะเบียน … และมูลนิธิ"); the bare list of entity types does not.
    ("partnershipoffences", ("พระราชบัญญัติกำหนดความผิดเกี่ยวกับห้างหุ้นส่วน", "พ.ร.บ.กำหนดความผิดเกี่ยวกับห้างหุ้นส่วน",
                             "ความผิดเกี่ยวกับห้างหุ้นส่วนจดทะเบียน ห้างหุ้นส่วนจำกัด บริษัทจำกัด สมาคม และมูลนิธิ",
                             "พระราชบัญญัติกำหนดความผิดเกี่ยวกับห้างหุ้นส่วนจดทะเบียน ห้างหุ้นส่วนจำกัด บริษัทจำกัด สมาคม และมูลนิธิ",
                             "พ.ร.บ.กำหนดความผิดเกี่ยวกับห้างหุ้นส่วนจดทะเบียน ห้างหุ้นส่วนจำกัด บริษัทจำกัด สมาคม และมูลนิธิ")),
    ("debtcollection", ("พระราชบัญญัติการทวงถามหนี้", "พ.ร.บ.การทวงถามหนี้", "debt collection act",)),
    ("bizsecurity", ("พระราชบัญญัติหลักประกันทางธุรกิจ", "พ.ร.บ.หลักประกันทางธุรกิจ", "business security act",)),
    ("fiinterest", ("พระราชบัญญัติดอกเบี้ยเงินให้กู้ยืมของสถาบันการเงิน", "พ.ร.บ.ดอกเบี้ยเงินให้กู้ยืมของสถาบันการเงิน",)),
    ("commerciallease", ("พระราชบัญญัติการเช่าอสังหาริมทรัพย์เพื่อพาณิชยกรรมและอุตสาหกรรม", "พ.ร.บ.การเช่าอสังหาริมทรัพย์เพื่อพาณิชยกรรมและอุตสาหกรรม",)),
    ("cyber", ("พระราชบัญญัติการรักษาความมั่นคงปลอดภัยไซเบอร์", "พ.ร.บ.การรักษาความมั่นคงปลอดภัยไซเบอร์", "cybersecurity act",)),
    ("procurement", ("พระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ", "พ.ร.บ.การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ", "public procurement and supplies administration act",)),
    ("telecom", ("พระราชบัญญัติการประกอบกิจการโทรคมนาคม", "พ.ร.บ.การประกอบกิจการโทรคมนาคม", "telecommunications business act",)),
    ("securityguard", ("พระราชบัญญัติธุรกิจรักษาความปลอดภัย", "พ.ร.บ.ธุรกิจรักษาความปลอดภัย", "security guard business act",)),
    ("consumercase", ("พระราชบัญญัติวิธีพิจารณาคดีผู้บริโภค", "พ.ร.บ.วิธีพิจารณาคดีผู้บริโภค", "consumer case procedure act",)),
    ("emeeting", ("พระราชกำหนดว่าด้วยการประชุมผ่านสื่ออิเล็กทรอนิกส์", "พ.ร.ก.ว่าด้วยการประชุมผ่านสื่ออิเล็กทรอนิกส์",
                  "พ.ร.ก.การประชุมผ่านสื่ออิเล็กทรอนิกส์", "emergency decree on electronic meetings")),
    # Laws added on 13 October 2026 (LAS Deep Research 176-180), verified against the Office of the Council of State
    # database: the Air Navigation Act with amending Act No. 14 B.E. 2562 merged section by section in las-billing.
    ("airnav", ("พระราชบัญญัติการเดินอากาศ", "พ.ร.บ.การเดินอากาศ", "air navigation act",)),
    ("radio", ("พระราชบัญญัติวิทยุคมนาคม", "พ.ร.บ.วิทยุคมนาคม", "radio communications act", "radiocommunications act",)),
    ("osh", ("พระราชบัญญัติความปลอดภัย อาชีวอนามัย และสภาพแวดล้อมในการทำงาน", "พ.ร.บ.ความปลอดภัย อาชีวอนามัย และสภาพแวดล้อมในการทำงาน",
             "occupational safety, health and environment act",)),
    ("tgo", ("พระราชกฤษฎีกาจัดตั้งองค์การบริหารจัดการก๊าซเรือนกระจก", "พ.ร.ฎ.จัดตั้งองค์การบริหารจัดการก๊าซเรือนกระจก",)),
    ("digitalasset", ("พระราชกำหนดการประกอบธุรกิจสินทรัพย์ดิจิทัล", "พ.ร.ก.การประกอบธุรกิจสินทรัพย์ดิจิทัล",
                      "emergency decree on digital asset businesses",)),
    ("medicaldevice", ("พระราชบัญญัติเครื่องมือแพทย์", "พ.ร.บ.เครื่องมือแพทย์", "medical device act",)),
    # wave audit-2026-11-07 (14 October 2026): Acts imported into the statute corpus (las-billing LOOKUPS.md)
    ("nbtc", ("พระราชบัญญัติองค์กรจัดสรรคลื่นความถี่", "พ.ร.บ.องค์กรจัดสรรคลื่นความถี่", "frequency allocation act",)),
    ("publichealth", ("พระราชบัญญัติการสาธารณสุข", "พ.ร.บ.การสาธารณสุข", "public health act",)),
    ("roadcarriage", ("พระราชบัญญัติการรับขนของทางถนนระหว่างประเทศ", "พ.ร.บ.การรับขนของทางถนนระหว่างประเทศ", "international carriage of goods by road act",)),
    ("wmd", ("พระราชบัญญัติการควบคุมสินค้าที่เกี่ยวข้องกับการแพร่ขยายอาวุธที่มีอานุภาพทำลายล้างสูง", "การแพร่ขยายอาวุธที่มีอานุภาพทำลายล้างสูง", "proliferation of weapons of mass destruction",)),
    ("mediation", ("พระราชบัญญัติการไกล่เกลี่ยข้อพิพาท", "พ.ร.บ.การไกล่เกลี่ยข้อพิพาท", "dispute mediation act",)),
    ("arbinstitute", ("พระราชบัญญัติสถาบันอนุญาโตตุลาการ", "พ.ร.บ.สถาบันอนุญาโตตุลาการ", "arbitration institute act",)),
    ("fiba", ("พระราชบัญญัติธุรกิจสถาบันการเงิน", "พ.ร.บ.ธุรกิจสถาบันการเงิน", "financial institutions businesses act",)),
    ("ukbribery", ("uk bribery act",)),
)


def _looks_like_statute_name(text: str) -> bool:
    if statute_in(text):
        return True
    if TH_NAMED_START.search(text):
        return True
    if EN_CONSTITUTION_TITLE.search(text):
        return True
    return EN_NAMED_STATUTE.search(text) is not None


def _sibling_separator(left: str, right: str) -> str:
    """Join sibling tags that continue a cite; cut when the next pill is unrelated.

    ``<span>ประมวลรัษฎากร</span><span>มาตรา 118</span>`` keeps Revenue scope.
    ``<span>มาตรา 118</span><span>พ.ร.บ.ความลับทางการค้า</span>`` stays a hard cut
    so 118 does not trailing-bind the next statute.
    """
    left = left.strip()
    right = right.strip()
    right_is_section = bool(SECTION_LEAD.match(right))
    left_is_section = bool(SECTION_TOKEN_IN.search(left))
    left_is_statute = _looks_like_statute_name(left)
    right_is_statute = _looks_like_statute_name(right)
    if left_is_statute and right_is_section:
        return " "
    if left_is_section and right_is_section:
        return " "
    if left_is_section and right_is_statute:
        return HARD_CUT
    return HARD_CUT


def _join_or_cut_siblings(text: str) -> str:
    """Replace only the gap between sibling tags so every pair is inspected.

    The previous pair's inner text must not be consumed, or
    ``มาตรา 83`` + ``พ.ร.บ.บริษัทมหาชน`` would skip the hard cut.
    """

    def replace(match: re.Match[str]) -> str:
        start = match.start()
        left_gt = text.rfind(">", 0, start)
        left = text[left_gt + 1 : start] if left_gt >= 0 else text[:start]
        end = match.end()
        right_lt = text.find("<", end)
        right = text[end:right_lt] if right_lt >= 0 else text[end:]
        sep = _sibling_separator(left, right)
        return f"{match.group('close')}{sep}{match.group('open')}"

    return SIBLING_GAP.sub(replace, text)


def prepare_text(text: str) -> str:
    """Normalize published citation text without dropping official recitations.

    Inline wrappers become spaces so ``<strong>PDPA title</strong> &mdash; มาตรา 37``
    still binds. Adjacent sibling tags join when the next element continues the
    citation and become a hard cut when it is a different statute or topic pill.
    """
    text = HTML_COMMENT.sub(" ", text)
    text = _join_or_cut_siblings(text)
    text = HTML_TAG.sub(" ", text)
    for entity, replacement in HTML_ENTITIES.items():
        text = text.replace(entity, replacement)
    text = HTML_ENTITY.sub(" ", text)
    return text.translate(THAI_DIGITS)


def normalize_section_token(token: str) -> str:
    token = re.sub(r"\s*/\s*", "/", token.strip())
    return re.sub(r"(?<=\d)\s*(?=[\u0E01-\u0E4E])", " ", token)


def section_token(match: re.Match[str]) -> str:
    return next(group for group in match.groups() if group is not None)


def expand_section_token(token: str, statute: str | None = None) -> list[str]:
    raw = token.strip()
    dash = DASH_RANGE_RE.fullmatch(raw)
    if dash:
        left, right = int(dash.group(1)), int(dash.group(2))
        if left <= right:
            return [str(number) for number in range(left, right + 1)]
        return [str(left)]
    token = normalize_section_token(token)
    if "/" not in token:
        return [token]
    if token in INSERTED_SECTIONS or token.startswith("193/"):
        return [token]
    if token.startswith("89/") and statute == "securities":
        return [token]
    # The Revenue Code numbers its inserted sections a/b throughout (มาตรา 85/14, 91/10, 91/21): bound to the Code, an
    # a/b token is one section, never a list of two.
    if statute == "revenue":
        return [token]
    # The Bankruptcy Act numbers its business-rehabilitation chapter 90/1 to 90/90 (มาตรา 90/41): one section each.
    if statute == "bankruptcy" and token.startswith("90/"):
        return [token]
    # The Air Navigation Act numbers its inserted sections a/b throughout (มาตรา 15/22, 41/114, 41/125, 60/12, 108/5;
    # the chapters added by Act No. 14 B.E. 2562 and earlier amendments): bound to that Act, an a/b token is one section.
    if statute == "airnav":
        return [token]
    parts = token.split("/")
    if len(parts) >= 2 and all(part.isdigit() and int(part) >= 10 for part in parts):
        return parts
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
    """Citation phrase after the previous section token.

    Only a section token ending inside the last PREFIX_LIMIT characters can shorten the phrase, so the scan starts
    PHRASE_LOOKBACK characters back instead of at the start of the text (the registry files and long pages made the
    full rescan quadratic).
    """
    start = max(0, len(prefix) - PHRASE_LOOKBACK)
    last_end = start
    for match in SECTION_RE.finditer(prefix, start):
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


def _constitution_binds(window: str) -> bool:
    """True when a whole-word Constitution title sits with only citation glue after it."""
    last = None
    for match in EN_CONSTITUTION_TITLE.finditer(window):
        last = match
    if last is None:
        return False
    gap = window[last.end() :]
    return not gap or bool(CITATION_GLUE.match(gap))


def _named_candidates(window: str) -> list[tuple[int, int, str | None]]:
    """Named-statute spans as (start, end, known_key_or_None)."""
    found: list[tuple[int, int, str | None]] = []
    text = window.lower()
    for key, aliases in STATUTE_ALIASES:
        for alias in aliases:
            start = 0
            while True:
                at = text.find(alias, start)
                if at < 0:
                    break
                found.append((at, at + len(alias), key))
                start = at + 1
    for match in EN_NAMED_STATUTE.finditer(window):
        words = match.group(1).split()
        while words and words[0].lower() in SKIP_NAMED_HEADS:
            words.pop(0)
        if not words:
            continue
        found.append((match.start(), match.end(), _en_title_key(words, match.group(2))))
    for match in EN_CONSTITUTION_TITLE.finditer(window):
        found.append((match.start(), match.end(), "constitution"))
    for match in TH_NAMED_START.finditer(window):
        stop = NAME_STOP.search(window, match.end())
        name_end = stop.start() if stop else len(window)
        if name_end - match.end() < 3:
            continue
        name = window[match.end() : name_end]
        if re.match(r"^[\s.]*ฉบับ", name):
            continue
        key = statute_in(window[match.start() : name_end])
        if key is not None:
            continue
        found.append((match.start(), name_end, None))
    return found


def _en_title_key(words: list[str], kind: str) -> str | None:
    """Known key of a capitalised English title only when the whole title is a known one (after leading words in
    EN_TITLE_LEADS), so "Controlled Drug Act" is an unknown Act, not the Drug Act."""
    while words and words[0].lower() in EN_TITLE_LEADS:
        words = words[1:]
    name = " ".join(words + [kind]).lower()
    for key, aliases in STATUTE_ALIASES:
        if any(name == alias or name == f"{alias} {kind.lower()}" for alias in aliases):
            return key
    return None


def _nearest_named(window: str) -> tuple[int, int, str | None] | None:
    """The statute name closest to the section token (rightmost end); at the same end the longer name wins, so a
    known title inside a longer unknown one ("Controlled Drug Act") does not bind."""
    candidates = _named_candidates(window)
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item[1], item[1] - item[0], item[2] is not None))


def prefix_statute(prefix: str) -> str | None:
    window = phrase_before(prefix)
    nearest = _nearest_named(window)
    if nearest is None:
        return None
    _start, end, key = nearest
    gap = window[end:]
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


def _trailing_connective_rest(window: str) -> str:
    """Drop only the of-the / แห่ง / ของ / ตาม connective, keeping a พระราชบัญญัติ / พ.ร.บ. prefix in place."""
    intro = re.match(r"^\s*(?:of(?:\s+the)?|แห่ง|ของ|ตาม)", window, re.IGNORECASE)
    if intro and not window[: intro.end()].isspace():
        return window[intro.end() :]
    return window


ACT_PREFIX_SPACE = re.compile(r"(พ\.ร\.[บกฎ]\.)\s+")


# "พระราชบัญญัตินี้ / ดังกล่าว / เดียวกัน / นั้น" refer back to an Act already named: not a title to match.
ACT_TITLE_LEAD = re.compile(
    r"^\s*(?:พระราชบัญญัติ|พ\.ร\.บ\.|พระราชกำหนด|พ\.ร\.ก\.|พระราชกฤษฎีกา|พ\.ร\.ฎ\.)\s*"
    r"(?!(?:ประกอบรัฐธรรมนูญ\s*)?(?:นี้|ดังกล่าว|เดียวกัน|นั้น))"
)
# The descriptive heads of a Thai Act title before its subject: "พระราชบัญญัติว่าด้วยข้อสัญญาที่ไม่เป็นธรรม",
# "พระราชบัญญัติการแข่งขันทางการค้า", "พระราชบัญญัติประกอบรัฐธรรมนูญว่าด้วยการป้องกันและปราบปรามการทุจริต".
TITLE_SUBJECT_HEAD = re.compile(r"^(?:ประกอบรัฐธรรมนูญ\s*)?(?:ว่าด้วย\s*)?(?:การ(?!นิคม))?")
# What may follow a complete Act title: the end of the phrase, a space, punctuation or a closing bracket, a year, the
# "(ฉบับที่ …)" / พ.ศ. / B.E. glue, the ประกอบ coordination, or one of the few Thai prose words that run on without a
# space and never begin an Act's name ("…ข้อสัญญาที่ไม่เป็นธรรมเป็นหลัก"). Any other letter means the title goes on — a
# different, unrecognised Act ("พระราชบัญญัติลิขสิทธิ์ดิจิทัล", "พระราชบัญญัติคุ้มครองแรงงานทางทะเล").
TITLE_END = re.compile(
    r"(?:$|[\s.,;:()\[\]{}<>'\"“”‘’/\-–—·|…!?]|\d|พ\.?\s?ศ|b\.?\s?e\.|ประกอบ|ฉบับ|เป็น|ซึ่ง|จึง|โดย)",
    re.IGNORECASE,
)


MIN_TRUNCATED_TITLE = 12


def _leading_alias(text: str, *, whole_title: bool = False) -> str | None:
    """Key of the longest alias that starts the text (so สถาบันอนุญาโตตุลาการ beats อนุญาโตตุลาการ).

    With ``whole_title`` (the text is an Act title: พระราชบัญญัติ / พ.ร.บ. …) the alias must end the title — see
    TITLE_END — unless the whole text is the start of an alias (the trailing window is 60 characters, shorter than
    some full titles).
    """
    head = ACT_PREFIX_SPACE.sub(r"\1", text.lstrip()).lower()
    best_key = None
    best_len = 0
    for key, aliases in STATUTE_ALIASES:
        for alias in aliases:
            if len(alias) <= best_len or not head.startswith(alias):
                continue
            if whole_title and not TITLE_END.match(head, len(alias)):
                continue
            best_key = key
            best_len = len(alias)
    if best_key is None and whole_title:
        # The 60-character window can stop inside a long title: the whole remaining text is the start of one alias.
        stem = head.rstrip()
        if len(stem) >= MIN_TRUNCATED_TITLE:
            for key, aliases in STATUTE_ALIASES:
                if any(alias.startswith(stem) for alias in aliases):
                    return key
    return best_key


def _trailing_act_title(after: str) -> str | None:
    """The Act title after an of / แห่ง / ของ / ตาม introducer, or right after the number; None when there is none."""
    window = _trailing_connective_rest(after)
    if window != after and ACT_TITLE_LEAD.match(window):
        return window
    return None



def trailing_statute(trailing: str) -> str | None:
    after = phrase_after(trailing)
    # ``มาตรา 5 แห่งพระราชบัญญัติการบัญชี`` / ``มาตรา 26 แห่ง พ.ร.บ.โรงแรม``: most aliases carry the พระราชบัญญัติ /
    # พ.ร.บ. prefix, so match the window with the prefix kept first, then with it stripped (``คุ้มครองแรงงาน``).
    # Only after an introducer: a bare following word ("มาตรา 150 อาคารชุดที่…") is prose, not the statute's name.
    # A title right after the number with no introducer ("มาตรา 19 พ.ร.บ.การประกอบกิจการพลังงาน") is often the next
    # item of a list, so only the unprefixed aliases bind there, as before.
    title = _trailing_act_title(after)
    if title is not None:
        # An Act title: the alias must be the whole title. The prefix-stripped form is tried too (``แห่งพระราชบัญญัติ
        # คุ้มครองแรงงาน`` binds through the bare ``คุ้มครองแรงงาน`` alias), under the same end-of-title rule, and an
        # Act title that matches no alias never falls through to the looser substring match below.
        key = _leading_alias(title, whole_title=True)
        if key is None:
            stripped = ACT_TITLE_LEAD.sub("", title, count=1)
            key = _leading_alias(stripped, whole_title=True)
            if key is None:
                head = TITLE_SUBJECT_HEAD.match(stripped)
                if head and head.end():
                    key = _leading_alias(stripped[head.end() :], whole_title=True)
        return key
    for window in (_trailing_connective_rest(after), _trailing_rest(after)):
        if window == after:
            continue
        key = _leading_alias(window)
        if key is not None:
            return key
    rest = _trailing_rest(after)
    key = statute_in(rest)
    if key is not None:
        span = _alias_span(rest, key)
        if span is None or span[0] > 0:
            return None
        return key
    stripped = rest.lstrip()
    lead = EN_CONSTITUTION_TITLE.match(stripped)
    if lead is not None:
        return "constitution"
    return None


def _has_unknown_named_statute(window: str) -> bool:
    """Unknown act nearest the section, even if a known alias appears earlier."""
    nearest = _nearest_named(window)
    if nearest is None:
        return False
    _start, end, key = nearest
    gap = window[end:]
    if gap and not CITATION_GLUE.match(gap):
        return False
    return key is None


def unrecognized_named_statute(prefix: str, trailing: str = "") -> bool:
    """True when this citation phrase names an act missing from the alias map."""
    before = phrase_before(prefix)
    if _has_unknown_named_statute(before):
        return True
    after = phrase_after(trailing)
    # ``มาตรา 44 แห่งพระราชบัญญัติลิขสิทธิ์ดิจิทัล``: an Act title after the number that no alias matches as a whole.
    title = _trailing_act_title(after)
    if title is not None and _trailing_rest(after) != after and trailing_statute(trailing) is None:
        return True
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


class Scan:
    """Everything the gate saw in one text: registry citations, unbound lists for review, unparsed tokens."""

    def __init__(self) -> None:
        self.citations: list[tuple[str | None, str]] = []
        self.review_lists: list[str] = []
        self.unparsed: list[str] = []


def _snippet(prepared: str, start: int, end: int) -> str:
    return re.sub(r"\s+", " ", prepared[max(0, start - 30) : end + 30]).strip()


def _list_sections(body: str, statute: str) -> list[str]:
    """Section identifiers of a bound list body; "A to B" / "A–B" between plain numbers expands like a dash range."""
    items = list(LIST_ITEM_RE.finditer(body))
    sections: list[str] = []
    skip_next = False
    for index, item in enumerate(items):
        if skip_next:
            skip_next = False
            continue
        number = item.group(1)
        if item.group(2) and index + 1 < len(items):
            end = items[index + 1].group(1)
            if number.isdigit() and end.isdigit():
                sections.extend(expand_section_token(f"{number}–{end}", statute))
                skip_next = True
                continue
        sections.extend(expand_section_token(number, statute))
    return sections


def scan_text(text: str, *, insert_statute: str | None = None) -> Scan:
    prepared = prepare_text(text)
    result = Scan()
    lists = [match for match in SECTION_LIST_RE.finditer(prepared)]
    plural = {match.start() for match in lists}
    lists += [match for match in SINGULAR_LIST_RE.finditer(prepared) if match.start() not in plural]
    lists.sort(key=lambda match: match.start())
    # A plural slash or dash head ("Sections 193/14(3), 295, 682") is only the start of a longer list: the list owns it.
    owned = {match.start(): match.end() for match in lists}
    result.citations, result.review_lists, covered = _extract_prepared(
        prepared, insert_statute=insert_statute, owned=owned, lists=lists
    )
    for match in SECTION_LIKE_RE.finditer(prepared):
        if not any(start <= match.start() < end for start, end in covered):
            result.unparsed.append(_snippet(prepared, match.start(), match.end()))
    return result


def extract_citations(
    text: str,
    *,
    insert_statute: str | None = None,
) -> list[tuple[str | None, str]]:
    """Registry citations, including comma / and lists bound to a named statute."""
    return scan_text(text, insert_statute=insert_statute).citations


# Between two citation tokens: "and", "or", "และ", "หรือ", "ประกอบ" or a bare comma keeps the statute of the previous
# token — for singular tokens ("Section 36 and Section 37") and for lists ("Sections 213, 41/1 and Sections 9998, 9999").
LIST_COORDINATION = re.compile(r"^\s*(?:,\s*)?(?:and|or|และ|หรือ|ประกอบ|,)\s*$", re.IGNORECASE)


def _extract_prepared(
    prepared: str,
    *,
    insert_statute: str | None = None,
    owned: dict[int, int] | None = None,
    lists: list[re.Match[str]] | None = None,
) -> tuple[list[tuple[str | None, str]], list[str], list[tuple[int, int]]]:
    """Citations, unbound lists for review and the spans consumed, from singular tokens and lists in text order."""
    found: list[tuple[str | None, str]] = []
    review: list[str] = []
    owned = owned or {}
    singles = [match for match in SECTION_RE.finditer(prepared) if owned.get(match.start(), -1) <= match.end()]
    covered = [match.span() for match in singles]
    events: list[tuple[int, str, re.Match[str]]] = [(match.start(), "single", match) for match in singles]
    for match in lists or []:
        if any(start <= match.start() < end for start, end in covered):
            continue
        covered.append(match.span())
        events.append((match.start(), "list", match))
    events.sort(key=lambda event: event[0])
    last_statute: str | None = None
    last_end = 0
    last_kind = ""
    for _start, kind, match in events:
        prefix = prepared[: match.start()]
        trailing = prepared[match.end() : match.end() + TRAILING_LIMIT]
        statute = attached_statute(prefix, trailing)
        if statute is None and last_end:
            if kind == "single" and last_kind == "single":
                coordinated = COORDINATION.match(phrase_before(prefix))
            else:
                coordinated = LIST_COORDINATION.match(prepared[last_end : match.start()])
            if coordinated:
                statute = last_statute
        if statute is None and unrecognized_named_statute(prefix, trailing):
            statute = UNRECOGNIZED
        if kind == "single":
            if statute == "bankruptcy" and "ไม่ใช่บทล้มละลาย" in trailing:
                statute = None
            for section in expand_section_token(section_token(match), statute or insert_statute):
                found.append((statute, section))
        elif match.re is SINGULAR_LIST_RE:
            # each number is read as a singular citation would be: bound to the statute, or unbound like "มาตรา 51"
            for item in SINGULAR_ITEM_RE.finditer(match.group(1)):
                for section in expand_section_token(item.group(1), statute or insert_statute):
                    found.append((statute, section))
        elif statute is None:
            review.append(re.sub(r"\s+", " ", match.group(0)).strip())
        else:
            for section in _list_sections(match.group(1), statute):
                found.append((statute, section))
        last_statute = statute
        last_end = match.end()
        last_kind = kind
    return found, review, covered


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
        sections = {section for _bound, section in extract_citations(text, insert_statute=statute)}
        if not sections:
            raise RuntimeError(f"citation registry {file.name} contains no section identifiers")
        by_statute.setdefault(statute, set()).update(sections)
    if not by_statute:
        raise RuntimeError("citation registry contains no section identifiers")
    return by_statute


# Statutes whose registry was compiled at the level of the base section number, with no consolidated text in the repo
# to check inserted sections against. For these a suffixed citation ("มาตรา 65 ทวิ") resolves on its base number, as
# every citation did before suffixes were kept. Empty since the Revenue Code text arrived (laws/revenue-code-2569.pdf,
# 3 October 2026); add a statute only while its text is missing, and remove it once its suffixed sections are registered.
BASE_NUMBER_STATUTES: set[str] = set()


def section_base(section: str) -> str:
    return section.split(" ", 1)[0]


def resolve_key(statute: str | None, section: str, registry: dict[str, set[str]]) -> str | None:
    if statute:
        if section in registry.get(statute, ()):
            return f"{statute}:{section}"
        if statute in BASE_NUMBER_STATUTES and section_base(section) in {
            section_base(known) for known in registry.get(statute, ())
        }:
            return f"{statute}:{section}"
        return None
    for name, sections in registry.items():
        if section in sections:
            return f"{name}:{section}"
    for name in sorted(BASE_NUMBER_STATUTES & registry.keys()):
        if section_base(section) in {section_base(known) for known in registry[name]}:
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


EXIT_PASS = 0
EXIT_BLOCK = 1
EXIT_NO_CITATION = 2
EXIT_ERROR = 3
# Section-like text ("Sec 5", a form the parser does not know) that was neither checked nor reported as a list. Never a
# pass: verify-legal-citations.sh blocks it like a registry miss.
EXIT_UNPARSED = 4


def check_text(text: str, registry: dict[str, set[str]], out=None, err=None) -> int:
    """Gate one page's text and print the per-citation report. Returns one of the EXIT_* codes."""
    out = out or sys.stdout
    err = err or sys.stderr
    scan = scan_text(text)
    for listed in scan.review_lists:
        print(f"[PUBLIC-CITATION-GATE] REVIEW unbound section list (not registry-checked): {listed}", file=out)
    for snippet in scan.unparsed:
        print(f"[PUBLIC-CITATION-GATE] UNPARSED section-like text: {snippet}", file=err)
    citations = scan.citations
    if not citations:
        if scan.unparsed:
            print("[PUBLIC-CITATION-GATE] FAIL — section-like text could not be parsed", file=err)
            return EXIT_UNPARSED
        if scan.review_lists:
            print(f"[PUBLIC-CITATION-GATE] No registry citations detected; {len(scan.review_lists)} unbound list(s) "
                  "reported for review.", file=out)
        else:
            print("[PUBLIC-CITATION-GATE] No statutory citations detected.", file=out)
        return EXIT_NO_CITATION
    unique_sections = {section for _statute, section in citations}
    missing = sorted(missing_citations(citations, registry), key=_sort_missing)
    print(f"[PUBLIC-CITATION-GATE] citations={len(citations)} unique={len(unique_sections)}", file=out)
    if missing:
        for label in missing:
            print(f"[PUBLIC-CITATION-GATE] BLOCK section {label}: not in official registry", file=err)
        print("[PUBLIC-CITATION-GATE] FAIL — every citation must be registry-backed", file=err)
        return EXIT_BLOCK
    if scan.unparsed:
        print("[PUBLIC-CITATION-GATE] FAIL — section-like text could not be parsed", file=err)
        return EXIT_UNPARSED
    print("[PUBLIC-CITATION-GATE] PASS — all citations are registry-backed", file=out)
    return EXIT_PASS


VERDICTS = {
    EXIT_PASS: "citations verified",
    EXIT_NO_CITATION: "no statutory citation detected",
    EXIT_BLOCK: "firewall exit 1 (citation not in official registry)",
    EXIT_ERROR: "firewall exit 3 (input missing or unreadable)",
    EXIT_UNPARSED: "firewall exit 4 (section-like text could not be parsed)",
}


def run_batch(paths: list[str], registry: dict[str, set[str]]) -> int:
    """Load the registry once and gate every file; print one [PASS]/[BLOCK] verdict per file.

    Returns 0 when every file passes (or has no section-like text at all), otherwise the first failing code.
    """
    first_failure = EXIT_PASS
    blocked = 0
    for name in paths:
        print(f"Checking: {name}", flush=True)
        source = Path(name)
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"[PUBLIC-CITATION-GATE] ERROR: cannot read {source}: {exc}", file=sys.stderr)
            status = EXIT_ERROR
        else:
            status = check_text(text, registry)
        sys.stderr.flush()
        if status in (EXIT_PASS, EXIT_NO_CITATION):
            print(f"[PASS] {name} — {VERDICTS[status]}", flush=True)
            continue
        print(f"[BLOCK] {name} — {VERDICTS[status]}", file=sys.stderr, flush=True)
        blocked += 1
        if first_failure == EXIT_PASS:
            first_failure = status
    print(f"[PUBLIC-CITATION-GATE] files={len(paths)} blocked={blocked}", flush=True)
    return first_failure


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, nargs="+", action="extend",
                        help="one or more HTML files; with more than one (or --batch) the registry loads once")
    parser.add_argument("--kb", required=True)
    parser.add_argument("--mode", default="hard-gate")
    parser.add_argument("--no-pinecone", action="store_true")
    parser.add_argument("--batch", action="store_true", help="print one [PASS]/[BLOCK] verdict line per file")
    args = parser.parse_args()
    if args.mode not in {"hard-gate", "soft-warn", "report"}:
        print(f"[PUBLIC-CITATION-GATE] invalid mode: {args.mode}", file=sys.stderr)
        return 1
    batch = args.batch or len(args.input) > 1
    if not batch:
        source = Path(args.input[0])
        if not source.is_file():
            print(f"[PUBLIC-CITATION-GATE] input is missing: {source}", file=sys.stderr)
            return EXIT_ERROR
    try:
        registry = load_registry(Path(args.kb))
        if not batch:
            text = source.read_text(encoding="utf-8")
    except (OSError, RuntimeError) as exc:
        print(f"[PUBLIC-CITATION-GATE] ERROR: {exc}", file=sys.stderr)
        return EXIT_ERROR
    if batch:
        return run_batch(args.input, registry)
    return check_text(text, registry)


if __name__ == "__main__":
    raise SystemExit(main())
