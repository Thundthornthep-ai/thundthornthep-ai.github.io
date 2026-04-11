# Bilingual Class Convention

**Status:** CANONICAL — enforced by `scripts/validate-knowledge-hub.js` (check C8)
**Owner:** Khun Tae (CEO, Legal Advance Solution Co., Ltd.)
**Last updated:** 2026-04-11

## Rule

There is exactly **one** bilingual class system in this repository:

| Class      | Purpose                                  |
|------------|------------------------------------------|
| `lang-th`  | Thai-language content (visible in TH mode) |
| `lang-en`  | English-language content (visible in EN mode) |

Toggle is controlled by `body[data-lang="th"]` or `body[data-lang="en"]` via the `setSiteLang()` function. Current language persists in `localStorage['las_site_lang']`.

## Why this rule exists

On 2026-04-11 a rebase conflict in `knowledge-hub.html` exposed **three coexisting bilingual systems**:

1. `.lang-th` / `.lang-en` (canonical, used site-wide)
2. `.th-text` / `.en-text` inside `[data-th-en]` (legacy hero section pattern)
3. `.t-th` / `.t-en` (accidentally introduced by an AI session during fix attempt)

Having multiple conventions caused:
- Toggle button swapping some elements but not others
- Merge conflicts when different sessions picked different conventions
- Validator impossible to write without ambiguity

**Decision:** collapse to a single canonical pair. All other bilingual class pairs are **deprecated** and must be migrated if encountered.

## Deprecated classes — DO NOT CREATE

| Deprecated          | Migrate to | Rationale |
|---------------------|------------|-----------|
| `t-th`, `t-en`      | `lang-th`, `lang-en` | Created by AI during hotfix |
| `th-text`, `en-text`| `lang-th`, `lang-en` | Legacy hero pattern |
| `lang-th-only`, `lang-en-only` | `lang-th`, `lang-en` | Older variants |

The validator (`scripts/validate-knowledge-hub.js` C8) will FAIL the build if any of these appear.

## Correct usage

### Simple inline bilingual text

```html
<button>
  <span class="lang-th">ทั้งหมด (98)</span>
  <span class="lang-en">All (98)</span>
</button>
```

### Paragraphs

```html
<p>
  <span class="lang-th">บทความกฎหมายธุรกิจ โดย Khun Tae</span>
  <span class="lang-en">Business law articles by Khun Tae</span>
</p>
```

### Links

```html
<a href="...">
  <span class="lang-th">อ่านต่อ →</span>
  <span class="lang-en">Read more →</span>
</a>
```

### DO NOT nest or mix

```html
<!-- BAD: mixing conventions -->
<span class="lang-th t-th">...</span>

<!-- BAD: nested bilingual -->
<span class="lang-th"><span class="lang-en">...</span></span>
```

## CSS (canonical — already in knowledge-hub.html)

```css
body[data-lang="th"] .lang-en { display: none; }
body[data-lang="en"] .lang-th { display: none; }
```

The `body[data-lang]` attribute is the only state source. Do not create alternate toggle mechanisms.

## JavaScript toggle (canonical)

```js
function setSiteLang(lang) {
  document.body.setAttribute('data-lang', lang);
  try { localStorage.setItem('las_site_lang', lang); } catch (e) {}
}
```

## Enforcement

- **Local:** `.git/hooks/pre-commit` runs `scripts/validate-knowledge-hub.js` — blocks commits that introduce deprecated classes
- **CI:** `.github/workflows/validate.yml` runs the same validator on every push/PR — blocks merges
- **Manual audit:** `node scripts/validate-knowledge-hub.js` anytime

## For AI sessions (Claude Code, Cowork, Gemini, etc.)

When editing any HTML file in this repository:

1. **Always** use `.lang-th` / `.lang-en` — never invent a new pair
2. **Always** `git pull --rebase origin main` before editing
3. **Always** run `node scripts/validate-knowledge-hub.js` before commit
4. If the validator fails with C8, **migrate** the deprecated classes — do not disable the check

## Migration playbook

If you need to migrate a file that has deprecated classes:

```bash
# Dry-run first — see what would change
grep -c 'class="[^"]*\bt-th\b' your-file.html

# Migrate (example for t-th → lang-th)
python -X utf8 -c "
s = open('your-file.html', encoding='utf-8').read()
s = s.replace('class=\"t-th\"', 'class=\"lang-th\"')
s = s.replace('class=\"t-en\"', 'class=\"lang-en\"')
open('your-file.html', 'w', encoding='utf-8').write(s)
"

# Verify
node scripts/validate-knowledge-hub.js
```

---

*This document is the single source of truth for bilingual class usage. Changes require CEO approval.*
