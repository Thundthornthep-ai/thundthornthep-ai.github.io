#!/usr/bin/env node
/*
 * validate-knowledge-hub.js — Sustainability guard for knowledge-hub.html
 *
 * Zero dependencies — runs on any Node 14+. Used by:
 *   - local: .git/hooks/pre-commit
 *   - CI:    .github/workflows/validate.yml
 *
 * Exit codes:
 *   0 = all checks pass
 *   1 = one or more checks failed (blocks commit / CI)
 *
 * Checks performed:
 *   C1  JS syntax of every non-JSON <script> block
 *   C2  No `event.target` in code called from inline onclick
 *   C3  Every filter button maps to existing content (no dead buttons)
 *   C4  Filter button label counts match actual data-category counts
 *   C5  .lang-th / .lang-en span count balance
 *   C6  All .article-card have data-category
 *   C7  Filter buttons all use `this` parameter (no window.event reliance)
 *   C8  No deprecated bilingual classes (.t-th, .t-en, .th-text, .en-text)
 *
 * Usage:
 *   node scripts/validate-knowledge-hub.js [path/to/knowledge-hub.html]
 */

'use strict';
const fs = require('fs');
const path = require('path');

const FILE = process.argv[2] || path.join(__dirname, '..', 'knowledge-hub.html');
const RED = '\x1b[31m', GREEN = '\x1b[32m', YELLOW = '\x1b[33m', RESET = '\x1b[0m', BOLD = '\x1b[1m';

if (!fs.existsSync(FILE)) {
  console.error(RED + 'File not found: ' + FILE + RESET);
  process.exit(1);
}

const html = fs.readFileSync(FILE, 'utf8');
const results = [];
const fail = (id, msg, detail) => results.push({ id, ok: false, msg, detail });
const pass = (id, msg) => results.push({ id, ok: true, msg });

// -------- C1: JS syntax of non-JSON script blocks --------
{
  const scriptRE = /<script(?![^>]*type="application\/ld\+json")(?![^>]*\ssrc=)[^>]*>([\s\S]*?)<\/script>/g;
  let m, idx = 0, errors = 0;
  while ((m = scriptRE.exec(html)) !== null) {
    const body = m[1];
    if (!body.trim()) continue;
    idx++;
    try {
      new Function(body);
    } catch (e) {
      errors++;
      fail('C1', 'JS syntax error in script block #' + idx, e.message);
    }
  }
  if (errors === 0) pass('C1', 'JS syntax OK (' + idx + ' script blocks)');
}

// -------- C2: No event.target in code --------
{
  const code = html
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/[^\n]*/g, '');
  if (/event\.target/.test(code)) {
    fail('C2', 'Found event.target in code — use `this` parameter passed from inline onclick instead');
  } else {
    pass('C2', 'No fragile event.target usage');
  }
}

// -------- C3 & C4 & C7: Filter button audit --------
{
  const cardCats = [...html.matchAll(/article-card"[^>]*\sdata-category="([^"]+)"/g)].map(m => m[1]);
  const seriesCats = [...html.matchAll(/series-section"[^>]*\sdata-category="([^"]+)"/g)].map(m => m[1]);
  const fwCats = [...html.matchAll(/las-fw-card\s+[a-z]+"\s+data-category="([^"]+)"/g)].map(m => m[1]);

  const cardCounts = {};
  cardCats.forEach(c => { cardCounts[c] = (cardCounts[c] || 0) + 1; });

  const allCats = new Set([...cardCats, ...seriesCats, ...fwCats, 'all']);

  const btnWithThis = [...html.matchAll(/filterArticles\('([^']+)',\s*this\)/g)].map(m => m[1]);
  const btnNoThis = [...html.matchAll(/filterArticles\('([^']+)'\)(?!\s*,\s*this)/g)].map(m => m[1]);

  if (btnNoThis.length > 0) {
    fail('C7', btnNoThis.length + ' filter buttons still call filterArticles without `this`',
      btnNoThis.join(', '));
  } else {
    pass('C7', 'All filter buttons use `this` parameter (' + btnWithThis.length + ' buttons)');
  }

  const dead = btnWithThis.filter(c => !allCats.has(c));
  if (dead.length > 0) {
    fail('C3', dead.length + ' dead filter button(s) map to missing content', dead.join(', '));
  } else {
    pass('C3', 'All ' + btnWithThis.length + ' filter buttons map to existing content');
  }

  const btnLabelRE = /filterArticles\('([^']+)',\s*this\)[^>]*>(<span class="lang-th">([^<]+)<\/span><span class="lang-en">([^<]+)<\/span>)/g;
  const btns = [...html.matchAll(btnLabelRE)];
  const mismatches = [];
  btns.forEach(([, cat, , th, en]) => {
    if (cat === 'all' || cat.startsWith('las-') || cat === 'bkk') return;
    const expected = cardCounts[cat] || 0;
    const need = '(' + expected + ')';
    if (!th.includes(need) || !en.includes(need)) {
      mismatches.push(cat + ': expected ' + need + ', got th="' + th + '" en="' + en + '"');
    }
  });
  if (mismatches.length > 0) {
    fail('C4', mismatches.length + ' label count mismatch(es)', mismatches.join('\n  '));
  } else {
    pass('C4', 'All label counts match actual card counts (' + btns.length + ' buttons checked)');
  }
}

// -------- C5: lang-th / lang-en balance --------
{
  const thCount = (html.match(/class="lang-th"/g) || []).length;
  const enCount = (html.match(/class="lang-en"/g) || []).length;
  if (thCount !== enCount) {
    fail('C5', 'Unbalanced bilingual spans: lang-th=' + thCount + ', lang-en=' + enCount);
  } else {
    pass('C5', 'Bilingual span balance OK (' + thCount + ' pairs)');
  }
}

// -------- C6: every article-card has data-category --------
{
  const allCards = [...html.matchAll(/<article[^>]*class="article-card"[^>]*>/g)];
  const withCat = allCards.filter(m => /data-category="[^"]+"/.test(m[0]));
  if (withCat.length !== allCards.length) {
    fail('C6', (allCards.length - withCat.length) + ' article-card(s) missing data-category');
  } else {
    pass('C6', 'All ' + allCards.length + ' article-cards have data-category');
  }
}

// -------- C8: deprecated bilingual classes --------
{
  const deprecated = [
    { cls: 't-th', canonical: 'lang-th' },
    { cls: 't-en', canonical: 'lang-en' },
    { cls: 'th-text', canonical: 'lang-th' },
    { cls: 'en-text', canonical: 'lang-en' },
  ];
  const found = deprecated
    .map(({ cls, canonical }) => ({
      cls,
      canonical,
      count: (html.match(new RegExp('class="[^"]*\\b' + cls + '\\b[^"]*"', 'g')) || []).length,
    }))
    .filter(x => x.count > 0);
  if (found.length > 0) {
    fail('C8', 'Deprecated bilingual classes found — see docs/BILINGUAL-CONVENTION.md',
      found.map(f => f.cls + ' (' + f.count + 'x) -> use ' + f.canonical).join('\n  '));
  } else {
    pass('C8', 'No deprecated bilingual classes');
  }
}

// -------- Report --------
console.log('\n' + BOLD + 'Validating: ' + path.basename(FILE) + RESET + '\n');
const passed = results.filter(r => r.ok).length;
const failed = results.filter(r => !r.ok).length;

results.forEach(r => {
  const icon = r.ok ? (GREEN + 'PASS' + RESET) : (RED + 'FAIL' + RESET);
  console.log('  [' + r.id + '] ' + icon + '  ' + r.msg);
  if (!r.ok && r.detail) {
    console.log('        ' + YELLOW + r.detail + RESET);
  }
});

console.log('\n' + BOLD + passed + ' passed, ' + failed + ' failed' + RESET);

if (failed > 0) {
  console.log('\n' + RED + BOLD + 'VALIDATION FAILED' + RESET + ' -- fix the issues above before committing.');
  console.log('See ' + BOLD + 'docs/BILINGUAL-CONVENTION.md' + RESET + ' for the bilingual class standard.');
  process.exit(1);
}

console.log(GREEN + BOLD + 'All checks passed' + RESET + '\n');
process.exit(0);
