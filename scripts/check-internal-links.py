#!/usr/bin/env python3
"""Internal-link gate for the LAS Knowledge Hub (fail closed).

Every local href / src on the article pages, the reviewed blog pages and the site index pages (index.html,
knowledge-hub.html, all-content.html) must resolve to a file in this repository (system audit of 17 ตุลาคม 2569,
findings SS-01 and G6). Links to https://thundthornthep-ai.github.io/… count as local. A "#fragment" is checked
best-effort against the id / name attributes of the target page; route-like fragments ("#/x", "#!x", "#a=b") and
fragments on pages that build their ids in JavaScript cannot be checked statically, so --no-anchors turns the
anchor check off if it ever reports such a false positive.

Usage
  python3 scripts/check-internal-links.py                 # whole scope
  python3 scripts/check-internal-links.py FILE.html ...   # selected pages
  python3 scripts/check-internal-links.py --no-anchors

Exit 0 when every link resolves, 1 when any link is broken, 3 when the scope cannot be read.
"""
from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import las_public_pages as pages  # noqa: E402

ROOT = pages.ROOT
OWN_HOSTS = {"thundthornthep-ai.github.io", "www.thundthornthep-ai.github.io"}
LINK_ATTRS = {"href", "src"}
SKIP_SCHEMES = {"mailto", "tel", "javascript", "data", "sms", "blob", "about"}
TEMPLATE = re.compile(r"\$\{|\{\{|<%")


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[int, str, str]] = []
        self.anchors: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if value is None:
                continue
            if name in {"id", "name"}:
                self.anchors.add(value)
            elif name in LINK_ATTRS and tag != "base":
                self.links.append((self.getpos()[0], tag, value.strip()))

    handle_startendtag = handle_starttag


_parsed: dict[Path, LinkCollector] = {}


def parse(path: Path) -> LinkCollector:
    if path not in _parsed:
        collector = LinkCollector()
        collector.feed(path.read_text(encoding="utf-8", errors="replace"))
        collector.close()
        _parsed[path] = collector
    return _parsed[path]


def resolve(root: Path, page: str, url: str) -> tuple[Path | None, str]:
    """Local file a link points at (None when it is external or not checkable) and its fragment."""
    if not url or TEMPLATE.search(url):
        return None, ""
    parts = urlsplit(url)
    if parts.scheme and parts.scheme.lower() in SKIP_SCHEMES:
        return None, ""
    if parts.scheme or parts.netloc:
        if parts.scheme.lower() not in {"http", "https", ""} or parts.netloc.lower() not in OWN_HOSTS:
            return None, ""
        target = PurePosixPath(unquote(parts.path) or "/")
    elif not parts.path:
        return root / page, parts.fragment
    elif parts.path.startswith("/"):
        target = PurePosixPath(unquote(parts.path))
    else:
        target = PurePosixPath("/") / PurePosixPath(page).parent / unquote(parts.path)
    resolved: list[str] = []
    for part in target.parts[1:]:
        if part == "..":
            if resolved:
                resolved.pop()
        elif part not in {".", ""}:
            resolved.append(part)
    local = root.joinpath(*resolved) if resolved else root
    if url.split("?")[0].split("#")[0].endswith("/") or local.is_dir():
        local = local / "index.html"
    return local, parts.fragment


def exists(local: Path) -> bool:
    if local.is_file():
        return True
    # GitHub Pages serves /name for name.html.
    return local.suffix == "" and local.with_suffix(".html").is_file()


def check_page(root: Path, page: str, anchors: bool = True) -> list[str]:
    problems: list[str] = []
    for line, tag, url in parse(root / page).links:
        local, fragment = resolve(root, page, url)
        if local is None:
            continue
        if not exists(local):
            problems.append(f"{page}:{line}: <{tag}> {url} — target missing ({local.relative_to(root)})")
            continue
        if not anchors or not fragment or fragment.startswith(("/", "!")) or "=" in fragment:
            continue
        if not local.is_file():
            local = local.with_suffix(".html")
        if local.suffix.lower() not in {".html", ".htm"}:
            continue
        if unquote(fragment) not in parse(local).anchors:
            problems.append(f"{page}:{line}: <{tag}> {url} — no id or name '{unquote(fragment)}' in "
                            f"{local.relative_to(root)}")
    return problems


def scope(root: Path) -> list[str]:
    return sorted(set(pages.citation_scope(root)) | set(pages.index_pages(root)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", nargs="*")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--no-anchors", action="store_true", help="check files only, not #fragments")
    args = parser.parse_args(argv)
    root = Path(args.root)
    try:
        targets = args.files or scope(root)
    except RuntimeError as exc:
        print(f"[LINK-CHECK] ERROR: {exc}", file=sys.stderr)
        return 3
    problems: list[str] = []
    failing: set[str] = set()
    links = 0
    for page in targets:
        if not (root / page).is_file():
            problems.append(f"{page}: file does not exist")
            failing.add(page)
            continue
        links += len(parse(root / page).links)
        found = check_page(root, page, anchors=not args.no_anchors)
        if found:
            failing.add(page)
            problems.extend(found)
    for problem in problems:
        print(f"[BROKEN] {problem}")
    print(f"[LINK-CHECK] pages={len(targets)} links={links} broken={len(problems)} failing pages={len(failing)}")
    if problems:
        print("[LINK-CHECK] FAIL — every local link must resolve", file=sys.stderr)
        return 1
    print("[LINK-CHECK] PASS — all local links resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
