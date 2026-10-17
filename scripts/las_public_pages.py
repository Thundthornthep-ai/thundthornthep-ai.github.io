#!/usr/bin/env python3
"""Which public pages the LAS publication gates cover.

Shared by verify-legal-citations.sh, validate-content-rules.py, check-internal-links.py and
check-sitemap-coverage.py so every gate agrees on the scope:

* article pages: every tracked ``articles/*.html`` and ``en/articles/*.html``;
* reviewed blog pages: the ``blog/`` and ``en/blog/`` variants registered in ``learning-hub/legal-reviews.json``
  (the Learning Hub's legal-review registry). Other blog pages, such as the Bangkok council election campaign pages,
  are outside the Knowledge Hub and outside these gates;
* index pages: the site-level hubs ``index.html``, ``knowledge-hub.html`` and ``all-content.html``.

A missing or malformed registry is a hard failure, so the blog scope cannot silently become empty.

CLI (used by the shell gate):
  python3 scripts/las_public_pages.py citation-scope     # article + reviewed blog pages, one per line
  python3 scripts/las_public_pages.py reviewed-blog      # reviewed blog pages only
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEWS = Path("learning-hub/legal-reviews.json")
ARTICLE_GLOBS = ("articles/*.html", "en/articles/*.html")
INDEX_PAGES = ("index.html", "knowledge-hub.html", "all-content.html")

META_REFRESH = re.compile(r"<meta[^>]+http-equiv\s*=\s*[\"']?refresh", re.IGNORECASE)
META_ROBOTS = re.compile(r"<meta[^>]+name\s*=\s*[\"']robots[\"'][^>]*>", re.IGNORECASE)


def tracked(root: Path, *patterns: str) -> list[str]:
    """Tracked files matching git pathspecs; a plain glob when the tree is not a git checkout."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--", *patterns],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        return sorted(line for line in out.splitlines() if line)
    except (OSError, subprocess.CalledProcessError):
        found: set[str] = set()
        for pattern in patterns:
            found.update(str(path.relative_to(root)) for path in root.glob(pattern))
        return sorted(found)


def reviewed_blog_pages(root: Path = ROOT) -> list[str]:
    path = root / REVIEWS
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        variants = data["variants"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(f"legal-review registry is missing or malformed: {path}: {exc}") from exc
    if not isinstance(variants, dict):
        raise RuntimeError(f"legal-review registry has no variants map: {path}")
    return sorted(key for key in variants if key.startswith(("blog/", "en/blog/")) and key.endswith(".html"))


def article_pages(root: Path = ROOT) -> list[str]:
    return tracked(root, *ARTICLE_GLOBS)


def citation_scope(root: Path = ROOT) -> list[str]:
    """Pages gated by the citation firewall and the content rules."""
    return sorted(set(article_pages(root)) | set(reviewed_blog_pages(root)))


def index_pages(root: Path = ROOT) -> list[str]:
    return [name for name in INDEX_PAGES if (root / name).is_file()]


def in_citation_scope(path: str, root: Path = ROOT) -> bool:
    if re.fullmatch(r"(?:en/)?articles/[^/]+\.html", path):
        return True
    return path in reviewed_blog_pages(root)


TEMPLATE_TAG = re.compile(r"<(/?)template\b[^>]*>", re.IGNORECASE)


def strip_templates(html: str) -> str:
    """The markup with every <template> subtree blanked, nesting included: template contents are inert and never
    rendered, and an inner </template> does not end the outer one. An unclosed template runs to the end."""
    out: list[str] = []
    depth, pos = 0, 0
    for tag in TEMPLATE_TAG.finditer(html):
        if tag.group(1):
            if depth:
                depth -= 1
                if not depth:
                    out.append(" ")
                    pos = tag.end()
        else:
            if not depth:
                out.append(html[pos:tag.start()])
            depth += 1
    if not depth:
        out.append(html[pos:])
    return "".join(out)


def is_redirect_stub(html: str) -> bool:
    return META_REFRESH.search(html) is not None


def is_noindex(html: str) -> bool:
    return any("noindex" in tag.lower() for tag in META_ROBOTS.findall(html))


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in {"citation-scope", "reviewed-blog"}:
        print("usage: las_public_pages.py citation-scope|reviewed-blog", file=sys.stderr)
        return 2
    try:
        pages = citation_scope() if argv[1] == "citation-scope" else reviewed_blog_pages()
    except RuntimeError as exc:
        print(f"[PUBLIC-PAGES] ERROR: {exc}", file=sys.stderr)
        return 1
    for page in pages:
        print(page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
