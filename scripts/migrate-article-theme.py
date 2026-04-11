#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate-article-theme.py — Swap dark theme -> wiki theme in legal articles.

SAFETY CONTRACT (never violate):
  1. NEVER modify text content inside <p>, <li>, <h*>, <blockquote>, etc.
  2. NEVER modify JSON-LD schemas (they must be preserved verbatim).
  3. NEVER modify meta tags, canonical URLs, Open Graph, or Twitter Card.
  4. ONLY replace:
     - The inline <style>...</style> block -> <link rel="stylesheet" href="/css/wiki-theme.css">
     - The <body>...</body> wrapper to inject wiki-wrapper + global lang toggle
     - Legacy <header class="site-header"> and <section class="article-hero">
       are left in place (wiki-theme.css restyles them via compatibility layer)
  5. Write a backup copy to .bak before modifying.

Usage:
  python3 scripts/migrate-article-theme.py articles/labour-protection-act-amendment-9-2568.html
  python3 scripts/migrate-article-theme.py --dry-run articles/*.html
  python3 scripts/migrate-article-theme.py --all-dark  # migrate all dark-theme articles
"""

import re
import sys
import os
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CSS_LINK = '<link rel="stylesheet" href="/css/wiki-theme.css">'
LANG_TOGGLE_HTML = '''<!-- Canonical TH/EN toggle (see docs/BILINGUAL-CONVENTION.md) -->
<div class="global-lang-toggle" role="group" aria-label="Site language toggle">
  <button type="button" class="active" data-lang="th" onclick="setSiteLang('th')">ไทย</button>
  <button type="button" data-lang="en" onclick="setSiteLang('en')">English</button>
</div>
'''

LANG_TOGGLE_SCRIPT = '''<!-- Canonical setSiteLang() — see docs/BILINGUAL-CONVENTION.md -->
<script>
function setSiteLang(lang) {
  document.body.setAttribute('data-lang', lang);
  document.querySelectorAll('.global-lang-toggle button').forEach(function(b) {
    b.classList.toggle('active', b.getAttribute('data-lang') === lang);
  });
  try { localStorage.setItem('las_site_lang', lang); } catch(e) {}
}
(function(){
  try {
    var saved = localStorage.getItem('las_site_lang');
    if (saved === 'en') setSiteLang('en');
  } catch(e) {}
})();
</script>
'''

MARKER_BEGIN = '<!-- [[THEME-MIGRATION-v1]] -->'
MARKER_END = '<!-- [[/THEME-MIGRATION-v1]] -->'


def is_dark_theme(html: str) -> bool:
    return bool(re.search(r'--navy\b|background:\s*#0a0f1a', html))


def is_already_migrated(html: str) -> bool:
    return MARKER_BEGIN in html


def migrate(html: str) -> tuple[str, dict]:
    """Return (new_html, stats). Pure function — never touches disk."""
    stats = {'style_replaced': False, 'body_wrapped': False, 'toggle_added': False}

    # 1. Replace FIRST inline <style>...</style> (in <head>) with stylesheet link
    #    and REMOVE all subsequent <style> blocks (in-body overrides with dark colors)
    style_re = re.compile(r'<style[^>]*>[\s\S]*?</style>', re.MULTILINE)
    style_matches = list(style_re.finditer(html))
    if style_matches:
        # Remove back-to-front to keep indices stable
        for i, m in enumerate(reversed(style_matches)):
            idx = len(style_matches) - 1 - i
            if idx == 0:
                # First <style> becomes the stylesheet link
                replacement = f'{MARKER_BEGIN}\n{CSS_LINK}\n{MARKER_END}'
            else:
                # Subsequent <style> blocks removed (wiki-theme.css handles these)
                replacement = f'<!-- [[removed inline style #{idx} by theme migration]] -->'
            html = html[:m.start()] + replacement + html[m.end():]
        stats['style_replaced'] = True
        stats['styles_removed'] = len(style_matches) - 1

    # 2. Add body[data-lang="th"] attribute if plain <body>
    body_open_re = re.compile(r'<body(?:\s[^>]*)?>', re.IGNORECASE)
    bm = body_open_re.search(html)
    if bm:
        body_tag = bm.group(0)
        if 'data-lang' not in body_tag:
            new_body = '<body data-lang="th">'
            html = html[:bm.start()] + new_body + html[bm.end():]
        # 3. Inject language toggle right after <body> open
        insertion_point = bm.start() + len('<body data-lang="th">')
        # Only insert if not already present
        if 'global-lang-toggle' not in html:
            html = html[:insertion_point] + '\n' + LANG_TOGGLE_HTML + html[insertion_point:]
            stats['toggle_added'] = True
        stats['body_wrapped'] = True

    # 4. Inject setSiteLang script before </body> if not present
    if 'function setSiteLang' not in html:
        close_body_re = re.compile(r'</body>', re.IGNORECASE)
        cb = close_body_re.search(html)
        if cb:
            html = html[:cb.start()] + LANG_TOGGLE_SCRIPT + '\n' + html[cb.start():]

    return html, stats


def process_file(path: Path, dry_run: bool = False) -> dict:
    result = {'path': str(path), 'status': 'skipped', 'reason': '', 'stats': {}}
    if not path.exists():
        result['reason'] = 'file not found'
        return result

    html = path.read_text(encoding='utf-8')

    if is_already_migrated(html):
        result['status'] = 'already-migrated'
        return result

    if not is_dark_theme(html):
        result['status'] = 'not-dark'
        result['reason'] = 'file does not use dark theme (no migration needed)'
        return result

    new_html, stats = migrate(html)
    result['stats'] = stats

    if not stats['style_replaced']:
        result['status'] = 'error'
        result['reason'] = 'could not find <style> block to replace'
        return result

    if dry_run:
        result['status'] = 'dry-run-ok'
        result['reason'] = f'would write {len(new_html)} bytes (was {len(html)})'
        return result

    # Backup original
    bak_path = path.with_suffix(path.suffix + '.bak')
    if not bak_path.exists():
        bak_path.write_text(html, encoding='utf-8')

    path.write_text(new_html, encoding='utf-8')
    result['status'] = 'migrated'
    return result


def main():
    parser = argparse.ArgumentParser(description='Migrate article theme dark -> wiki')
    parser.add_argument('files', nargs='*', help='Files to migrate (relative to repo root)')
    parser.add_argument('--dry-run', action='store_true', help='Do not write changes')
    parser.add_argument('--all-dark', action='store_true',
                        help='Find all dark-theme articles under articles/ blog/ en/')
    args = parser.parse_args()

    targets: list[Path] = []
    if args.all_dark:
        for d in ['articles', 'blog/bkk-council', 'en/articles']:
            full = REPO_ROOT / d
            if full.is_dir():
                targets.extend(sorted(full.glob('*.html')))
    else:
        for f in args.files:
            targets.append(REPO_ROOT / f if not os.path.isabs(f) else Path(f))

    if not targets:
        print('No files specified. Use --all-dark or pass file paths.')
        sys.exit(1)

    print(f"Processing {len(targets)} file(s){' (DRY RUN)' if args.dry_run else ''}...\n")

    counts = {'migrated': 0, 'dry-run-ok': 0, 'already-migrated': 0, 'not-dark': 0, 'error': 0, 'skipped': 0}
    for t in targets:
        r = process_file(t, dry_run=args.dry_run)
        counts[r['status']] = counts.get(r['status'], 0) + 1
        label = {
            'migrated': 'OK ',
            'dry-run-ok': 'DRY',
            'already-migrated': '-- ',
            'not-dark': '-- ',
            'error': 'ERR',
            'skipped': 'SKP',
        }.get(r['status'], '???')
        rel = os.path.relpath(r['path'], REPO_ROOT)
        extra = f"  ({r['reason']})" if r['reason'] else ''
        print(f'  [{label}] {rel}{extra}')

    print(f"\nSummary: {counts}")
    if counts['error'] > 0:
        sys.exit(2)


if __name__ == '__main__':
    main()
