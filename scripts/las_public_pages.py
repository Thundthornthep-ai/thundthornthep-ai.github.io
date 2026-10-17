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


# inline formatting joins its text with the text around it, as the browser renders it
INLINE = {"a", "abbr", "b", "bdi", "bdo", "cite", "code", "del", "dfn", "em", "font", "i", "ins", "kbd", "label", "mark",
          "q", "s", "samp", "small", "span", "strong", "sub", "sup", "time", "u", "var"}
# the inside of a start or end tag, reading quoted attribute values whole ('<div data-note="1 > 0" hidden>' is one tag)
TAG_BODY = r"""(?:[^>"']|"[^"]*"|'[^']*')*"""
ANY_TAG = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9-]*)?" + TAG_BODY + ">")


def untag(markup: str) -> str:
    """Text of `markup` with block tags as spaces and inline tags removed ("<em>คำถาม</em>ที่พบบ่อย" is one word)."""
    return ANY_TAG.sub(lambda tag: "" if (tag.group(2) or "").lower() in INLINE else " ", markup)


VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
HIDDEN_ATTR = re.compile(r"\s(?:hidden|aria-hidden\s*=\s*[\"']?true[\"']?)(?=[\s/>=]|$)"
                         # a quoted style value, or an unquoted one up to the next whitespace
                         r"|\sstyle\s*=\s*(?:\"[^\"]*?|'[^']*?|[^\"'\s>]*?)\b(?:display\s*:\s*none|visibility\s*:\s*hidden)",
                         re.IGNORECASE)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# elements whose content visitors never see: <template> is inert, <noscript> shows only with scripting off
INERT = {"template", "noscript"}


def strip_unrendered(html: str) -> str:
    """The markup with every subtree a reader never sees blanked: <template> contents (inert), <noscript> contents
    (shown only with scripting off) and elements with the
    hidden attribute, aria-hidden="true" or an inline display:none / visibility:hidden style. Nesting is counted by tag name, so an inner </template> or </div> does not
    end the outer element; an unclosed one runs to the end."""
    out: list[str] = []
    pos, skip, depth = 0, "", 0
    for tag in ANY_TAG.finditer(html):
        closing, name = tag.group(1) == "/", (tag.group(2) or "").lower()
        if not name:
            continue
        if skip:
            if name == skip:
                depth += -1 if closing else (0 if tag.group(0).endswith("/>") else 1)
                if not depth:
                    out.append(" ")
                    pos, skip = tag.end(), ""
            continue
        if closing or name in VOID_TAGS or tag.group(0).endswith("/>"):
            continue
        if name in INERT or HIDDEN_ATTR.search(tag.group(0)[len(name) + 1:]):
            out.append(html[pos:tag.start()])
            skip, depth = name, 1
    if not skip:
        out.append(html[pos:])
    return "".join(out)


strip_templates = strip_unrendered


SCRIPT_OR_STYLE = re.compile(r"<(script|style)\b" + TAG_BODY + r">.*?</\1\s*>", re.DOTALL | re.IGNORECASE)


def is_redirect_stub(html: str) -> bool:
    # a refresh tag in a comment, a script string or a style does not redirect (Codex review of PR #80)
    return META_REFRESH.search(SCRIPT_OR_STYLE.sub(" ", HTML_COMMENT.sub(" ", html))) is not None


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
