#!/usr/bin/env python3
"""LAS Knowledge Hub template-structure report (report-only; fail closed for pages named with --strict).

The owner's article standard (las-billing docs/legal-kb/knowledge-hub/templates/ARTICLE-STANDARD.md section 2,
template v1.0.0 section 7, adopted 29 กันยายน 2569) locks the order and presence of these parts of every article.
This check lists, per page, which of the locked markers it cannot find (system audit of 17 ตุลาคม 2569, finding
TPL-01). The markers are the ones the Drive pipeline (las-billing scripts/legal/md-to-hub-article.mjs) emits, with
the headings and labels that the hand-built pages use for the same parts:

  quick-answer     class "quick-answer" (or short-answer / answer-box), or the label คำตอบโดยย่อ / คำตอบสั้น /
                   Quick Answer / Short Answer
  practice-note    class "practice-note", a heading "… Practice Note …", or the label "Practice Note"
  counterargument  a heading (h2 to h4) or class for the other side's best case: ข้อโต้แย้ง, ข้อต่อสู้, อีกฝ่าย,
                   ฝ่ายตรงข้าม, Counterargument, Counter-Argument, Devil's Advocate, Other Side, Opposing
  faq              class "faq…" (faq-item, faq-section …), or a heading คำถามที่พบบ่อย / FAQ / Frequently Asked
  ref-section      class "ref-section", or a heading แหล่งอ้างอิง / เอกสารอ้างอิง / อ้างอิง / References / Sources
  disclaimer       class "…disclaimer…", or the text ข้อสงวนสิทธิ์ / คำสงวนสิทธิ์ / Disclaimer / "not legal advice"
                   (the same test as content rule CR1)
  table            at least one <table>

Markers are searched with comments, scripts (JSON-LD included), styles and <template> contents removed, because every page's inline CSS
names ".practice-note" and ".faq-item" whether or not the page has those parts. A label inside a link (a table of
contents) and a heading of class "sub-heading" name or subdivide a section and do not count as one; one element cannot
count as two sections. Redirect stubs are skipped.

The six section markers (all but the table) must also stand in the locked order: quick-answer, practice-note,
counterargument, faq, ref-section, disclaimer (the references and the disclaimer by their last occurrence, the others by
their first). Most pages published before the standard lack some parts, so the whole-site run only reports and exits 0.
A new or rewritten page is named with --strict and must carry every marker in that order, each by its class or
heading (text labels are accepted only in the report on legacy pages).

Usage
  python3 scripts/check-template-structure.py                       # report for every article page (exit 0)
  python3 scripts/check-template-structure.py FILE.html ...         # report for the named pages (exit 0)
  python3 scripts/check-template-structure.py --strict FILE.html …  # exit 1 when a named page misses a marker or
                                                                    # breaks the order
  python3 scripts/check-template-structure.py --json                # machine-readable report on stdout

Exit 0 when the report ran (and every --strict page is complete), 1 when a --strict page misses a marker or does not
exist, 3 when the scope cannot be read.
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

# comments, scripts and styles are not rendered (nor are <template> contents and hidden elements:
# pages.strip_unrendered); a <textarea> shows its content as text, so markup inside it makes no element
HIDDEN = re.compile(r"<!--.*?-->|<script\b" + pages.TAG_BODY + r">.*?</script\s*>|<style\b" + pages.TAG_BODY + r">.*?</style\s*>"
                    r"|<textarea\b" + pages.TAG_BODY + r">.*?</textarea\s*>",
                    re.DOTALL | re.IGNORECASE)
# tags are read with their quoted attribute values whole, so a ">" inside a value does not end them
TAG = re.compile(r"<[^\s>]" + pages.TAG_BODY + ">")
HEADING = re.compile(r"<h([2-4])\b" + pages.TAG_BODY + r">(.*?)</h\1\s*>", re.DOTALL | re.IGNORECASE)
ENTITY_OR_CHAR = re.compile(r"&(?:#\d+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);|.", re.DOTALL)


def class_has(pattern: str) -> re.Pattern[str]:
    # the name starts a class token ("faq-item", not "no-faq")
    return re.compile(r"(?:" + pattern + r")", re.IGNORECASE)


MARKERS = ("quick-answer", "practice-note", "counterargument", "faq", "ref-section", "disclaimer", "table")
# read against the tokens of an element's own class attribute (pages.class_tokens), so a class written inside another
# attribute's value (data-note="x class=quick-answer") marks nothing (Codex review of PR #80)
CLASS = {
    "quick-answer": class_has(r"quick-answer|short-answer|answer-box"),
    "practice-note": class_has(r"practice-note"),
    "counterargument": class_has(r"counter-?argument|devil|other-side"),
    "faq": class_has(r"faq"),
    "ref-section": class_has(r"ref-section"),
}


def has_class(marker: str, tag_body: str) -> bool:
    tokens = pages.class_tokens(tag_body)
    if marker == "disclaimer":  # any class containing "disclaimer" (las-disclaimer too), as content rule CR1 reads it
        return any("disclaimer" in token for token in tokens)
    return any(CLASS[marker].match(token) for token in tokens)


# label text anywhere in the visible body
TEXT = {
    "quick-answer": re.compile(r"คำตอบโดยย่อ|คำตอบสั้น|\bquick\s+answer\b|\bshort\s+answer\b", re.IGNORECASE),
    "practice-note": re.compile(r"\bpractice\s+note\b", re.IGNORECASE),
    "disclaimer": re.compile(
        r"ข้อสงวนสิทธิ์|คำสงวนสิทธิ์|\bdisclaimer\b|not\s+(?:constitute\s+)?legal\s+advice|does\s+not\s+constitute",
        re.IGNORECASE,
    ),
}
# heading text (h2 to h4): words in running prose ("อีกฝ่ายหนึ่ง" in quoted statute text) do not make a section
HEAD = {
    # a heading that opens with the label ("Quick Answer", "ข้อสงวนสิทธิ์"); one that only mentions it later, such as
    # "LAS Practice Note: … Human-in-the-Loop Disclaimer", is not that section
    "quick-answer": re.compile(r"^\W*(?:คำตอบโดยย่อ|คำตอบสั้น|quick\s+answer\b|short\s+answer\b)", re.IGNORECASE),
    "disclaimer": re.compile(r"^\W*(?:ข้อสงวนสิทธิ์|คำสงวนสิทธิ์|disclaimer\b)", re.IGNORECASE),
    "practice-note": re.compile(r"\bpractice\s+note\b", re.IGNORECASE),
    "counterargument": re.compile(
        r"ข้อโต้แย้ง|ข้อต่อสู้|อีกฝ่าย|ฝ่ายตรงข้าม|counter-?\s?arguments?|devil'?s\s+advocate|other\s+side|opposing",
        re.IGNORECASE,
    ),
    "faq": re.compile(r"คำถามที่พบบ่อย|\bFAQs?\b|frequently\s+asked", re.IGNORECASE),
    "ref-section": re.compile(r"แหล่งอ้างอิง|เอกสารอ้างอิง|อ้างอิง|\breferences?\b|\bsources\b", re.IGNORECASE),
}
TABLE = re.compile(r"<table\b", re.IGNORECASE)


def body_markup(raw: str) -> str:
    """Markup a reader sees: only the <body> (a class in <head> marks nothing, Codex review of PR #80), with no
    comments, scripts (JSON-LD included), styles or <template> contents; comments and scripts go first, so a "<body>"
    inside one does not count as the start of the body."""
    return pages.mask_attribute_markup(pages.strip_unrendered(pages.page_body(HIDDEN.sub(" ", raw))))


untag = pages.untag


def flatten(body: str) -> tuple[str, list[int]]:
    """The visible text of `body` (block tags become spaces, inline tags such as <strong> join their text as the
    browser renders it, entities decoded) and, for every character of it, its offset in `body`, so a label found in the
    text ("Quick <em>Answer</em>", "<strong>คำตอบ</strong>โดยย่อ") has the same position as a class or heading."""
    chars: list[str] = []
    offsets: list[int] = []

    def run(start: int, end: int) -> None:
        # every character keeps its own offset; a decoded entity ("&amp;") maps to where the entity starts
        for unit in ENTITY_OR_CHAR.finditer(body, start, end):
            text = htmllib.unescape(unit.group(0))
            chars.append(text)
            offsets.extend([unit.start()] * len(text))

    pos = 0
    for tag in TAG.finditer(body):
        run(pos, tag.start())
        name = TAG_NAME.match(tag.group(0))
        if not (name and name.group(2).lower() in INLINE):
            chars.append(" ")
            offsets.append(tag.start())
        pos = tag.end()
    run(pos, len(body))
    return "".join(chars), offsets


TAG_NAME = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9-]*)")
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
NAMING = HEADINGS | {"a"}
# inline formatting does not make an element of its own: a label belongs to the nearest block around it
INLINE = pages.INLINE


def enclosing_elements(body: str, points: list[int]) -> dict[int, tuple[int, str, bool, frozenset[int]]]:
    """For each offset in `points`, the start and tag name of the innermost block element of `body` that contains it
    (-1 and "" at top level; inline formatting such as <span> or <strong> is passed over), so a label in running text
    belongs to an element just as a class does; whether any element around it is a link; and the starts of every
    element around it."""
    wanted = sorted(set(points))
    result: dict[int, tuple[int, str, bool, frozenset[int]]] = {}

    def here() -> tuple[int, str, bool, frozenset[int]]:
        in_link = any(name == "a" for name, _ in stack)
        ancestors = frozenset(start for _, start in stack)
        block = next(((name, start) for name, start in reversed(stack) if name not in INLINE), None)
        return (block[1], block[0], in_link, ancestors) if block else (-1, "", in_link, ancestors)

    stack: list[tuple[str, int]] = []
    i = 0
    for tag in TAG.finditer(body):
        while i < len(wanted) and wanted[i] < tag.start():
            result[wanted[i]] = here()
            i += 1
        name = TAG_NAME.match(tag.group(0))
        if not name:
            continue
        closing, tagname = name.group(1) == "/", name.group(2).lower()
        if closing:
            for depth in range(len(stack) - 1, -1, -1):
                if stack[depth][0] == tagname:
                    del stack[depth:]
                    break
        elif not pages.self_closing(tagname, tag.group(0)):
            stack.append((tagname, tag.start()))
    for point in wanted[i:]:
        result[point] = here()
    return result


# The locked order of the sections (ARTICLE-STANDARD section 2). Tables may stand anywhere, so they are not ordered.
# The references and the disclaimer close the page: their last occurrence counts, so a heading such as
# "ตารางสรุปมาตราที่อ้างอิง" in the body or a disclaimer quoted early does not move them; the others count from their
# first occurrence.
ORDER = ("quick-answer", "practice-note", "counterargument", "faq", "ref-section", "disclaimer")
CLOSING = {"ref-section", "disclaimer"}


def marker_hits(
    raw: str, labels: bool = True,
) -> tuple[dict[str, int], dict[str, set[int]], dict[str, set[tuple[int, str]]], dict[str, set[int]]]:
    """For each section marker found on the page, its offset in the visible markup (the first hit, or the last for the
    closing sections), the start of every element that is that section by its class or heading, and the start of the
    innermost element (start and tag name) around each of its text labels outside links, and the starts of every
    element around those labels. Presence, order and the one-element rule all come from here, so every marker that
    counts as present also takes part in the order check. With labels=False (a --strict page) only classes and
    headings count: a label in prose ("read the Practice Note below") names a section without being one, and the Drive
    pipeline gives every locked section its class or heading."""
    body = body_markup(raw)
    text, offsets = flatten(body)
    found: dict[str, int] = {}
    elements: dict[str, set[int]] = {}
    around: dict[str, set[tuple[int, str]]] = {}
    within: dict[str, set[int]] = {}
    for marker in ORDER:
        # a class marker sits at the start of its element, so two sections named in one element share that element
        # a void element (<input type="hidden">, <meta>, <br>) holds no section, whatever its class (Codex review of PR #80)
        owned = [tag.start() for tag in pages.START_TAG.finditer(body)
                 if tag.group(1).lower() not in pages.VOID_TAGS and has_class(marker, tag.group(2))]
        if marker in HEAD:
            # a pipeline sub-heading (h3 class "sub-heading", such as "Claim Ledger (… ข้อต่อสู้ทางกฎหมาย)") is a part
            # of another section, not a section of its own
            owned += [match.start() for match in HEADING.finditer(body)
                      if HEAD[marker].search(htmllib.unescape(untag(match.group(2))))
                      and not any(token.startswith("sub-heading")
                                  for token in pages.class_tokens(pages.START_TAG.match(body, match.start()).group(2)))]
        hits = list(owned)
        if marker in TEXT and labels:
            found_labels = [offsets[match.start()] for match in TEXT[marker].finditer(text)]
            inside = enclosing_elements(body, found_labels)
            # link text only names a section (a table of contents), so it is neither presence nor position
            found_labels = [label for label in found_labels if not inside[label][2]]
            hits += found_labels
            # a label belongs to the innermost element around it (Codex review of PR #80: "Quick Answer and Practice
            # Note" in one element is still one section)
            around[marker] = {inside[label][:2] for label in found_labels if inside[label][0] >= 0}
            # a label inside an element of its own section (div.disclaimer nested in div.ref-section) belongs to it,
            # and a label in a heading names something ("LAS Practice Note: … Disclaimer และ DPA" names a clause)
            within[marker] = set().union(*(inside[label][3] for label in found_labels
                                           if not inside[label][3] & set(owned) and inside[label][1] not in HEADINGS))
        if hits:
            found[marker] = max(hits) if marker in CLOSING else min(hits)
            elements[marker] = set(owned)
    return found, elements, around, within


def marker_positions(raw: str, labels: bool = True) -> dict[str, int]:
    """Offset in the visible markup of each section marker found on the page."""
    return marker_hits(raw, labels)[0]


def missing_markers(raw: str, labels: bool = True) -> list[str]:
    found = marker_positions(raw, labels)
    table = TABLE.search(body_markup(raw)) is not None
    return [marker for marker in MARKERS if not (table if marker == "table" else marker in found)]


def order_problems(raw: str, labels: bool = True) -> list[str]:
    """Pairs of sections that stand in the wrong order, e.g. "out of order: ref-section before quick-answer"."""
    pos, elements, around, within = marker_hits(raw, labels)
    present = [marker for marker in ORDER if marker in pos]
    problems = [f"out of order: {later} before {earlier}" for i, earlier in enumerate(present)
                for later in present[i + 1:] if pos[later] < pos[earlier]]
    # one element cannot be two sections (Codex review of PR #80): compared by element, not by the offset chosen for
    # the order, because class="ref-section disclaimer" shares an element while the two closing offsets may differ. A
    # label counts against an element that is another section by class or heading when it stands anywhere inside it
    # (<div class="quick-answer"><b>Quick Answer</b><span>Practice Note</span></div>); two labels in one heading do not
    # ("LAS Practice Note: … Disclaimer clause").
    # Two labels in one element are one section too (<div>Quick Answer Practice Note</div>), except in a heading or a
    # link, which name sections rather than being them (a table of contents, "LAS Practice Note: … Disclaimer" naming a
    # clause).
    def starts(items: set[tuple[int, str]], prose: bool = True) -> set[int]:
        return {start for start, name in items if prose or name not in NAMING}

    def shared(a: str, b: str) -> bool:
        la, lb = around.get(a, set()), around.get(b, set())
        return bool(elements[a] & (elements[b] | within.get(b, set())) or within.get(a, set()) & elements[b]
                    or starts(la, prose=False) & starts(lb, prose=False))

    problems += [f"one element for two sections: {earlier} and {later}" for i, earlier in enumerate(present)
                 for later in present[i + 1:] if pos[later] == pos[earlier] or shared(earlier, later)]
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", nargs="*", help="pages to report on (default: every article page)")
    parser.add_argument("--strict", nargs="+", default=[], metavar="FILE",
                        help="pages that must carry every marker (new or rewritten articles)")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)
    root = Path(args.root)
    strict = sorted({Path(rel).as_posix() for rel in args.strict})
    try:
        scope = pages.article_pages(root) if not (args.files or strict) else []
    except RuntimeError as exc:
        print(f"[TEMPLATE] ERROR: {exc}", file=sys.stderr)
        return 3
    targets = sorted({Path(rel).as_posix() for rel in args.files} | set(strict) | set(scope))
    report: dict[str, list[str]] = {}
    checked = 0
    for rel in targets:
        path = root / rel
        if not path.is_file():
            report[rel] = ["file does not exist"]
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        if pages.is_redirect_stub(raw):
            continue
        checked += 1
        # a --strict page must show every section by its class or heading; legacy pages are reported with labels
        labels = rel not in strict
        missing = missing_markers(raw, labels) + order_problems(raw, labels)
        if missing:
            report[rel] = missing
    failing = [rel for rel in strict if rel in report]
    if args.json:
        print(json.dumps({"checked": checked, "missing": report, "strict_failing": failing},
                         ensure_ascii=False, indent=1))
    else:
        for rel, missing in report.items():
            label = "FAIL" if rel in failing else "REPORT"
            absent = [item for item in missing if item in MARKERS]
            parts = ([f"missing {', '.join(absent)}"] if absent else []) + [item for item in missing if item not in MARKERS]
            print(f"[{label}] {rel}: {'; '.join(parts)}")
        counts = {marker: sum(1 for missing in report.values() if marker in missing) for marker in MARKERS}
        summary = ", ".join(f"{marker} {count}" for marker, count in counts.items() if count)
        print(f"[TEMPLATE] pages checked={checked} incomplete={len(report)}" + (f" ({summary})" if summary else ""))
    if failing:
        if not args.json:
            print(f"[TEMPLATE] FAIL — {len(failing)} --strict page(s) miss a locked template part or break its order",
                  file=sys.stderr)
        return 1
    if not args.json:
        print("[TEMPLATE] report only — legacy pages are listed, not failed; name new pages with --strict")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
