#!/usr/bin/env python3
"""Remove external hyperlinks except laslegal.co.th and this GitHub Pages site."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_HOSTS = frozenset(
    {
        "thundthornthep-ai.github.io",
        "laslegal.co.th",
        "www.laslegal.co.th",
    }
)
SKIP_DIRS = {".git", "node_modules", "docs"}


def host_allowed(href: str) -> bool:
    if not href or href.startswith("#"):
        return True
    if href.startswith("/") and not href.startswith("//"):
        return True
    if href.startswith("mailto:"):
        return True
    if not href.lower().startswith(("http://", "https://")):
        return True
    host = urlparse(href).netloc.lower()
    return host in ALLOWED_HOSTS


def link_tag_allowed(href: str) -> bool:
    if not href:
        return True
    if host_allowed(href):
        return True
    host = urlparse(href).netloc.lower() if href.lower().startswith(("http://", "https://")) else ""
    return host in ("fonts.googleapis.com", "fonts.gstatic.com")


def unwrap_disallowed_anchors(soup: BeautifulSoup) -> int:
    count = 0
    for a in list(soup.find_all("a", href=True)):
        href = a.get("href", "")
        if host_allowed(href):
            continue
        a.unwrap()
        count += 1
    return count


def fix_link_tags(soup: BeautifulSoup) -> int:
    count = 0
    for link in list(soup.find_all("link", href=True)):
        href = link.get("href", "")
        if link_tag_allowed(href):
            continue
        del link["href"]
        count += 1
    return count


def clean_json_ld_urls(text: str) -> str:
    def repl_same_as(match: re.Match[str]) -> str:
        raw = match.group(1)
        try:
            urls = json.loads(raw)
        except json.JSONDecodeError:
            return match.group(0)
        if not isinstance(urls, list):
            return match.group(0)
        kept = [
            u
            for u in urls
            if isinstance(u, str) and host_allowed(u)
        ]
        return f'"sameAs":{json.dumps(kept, ensure_ascii=False)}'

    text = re.sub(r'"sameAs"\s*:\s*(\[[^\]]*\])', repl_same_as, text)

    def repl_url_field(match: re.Match[str]) -> str:
        url = match.group(1)
        if host_allowed(url):
            return match.group(0)
        key = match.group(2)
        return f'"{key}":""'

    text = re.sub(
        r'"(url)"\s*:\s*"(https?://[^"]+)"',
        lambda m: repl_url_field(m) if not host_allowed(m.group(2)) else m.group(0),
        text,
    )
    return text


def process_html(path: Path) -> tuple[int, int]:
    original = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(original, "html.parser")
    anchor_count = unwrap_disallowed_anchors(soup)
    fix_link_tags(soup)
    updated = str(soup)
    if anchor_count or updated != original:
        updated = clean_json_ld_urls(updated)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
    return anchor_count, int(updated != original)


def main() -> int:
    total_anchors = 0
    changed_files = 0
    for path in ROOT.rglob("*.html"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        anchors, changed = process_html(path)
        if changed:
            changed_files += 1
            total_anchors += anchors
            print(f"  {path.relative_to(ROOT)}: {anchors} links unwrapped")
    print(f"Done: {changed_files} files updated, {total_anchors} external anchors removed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
