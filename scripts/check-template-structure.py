#!/usr/bin/env python3
"""LAS Knowledge Hub template-structure report (report-only; fail closed for pages named with --strict).

The owner's article standard (las-billing docs/legal-kb/knowledge-hub/templates/ARTICLE-STANDARD.md section 2,
template v1.0.0 section 7, adopted 29 กันยายน 2569) locks the order and presence of these parts of every article.
This check lists, per page, which of the locked markers it cannot find (system audit of 17 ตุลาคม 2569, finding
TPL-01). The markers are the ones the Drive pipeline (las-billing scripts/legal/md-to-hub-article.mjs) emits, with
the headings and labels that the hand-built pages use for the same parts:

  quick-answer     class "quick-answer" (or short-answer / answer-box), or the label คำตอบโดยย่อ / คำตอบสั้น /
                   Quick Answer / Short Answer
  practice-note    class "practice-note", or the label "Practice Note"
  counterargument  a heading (h2 to h4) or class for the other side's best case: ข้อโต้แย้ง, ข้อต่อสู้, อีกฝ่าย,
                   ฝ่ายตรงข้าม, Counterargument, Counter-Argument, Devil's Advocate, Other Side, Opposing
  faq              class "faq…" (faq-item, faq-section …), or a heading คำถามที่พบบ่อย / FAQ / Frequently Asked
  ref-section      class "ref-section", or a heading แหล่งอ้างอิง / เอกสารอ้างอิง / อ้างอิง / References / Sources
  disclaimer       class "…disclaimer…", or the text ข้อสงวนสิทธิ์ / คำสงวนสิทธิ์ / Disclaimer / "not legal advice"
                   (the same test as content rule CR1)
  table            at least one <table>

Markers are searched with comments, scripts (JSON-LD included) and styles removed, because every page's inline CSS
names ".practice-note" and ".faq-item" whether or not the page has those parts. Redirect stubs are skipped.

Most pages published before the standard lack some parts, so the whole-site run only reports and exits 0. A new or
rewritten page is named with --strict and must carry every marker.

Usage
  python3 scripts/check-template-structure.py                       # report for every article page (exit 0)
  python3 scripts/check-template-structure.py FILE.html ...         # report for the named pages (exit 0)
  python3 scripts/check-template-structure.py --strict FILE.html …  # exit 1 when a named page misses a marker
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

HIDDEN = re.compile(r"<!--.*?-->|<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")
HEADING = re.compile(r"<h([2-4])\b[^>]*>(.*?)</h\1>", re.DOTALL | re.IGNORECASE)


def class_has(pattern: str) -> re.Pattern[str]:
    return re.compile(r"class\s*=\s*[\"'][^\"']*\b(?:" + pattern + r")", re.IGNORECASE)


MARKERS = ("quick-answer", "practice-note", "counterargument", "faq", "ref-section", "disclaimer", "table")
CLASS = {
    "quick-answer": class_has(r"quick-answer|short-answer|answer-box"),
    "practice-note": class_has(r"practice-note"),
    "counterargument": class_has(r"counter-?argument|devil|other-side"),
    "faq": class_has(r"faq"),
    "ref-section": class_has(r"ref-section"),
    "disclaimer": re.compile(r"class\s*=\s*[\"'][^\"']*disclaimer", re.IGNORECASE),
}
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
    "counterargument": re.compile(
        r"ข้อโต้แย้ง|ข้อต่อสู้|อีกฝ่าย|ฝ่ายตรงข้าม|counter-?\s?arguments?|devil'?s\s+advocate|other\s+side|opposing",
        re.IGNORECASE,
    ),
    "faq": re.compile(r"คำถามที่พบบ่อย|\bFAQs?\b|frequently\s+asked", re.IGNORECASE),
    "ref-section": re.compile(r"แหล่งอ้างอิง|เอกสารอ้างอิง|อ้างอิง|\breferences?\b|\bsources\b", re.IGNORECASE),
}
TABLE = re.compile(r"<table\b", re.IGNORECASE)


def body_markup(raw: str) -> str:
    """Markup a reader sees: no comments, scripts (JSON-LD included) or styles."""
    return HIDDEN.sub(" ", raw)


def missing_markers(raw: str) -> list[str]:
    body = body_markup(raw)
    text = htmllib.unescape(TAG.sub(" ", body))
    headings = [htmllib.unescape(TAG.sub(" ", match.group(2))) for match in HEADING.finditer(body)]
    missing: list[str] = []
    for marker in MARKERS:
        if marker == "table":
            found = TABLE.search(body) is not None
        else:
            found = bool(CLASS[marker].search(body))
            if not found and marker in TEXT:
                found = TEXT[marker].search(text) is not None
            if not found and marker in HEAD:
                found = any(HEAD[marker].search(heading) for heading in headings)
        if not found:
            missing.append(marker)
    return missing


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
        missing = missing_markers(raw)
        if missing:
            report[rel] = missing
    failing = [rel for rel in strict if rel in report]
    if args.json:
        print(json.dumps({"checked": checked, "missing": report, "strict_failing": failing},
                         ensure_ascii=False, indent=1))
    else:
        for rel, missing in report.items():
            label = "FAIL" if rel in failing else "REPORT"
            print(f"[{label}] {rel}: missing {', '.join(missing)}")
        counts = {marker: sum(1 for missing in report.values() if marker in missing) for marker in MARKERS}
        summary = ", ".join(f"{marker} {count}" for marker, count in counts.items() if count)
        print(f"[TEMPLATE] pages checked={checked} incomplete={len(report)}" + (f" ({summary})" if summary else ""))
    if failing:
        if not args.json:
            print(f"[TEMPLATE] FAIL — {len(failing)} --strict page(s) miss a locked template part", file=sys.stderr)
        return 1
    if not args.json:
        print("[TEMPLATE] report only — legacy pages are listed, not failed; name new pages with --strict")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
