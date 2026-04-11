# Article Theme Migration Playbook

**Status:** Active — Phase 1 complete (5 flagship articles)
**Owner:** Khun Tae (CEO)
**Last updated:** 2026-04-11

## Why

Before Phase 1, the LAS repository had **three competing themes** across 137 article files:

| Theme | Location | Count | Problem |
|-------|----------|-------|---------|
| Wiki (light, serif, `#a7d7f9` border) | `index.html`, `knowledge-hub.html`, 47 articles | 51 | — canonical |
| Dark navy/gold (`#0a0f1a` bg, sans-serif) | 79 articles including flagships | 79 | inconsistent with profile |
| Custom / legacy | `blog/bkk-council/` mostly | 7 | untracked variants |

Users clicking from the profile page into an article experienced a jarring light → dark transition. The goal of this migration is to unify all articles under the wiki theme so the entire site has one consistent, encyclopedic, professional look.

## Canonical theme

**Single source of truth:** `css/wiki-theme.css`

Extracted from `index.html` (profile page) on 2026-04-11. Contains:
- Wikipedia-inspired reset, typography (Linux Libertine / Georgia serif)
- `.wiki-wrapper` page frame (max-width 960px, `#a7d7f9` border)
- Headings, links, tables, infobox, TOC, practice-grid, pub-item
- **Compatibility layer** — maps 79 legacy dark-theme classes
  (`.insight-box`, `.warning-box`, `.law-cite`, `.amendment-grid`,
  `.section-heading`, `.risk-high`, etc.) to wiki-safe rendering
- Global TH/EN toggle CSS (`body[data-lang="th"] .lang-en { display: none; }`)
- Mobile responsive breakpoints

## Safety contract

Migration scripts **never** touch:

1. **Text content** inside `<p>`, `<li>`, `<h*>`, `<blockquote>` — not one word changes
2. **JSON-LD schemas** — preserved verbatim (SEO critical)
3. **Meta tags** — title, description, keywords, canonical, Open Graph, Twitter Card
4. **URLs** — internal links, image refs, canonical URLs
5. **Legal citations** — ม.xx, ฎ.xx/yyyy references

Only these are modified:
- `<style>...</style>` blocks → replaced with `<link rel="stylesheet" href="/css/wiki-theme.css">`
- `<body>` tag → gets `data-lang="th"` attribute
- Right after `<body>` → global TH/EN toggle injected
- Before `</body>` → `setSiteLang()` script injected

## Migration tool

**Script:** `scripts/migrate-article-theme.py`
**Requirements:** Python 3.10+, no external deps

### Usage

```bash
# Dry run — show what would change
python3 scripts/migrate-article-theme.py --dry-run articles/some-article.html

# Migrate specific files
python3 scripts/migrate-article-theme.py articles/labour-protection-act-amendment-9-2568.html

# Batch migrate all dark-theme articles
python3 scripts/migrate-article-theme.py --all-dark
```

### Safety features

- Writes `.bak` backup before modifying
- Skips already-migrated files (detects `[[THEME-MIGRATION-v1]]` marker)
- Skips non-dark files (no-op)
- Dry-run mode shows size delta before committing
- Outputs per-file status table

### What it does

1. Finds all `<style>...</style>` blocks
2. Replaces the FIRST one (in `<head>`) with the stylesheet link + migration marker
3. Removes subsequent in-body `<style>` blocks (often contain conflicting dark colors)
4. Adds `data-lang="th"` to `<body>`
5. Injects `.global-lang-toggle` right after `<body>` open
6. Injects `setSiteLang()` script before `</body>`

## Phase 1 — Flagship migration (COMPLETE 2026-04-11)

5 flagship articles migrated as proof of concept:

| File | Category | Why flagship |
|------|----------|--------------|
| `labour-protection-act-amendment-9-2568.html` | Labour | LPA v9 — newest, RULE 9 compliance priority |
| `pdpa-compliance-guide-business.html` | PDPA | PDPA flagship, LAS core service |
| `nda-non-disclosure-agreement-thailand.html` | Contracts | NDA most-searched contract type |
| `joint-venture-agreement-thailand.html` | Corporate | JV is Khun Tae's signature expertise |
| `hotel-management-agreement-thailand.html` | Real Estate | Hotel MA — MahaNakhon legacy, Real Estate flagship |

**Verification performed:**
- ✓ JSON-LD count preserved (2=2 per file)
- ✓ Meta tag count preserved (22=22)
- ✓ Body word count delta matches injected toggle/script exactly
- ✓ `<style>` blocks removed (0 remaining)
- ✓ `wiki-theme.css` link present (1)
- ✓ `global-lang-toggle` present (2 references = div + buttons)
- ✓ `setSiteLang` script present
- ✓ `body[data-lang="th"]` attribute added
- ✓ `knowledge-hub.html` validator still passes (8/8 checks)

## Phase 2 — Batch migration (PENDING)

**Scope:** 28 remaining dark-theme articles in `articles/` + 13 in `blog/bkk-council/`

**How to run:**
```bash
# Pull latest, create WIP branch
git pull --rebase origin main
git checkout -b theme/phase2-batch

# Dry run first
python3 scripts/migrate-article-theme.py --all-dark

# If all show DRY status, run live
python3 scripts/migrate-article-theme.py --all-dark

# Spot-check 5 random files in a browser
# If visually correct, commit
git add articles/ blog/
git commit -m "feat(theme): Phase 2 batch migrate to wiki theme"
git push origin theme/phase2-batch
```

**Risk:** each dark article has slightly different inline styles / custom classes. The compatibility layer in `wiki-theme.css` covers the 40+ common classes but may miss rare ones. Spot-check before bulk commit.

## Phase 3 — EN mirror + cleanup (PENDING)

**Scope:** 33 files in `en/articles/`

**Decision needed:** migrate or deprecate?
- Migrate if `en/` is still actively used
- Deprecate if bilingual toggle (lang-th / lang-en spans) supersedes `en/` duplicates

Khun Tae to decide based on SEO value of `/en/` URLs vs. maintenance cost.

## How to add a new article (post-migration)

1. Copy `templates/article-wiki-template.html` to `articles/<slug>.html`
2. Replace `{{PLACEHOLDERS}}` with real content
3. Write your content inside the `{{ARTICLE_BODY}}` section
4. Use existing CSS classes from `wiki-theme.css`:
   - `.infobox` for side panels
   - `.toc` for table of contents
   - `.law-cite` for statute quotes
   - `.insight-box`, `.warning-box`, `.success-box` for callouts
   - `.risk-high`, `.risk-medium`, `.risk-low` for inline risk badges
5. Add bilingual content using `.lang-th` / `.lang-en` spans
6. Do NOT inline `<style>` blocks — extend `wiki-theme.css` instead if you need new classes
7. Test locally by opening in a browser
8. Run `node scripts/validate-knowledge-hub.js` before committing (only validates knowledge-hub.html, but catches overall regressions)

## Rollback

Each migrated file has a `.bak` copy. To roll back:

```bash
cp articles/some-article.html.bak articles/some-article.html
```

To roll back ALL Phase 1 files:
```bash
for f in articles/*.bak; do cp "$f" "${f%.bak}"; done
```

Once Phase 1 is verified stable (1 week), `.bak` files can be deleted:
```bash
find articles -name "*.bak" -delete
```

## FAQ

**Q: Will the dark theme ever come back?**
A: No. Wiki theme is canonical per CEO decision 2026-04-11. If you want a dark mode, add `body[data-theme="dark"]` CSS to `wiki-theme.css` — don't create a second stylesheet.

**Q: What if a custom class from a dark article is missing from the compatibility layer?**
A: Add it to `wiki-theme.css` compatibility layer section. Don't add inline `<style>` to the article.

**Q: What about performance — is loading an external CSS slower than inline?**
A: First page load: +1 HTTP request (~10ms). Every subsequent article: 0 extra requests (cached). Net: faster site-wide once 2+ articles loaded.

**Q: Will this break SEO?**
A: No. JSON-LD schemas, meta tags, canonical URLs, and text content are all preserved verbatim. Only the visual wrapper changes.

---

*This document is the playbook for all future article theme work. Changes require CEO approval.*
