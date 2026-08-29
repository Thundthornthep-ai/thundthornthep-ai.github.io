#!/usr/bin/env python3
"""Public, release-scoped LAS citation gate.

This verifier checks that every statutory section cited by a public article is
present in the release's official-source registry. It deliberately stores no
private source text. The full semantic legal review remains a separate LAS
control; a missing verifier, missing registry, malformed file, or unmatched
citation is a hard failure.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SECTION_PATTERNS = (
    re.compile(r"มาตรา\s*(\d+(?:/\d+)?)"),
    re.compile(r"(?i)\bsection\s+(\d+(?:/\d+)?)"),
)


def load_registry(path: Path) -> set[str]:
    if not path.is_dir():
        raise RuntimeError(f"citation registry is missing: {path}")
    files = sorted(path.glob("*.md"))
    if not files:
        raise RuntimeError(f"citation registry has no Markdown files: {path}")
    sections: set[str] = set()
    has_official_source = False
    for file in files:
        try:
            text = file.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"cannot read citation registry {file}: {exc}") from exc
        if "http://" in text or "https://" in text:
            has_official_source = True
        sections.update(match.group(1) for pattern in SECTION_PATTERNS for match in pattern.finditer(text))
    if not has_official_source:
        raise RuntimeError("citation registry contains no official source URL")
    if not sections:
        raise RuntimeError("citation registry contains no section identifiers")
    return sections


def cited_sections(text: str) -> list[str]:
    found: list[str] = []
    for pattern in SECTION_PATTERNS:
        found.extend(match.group(1) for match in pattern.finditer(text))
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--kb", required=True)
    parser.add_argument("--mode", default="hard-gate")
    parser.add_argument("--no-pinecone", action="store_true")
    args = parser.parse_args()
    if args.mode not in {"hard-gate", "soft-warn", "report"}:
        print(f"[PUBLIC-CITATION-GATE] invalid mode: {args.mode}", file=sys.stderr)
        return 1
    source = Path(args.input)
    if not source.is_file():
        print(f"[PUBLIC-CITATION-GATE] input is missing: {source}", file=sys.stderr)
        return 3
    try:
        text = source.read_text(encoding="utf-8")
        registry = load_registry(Path(args.kb))
    except (OSError, RuntimeError) as exc:
        print(f"[PUBLIC-CITATION-GATE] ERROR: {exc}", file=sys.stderr)
        return 3
    citations = cited_sections(text)
    if not citations:
        print("[PUBLIC-CITATION-GATE] No statutory citations detected.")
        return 2
    missing = sorted(set(citations) - registry, key=lambda value: (int(value.split('/')[0]), value))
    print(f"[PUBLIC-CITATION-GATE] citations={len(citations)} unique={len(set(citations))}")
    if missing:
        for section in missing:
            print(f"[PUBLIC-CITATION-GATE] BLOCK section {section}: not in official registry", file=sys.stderr)
        print("[PUBLIC-CITATION-GATE] FAIL — every citation must be registry-backed", file=sys.stderr)
        return 1
    print("[PUBLIC-CITATION-GATE] PASS — all citations are registry-backed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
