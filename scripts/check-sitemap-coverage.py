#!/usr/bin/env python3
"""Sitemap coverage gate for the LAS Knowledge Hub (fail closed).

Every public article — each articles/*.html and en/articles/*.html page and each reviewed blog page in
learning-hub/legal-reviews.json that is neither a redirect stub (meta refresh) nor marked noindex — must have a
<loc> in sitemap.xml (system audit of 17 ตุลาคม 2569, findings SS-06 and AUTO-06). The gate does not edit the
sitemap; it lists what is missing. Sitemap entries that point at a missing file, a redirect stub or a noindex page
are reported as warnings (they are not article-scope errors and do not fail the gate).

Usage
  python3 scripts/check-sitemap-coverage.py [--sitemap sitemap.xml]

Exit 0 when every public article is listed, 1 when any is missing, 3 when the sitemap or scope cannot be read.
"""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import las_public_pages as pages  # noqa: E402

ROOT = pages.ROOT
SITE_HOST = "thundthornthep-ai.github.io"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def sitemap_paths(path: Path) -> list[str]:
    """Repository paths of the sitemap's <loc> entries on this site ('/' and 'x/' become index.html)."""
    try:
        tree = ET.parse(path)
    except (OSError, ET.ParseError) as exc:
        raise RuntimeError(f"cannot read sitemap {path}: {exc}") from exc
    found: list[str] = []
    for loc in tree.getroot().iterfind("sm:url/sm:loc", NS):
        url = (loc.text or "").strip()
        parts = urlsplit(url)
        if parts.netloc.lower() != SITE_HOST:
            continue
        rel = unquote(parts.path).lstrip("/")
        if rel == "" or rel.endswith("/"):
            rel += "index.html"
        found.append(rel)
    return found


def public_articles(root: Path) -> list[str]:
    public: list[str] = []
    for rel in pages.citation_scope(root):
        path = root / rel
        if not path.is_file():
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        if pages.is_redirect_stub(raw) or pages.is_noindex(raw):
            continue
        public.append(rel)
    return public


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--sitemap", default="sitemap.xml")
    args = parser.parse_args(argv)
    root = Path(args.root)
    try:
        listed = sitemap_paths(root / args.sitemap)
        articles = public_articles(root)
    except RuntimeError as exc:
        print(f"[SITEMAP] ERROR: {exc}", file=sys.stderr)
        return 3
    listed_set = set(listed)
    missing = [rel for rel in articles if rel not in listed_set]
    for rel in missing:
        print(f"[MISSING] {rel} — public article not in {args.sitemap}")
    seen: set[str] = set()
    for rel in listed:
        path = root / rel
        if rel in seen:
            print(f"[WARN] {rel} — listed more than once")
        seen.add(rel)
        if not path.is_file():
            print(f"[WARN] {rel} — listed but the file does not exist")
            continue
        if re.search(r"\.html?$", rel):
            raw = path.read_text(encoding="utf-8", errors="replace")
            if pages.is_redirect_stub(raw):
                print(f"[WARN] {rel} — listed but it is a redirect stub")
            elif pages.is_noindex(raw):
                print(f"[WARN] {rel} — listed but it is marked noindex")
    print(f"[SITEMAP] public articles={len(articles)} listed={len(articles) - len(missing)} missing={len(missing)}")
    if missing:
        print("[SITEMAP] FAIL — add the missing pages to the sitemap", file=sys.stderr)
        return 1
    print("[SITEMAP] PASS — every public article is in the sitemap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
