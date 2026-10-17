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

import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEWS = Path("learning-hub/legal-reviews.json")
ARTICLE_GLOBS = ("articles/*.html", "en/articles/*.html")
INDEX_PAGES = ("index.html", "knowledge-hub.html", "all-content.html")

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
CSS_COMMENT = re.compile(r"/\*.*?(?:\*/|\Z)", re.DOTALL)
CSS_WIDE = {"inherit", "initial", "unset", "revert", "revert-layer"}
DISPLAY_KEYWORDS = {
    "none", "contents", "block", "inline", "run-in", "flow", "flow-root", "table", "flex", "grid", "ruby", "math",
    "list-item", "inline-block", "inline-table", "inline-flex", "inline-grid", "table-row-group",
    "table-header-group", "table-footer-group", "table-row", "table-cell", "table-column-group", "table-column",
    "table-caption", "ruby-base", "ruby-text", "ruby-base-container", "ruby-text-container", "inline-list-item",
}
VISIBILITY_KEYWORDS = {"visible", "hidden", "collapse"}


def valid_value(prop: str, value: str) -> bool:
    """Whether a display or visibility value is one a browser accepts (a CSS-wide keyword included)."""
    if value in CSS_WIDE:
        return True
    if prop == "visibility":
        return value in VISIBILITY_KEYWORDS
    words = value.split()
    return bool(words) and len(words) <= 3 and all(word in DISPLAY_KEYWORDS for word in words) and (
        "none" not in words or len(words) == 1)


def winning_declaration(style: str, prop: str) -> str:
    """The value of `prop` that an inline style applies: the last !important declaration if any, else the last one
    ("display:none; display:block" shows the element; Codex review of PR #80)."""
    normal = important = ""
    # a CSS comment is whitespace to the cascade: "display:/**/none" hides the element (Codex review of PR #80)
    style = CSS_COMMENT.sub(" ", style)
    for declaration in style.split(";"):
        name, colon, value = declaration.partition(":")
        if not colon or name.strip().lower() != prop:
            continue
        value = value.strip().lower()
        is_important = value.endswith("!important")
        if is_important:
            value = value[: -len("!important")].strip()
        # an invalid value is dropped by the browser and does not override ("display:none; display:bogus" stays
        # hidden; Codex review of PR #80)
        if not valid_value(prop, value):
            continue
        if is_important:
            important = value
        else:
            normal = value
    return important or normal


def is_hidden(tag_body: str) -> bool:
    """A start tag (its inside) that hides its element: the hidden attribute, aria-hidden="true" or an inline style
    with display:none or visibility:hidden. The attributes are parsed, so the word "hidden" inside another attribute's
    value (title="section hidden by default") hides nothing (Codex review of PR #80)."""
    attrs = attributes(tag_body)
    return ("hidden" in attrs or attrs.get("aria-hidden", "").strip().lower() == "true"
            or winning_declaration(attrs.get("style", ""), "display") == "none"
            or winning_declaration(attrs.get("style", ""), "visibility") == "hidden")


def class_tokens(tag_body: str) -> list[str]:
    """The tokens of a start tag's own class attribute, lower-cased; text inside another attribute's value
    (data-note="x class=faq") is not a class (Codex review of PR #80)."""
    return attributes(tag_body).get("class", "").lower().split()


# a start tag: its name and its inside, quoted attribute values read whole
START_TAG = re.compile(r"<([A-Za-z][A-Za-z0-9-]*)(" + TAG_BODY + ")>")
QUOTED_VALUE = re.compile(r"\"[^\"]*\"|'[^']*'")


def mask_attribute_markup(html: str) -> str:
    """The markup with every "<" and ">" inside a quoted attribute value replaced by a space (same length, so offsets
    hold): markup written in an attribute (title="<h2>FAQ</h2>", data-example="<table>") is text the browser never
    parses, so no heading or table regex can find it there (Codex review of PR #80)."""
    def tag(match: re.Match[str]) -> str:
        return QUOTED_VALUE.sub(lambda value: value.group(0).replace("<", " ").replace(">", " "), match.group(0))
    return START_TAG.sub(tag, html)
HTML_COMMENT = re.compile(r"<!--.*?(?:-->|\Z)", re.DOTALL)
# comments and raw-text elements read left to right in one pass: a "<!--" inside a script, style, textarea, title or
# xmp is that element's text, not a comment (const marker = "<!--"; Codex review of PR #80)
COMMENT_OR_RAW_TEXT = re.compile(r"<!--.*?(?:-->|\Z)|<(script|style|textarea|title|xmp)(?=[\s/>])" + TAG_BODY
                                 + r">.*?(?:</\1\s*>|\Z)", re.DOTALL | re.IGNORECASE)


def strip_comments(html: str) -> str:
    """The markup with its HTML comments blanked and every raw-text element left as it is."""
    return COMMENT_OR_RAW_TEXT.sub(lambda match: " " if match.group(0).startswith("<!--") else match.group(0), html)

# elements whose content visitors never see: <template> is inert, <noscript> shows only with scripting off, and the
# fallback body of <iframe>, <noembed> and <noframes> is raw text a browser with those features never shows (Codex review
# of PR #80)
INERT = {"template", "noscript", "iframe", "noembed", "noframes",
         # and <textarea> holds raw text: markup inside it is shown as characters, never as elements (Codex review of
         # PR #80), so a heading or a refresh tag written there is no heading and no redirect
         "textarea", "xmp",
         # <plaintext> has no end: everything after it is text, so it is blanked to the end of the file
         "plaintext"}


# a trailing "/" closes a start tag only in foreign content: on <svg> or <math> itself and on any element inside one
# (<circle … />). On an HTML element, a custom element included, it does nothing: <div hidden/> and <search hidden/>
# open a hidden element that runs to its end tag (HTML Standard, start tags; Codex review of PR #80)
FOREIGN_ROOTS = ("svg", "math")
FOREIGN_ELEMENT = re.compile(r"<(svg|math)(?=[\s/>])" + TAG_BODY + r">.*?</\1\s*>", re.DOTALL | re.IGNORECASE)


def foreign_spans(html: str) -> list[tuple[int, int]]:
    """The (start, end) offsets of every <svg> and <math> element (an unclosed one is not foreign content here)."""
    return [(match.start(), match.end()) for match in FOREIGN_ELEMENT.finditer(html)]


# HTML integration points: inside <foreignObject>, <desc> or <title> of an SVG, and <annotation-xml> of MathML, the
# content is parsed as HTML again, so "<div hidden/>" there opens a hidden div (Codex review of PR #80)
INTEGRATION_POINTS = ("foreignobject", "desc", "title", "annotation-xml")
INTEGRATION_ELEMENT = re.compile(r"<(foreignObject|desc|title|annotation-xml)(?=[\s/>])" + TAG_BODY + r">.*?</\1\s*>",
                                 re.DOTALL | re.IGNORECASE)


def foreign_test(html: str):
    """A test of whether an offset of `html` is in foreign content: inside an <svg> or <math> element and not inside
    one of its HTML integration points."""
    foreign = foreign_spans(html)
    integration = [(match.start(), match.end()) for match in INTEGRATION_ELEMENT.finditer(html)
                   if in_spans(foreign, match.start())]
    return lambda position: in_spans(foreign, position) and not in_spans(integration, position)


def in_spans(spans: list[tuple[int, int]], position: int) -> bool:
    return any(start < position < end for start, end in spans)


def stack_is_foreign(open_names: list[str]) -> bool:
    """Whether the innermost of the open elements (outermost first) puts its content in foreign content."""
    for name in reversed(open_names):
        if name in INTEGRATION_POINTS:
            return False
        if name in FOREIGN_ROOTS:
            return True
    return False


# elements whose content is raw text or text-only: nothing inside them nests
RAW_TEXT = {"textarea", "iframe", "noembed", "noframes", "noscript", "title", "xmp", "plaintext"}


def self_closing(name: str, tag: str, foreign: bool = False) -> bool:
    """Whether a start tag opens no subtree: a void element, or "/>" in foreign content (`foreign`: the tag is inside
    an <svg> or <math> element) or on <svg> or <math> itself."""
    return name in VOID_TAGS or (tag.endswith("/>") and (foreign or name in FOREIGN_ROOTS))


def strip_unrendered(html: str) -> str:
    """The markup with every subtree a reader never sees blanked: <template> contents (inert), <noscript> contents
    (shown only with scripting off), <iframe>, <noembed> and <noframes> fallback bodies, and elements with the
    hidden attribute, aria-hidden="true" or an inline display:none / visibility:hidden style. Nesting is counted by tag name, so an inner </template> or </div> does not
    end the outer element; an unclosed one runs to the end."""
    out: list[str] = []
    pos, skip, depth = 0, "", 0
    foreign = foreign_test(html)
    for tag in ANY_TAG.finditer(html):
        closing, name = tag.group(1) == "/", (tag.group(2) or "").lower()
        if not name:
            continue
        if skip:
            if name == skip:
                if skip in RAW_TEXT:
                    # raw text ends at its first end tag: a "<textarea>" inside it is characters, not a nested
                    # element (Codex review of PR #80)
                    depth = 0 if closing else depth
                else:
                    depth += -1 if closing else (0 if self_closing(name, tag.group(0), foreign(tag.start())) else 1)
                if not depth:
                    out.append(" ")
                    pos, skip = tag.end(), ""
            continue
        if closing or self_closing(name, tag.group(0), foreign(tag.start())):
            continue
        if name in INERT or is_hidden(tag.group(0)[len(name) + 1:-1]):
            out.append(html[pos:tag.start()])
            skip, depth = name, 1
    if not skip:
        out.append(html[pos:])
    return "".join(out)


strip_templates = strip_unrendered

BODY_START = re.compile(r"<body(?=[\s/>])" + TAG_BODY + ">", re.IGNORECASE)


def page_body(html: str) -> str:
    """The markup after the <body> start tag (the whole page when it has none). A "<body>" inside the raw <title> text
    is characters, so titles are blanked (same length) before the search (Codex review of PR #80)."""
    blank = lambda title: " " * len(title.group(0))  # noqa: E731
    start = BODY_START.search(TITLE_ELEMENT.sub(blank, html))
    # a <title> after the body start is raw text too and renders nothing in the page (Codex review of PR #80)
    return TITLE_ELEMENT.sub(blank, html[start.end():] if start else html)


META_TAG = re.compile(r"<meta(?=[\s/>])(" + TAG_BODY + ")>", re.IGNORECASE)
# one attribute of a tag: its name and its value (quoted or not)
ATTRIBUTE = re.compile(r"""([^\s"'>/=]+)(?:\s*=\s*("[^"]*"|'[^']*'|[^\s"'>]+))?""")


def attributes(tag_body: str) -> dict[str, str]:
    """The attributes of a start tag's inside, names lower-cased, values unquoted and with character references decoded
    as a browser applies them (style="display&#58;none"; Codex review of PR #80), the first of a repeated name."""
    found: dict[str, str] = {}
    for name, value in ATTRIBUTE.findall(tag_body):
        found.setdefault(name.lower(), html.unescape(value[1:-1] if value[:1] in "\"'" and value else value))
    return found
# the content of a refresh: a delay, then ";" or "," and the destination, with or without "url="
REFRESH_CONTENT = re.compile(r"\s*\d+(?:\.\d*)?\s*[;,]\s*(?:url\s*=\s*)?(.*)", re.IGNORECASE | re.DOTALL)


def refresh_target(content: str) -> str:
    """The destination a refresh content names ("0;url=https://…", "0; '/a.html'"); "" for a plain reload ("30")."""
    match = REFRESH_CONTENT.match(content)
    return match.group(1).strip().strip("\"'").strip() if match else ""


# a raw-text element or comment with no end runs to the end of the file, as a browser reads it (Codex review of PR #80)
TITLE_ELEMENT = re.compile(r"<title(?=[\s/>])" + TAG_BODY + r">.*?(?:</title\s*>|\Z)", re.DOTALL | re.IGNORECASE)
SCRIPT_OR_STYLE = re.compile(r"<(script|style)(?=[\s/>])" + TAG_BODY + r">.*?(?:</\1\s*>|\Z)",
                             re.DOTALL | re.IGNORECASE)


def is_redirect_stub(html: str) -> bool:
    # a refresh tag in a comment, a script string or a style does not redirect (Codex review of PR #80)
    # each <meta> tag is read with its quoted attribute values whole ('<meta data-note="1 > 0" http-equiv="refresh">')
    # a refresh without a destination (content="30", or no content) only reloads the page and is no redirect stub, so
    # an ordinary article with one is still checked (Codex review of PR #80)
    # nor does one in an inert subtree (<template>, <iframe> fallback, a hidden element): such a page is still checked
    # and <title> text is raw text: a refresh tag written there is characters (Codex review of PR #80)
    markup = strip_unrendered(TITLE_ELEMENT.sub(" ", SCRIPT_OR_STYLE.sub(" ", strip_comments(html))))
    for tag in META_TAG.finditer(markup):
        attrs = attributes(tag.group(1))
        if attrs.get("http-equiv", "").strip().lower() == "refresh" and refresh_target(attrs.get("content", "")):
            return True
    return False


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
