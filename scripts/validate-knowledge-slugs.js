#!/usr/bin/env node
/*
 * validate-knowledge-slugs.js — exact public Knowledge route/registry gate
 *
 * This validator is intentionally dependency-free and offline. It proves that
 * a series' file names, metadata, redirect stubs, indexes, catalog pages and
 * sitemap agree with the files that actually exist in this checkout. It does
 * not treat a title or a link found on one page as proof that the target file
 * exists.
 *
 * Usage:
 *   node scripts/validate-knowledge-slugs.js --all
 *   node scripts/validate-knowledge-slugs.js --slug las-share-01.html
 *   node scripts/validate-knowledge-slugs.js --root /path/to/checkout --slug ...
 *
 * Exit 0 only when every requested check passes. A missing page, malformed
 * JSON-LD, wrong canonical/og:url, missing breadcrumb, missing adjacent link,
 * stale registry/count, or collision is a hard failure.
 */

'use strict';

const fs = require('fs');
const path = require('path');

const BASE = 'https://thundthornthep-ai.github.io';
const BASE_HOST = 'thundthornthep-ai.github.io';
const SERIES = [
  { key: 'share', prefix: 'las-share', label: 'LAS Share' },
  { key: 'shield', prefix: 'las-shield', label: 'LAS Shield' },
  { key: 'cc', prefix: 'las-cc', label: 'LAS C&C' },
  { key: 'upsize', prefix: 'las-upsize', label: 'LAS UP' },
  { key: 'invest', prefix: 'las-invest', label: 'LAS INVEST' },
];

const argv = process.argv.slice(2);
let root = path.resolve(__dirname, '..');
let all = false;
const requestedSlugs = [];

function usageError(message) {
  console.error(`[SLUG-GATE] ERROR: ${message}`);
  console.error('Usage: node scripts/validate-knowledge-slugs.js [--all | --slug <slug>] [--root <dir>]');
  process.exit(1);
}

for (let i = 0; i < argv.length; i += 1) {
  const arg = argv[i];
  if (arg === '--all') {
    all = true;
  } else if (arg === '--slug') {
    if (!argv[i + 1]) usageError('--slug requires a value');
    requestedSlugs.push(argv[++i]);
  } else if (arg === '--root') {
    if (!argv[i + 1]) usageError('--root requires a directory');
    root = path.resolve(argv[++i]);
  } else if (arg === '--help' || arg === '-h') {
    console.log('Usage: node scripts/validate-knowledge-slugs.js [--all | --slug <slug>] [--root <dir>]');
    process.exit(0);
  } else {
    usageError(`unknown argument: ${arg}`);
  }
}

if (all && requestedSlugs.length) usageError('--all cannot be combined with --slug');
if (!all && requestedSlugs.length === 0) all = true;

const results = [];
function pass(id, message) {
  results.push({ id, ok: true, message });
}
function fail(id, message, detail) {
  results.push({ id, ok: false, message, detail });
}
function list(values) {
  return values.length ? values.join(', ') : '(none)';
}

function read(rel) {
  const file = path.join(root, rel);
  if (!fs.existsSync(file)) return null;
  try {
    return fs.readFileSync(file, 'utf8');
  } catch (error) {
    fail('FS', `cannot read ${rel}`, error.message);
    return null;
  }
}

function exists(rel) {
  return fs.existsSync(path.join(root, rel));
}

function attrs(tag) {
  const out = {};
  const re = /([:\w-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g;
  let match;
  while ((match = re.exec(tag)) !== null) out[match[1].toLowerCase()] = match[2] ?? match[3] ?? '';
  return out;
}

function tags(html, name) {
  const re = new RegExp(`<${name}\\b[^>]*>`, 'gi');
  return [...html.matchAll(re)].map((match) => match[0]);
}

function firstTagValue(html, name, predicate) {
  for (const tag of tags(html, name)) {
    const values = attrs(tag);
    if (!predicate || predicate(values)) return values;
  }
  return null;
}

function linkValue(html, rel) {
  const item = firstTagValue(html, 'link', (values) => (values.rel || '').toLowerCase() === rel);
  return item ? item.href || '' : '';
}

function metaValue(html, key, value) {
  const item = firstTagValue(html, 'meta', (values) => (values[key] || '').toLowerCase() === value.toLowerCase());
  return item ? item.content || '' : '';
}

function titleValue(html) {
  const match = html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i);
  return match ? match[1].replace(/\s+/g, ' ').trim() : '';
}

function typeIncludes(node, expected) {
  if (!node || typeof node !== 'object') return false;
  const type = node['@type'];
  return Array.isArray(type) ? type.includes(expected) : type === expected;
}

function allJsonLdNodes(value) {
  const nodes = [];
  function visit(node) {
    if (Array.isArray(node)) {
      node.forEach(visit);
    } else if (node && typeof node === 'object') {
      nodes.push(node);
      if (Array.isArray(node['@graph'])) node['@graph'].forEach(visit);
    }
  }
  visit(value);
  return nodes;
}

function parseJsonLd(html, rel) {
  const scripts = [];
  const re = /<script\b[^>]*type\s*=\s*["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  let match;
  while ((match = re.exec(html)) !== null) scripts.push(match[1].trim());
  const nodes = [];
  let errors = 0;
  scripts.forEach((text, index) => {
    if (!text) {
      errors += 1;
      fail('JSON-LD', `${rel} has empty JSON-LD block #${index + 1}`);
      return;
    }
    try {
      nodes.push(...allJsonLdNodes(JSON.parse(text)));
    } catch (error) {
      errors += 1;
      fail('JSON-LD', `${rel} has invalid JSON-LD block #${index + 1}`, error.message);
    }
  });
  return { nodes, scripts, errors };
}

function hrefs(html) {
  const values = [];
  const re = /<a\b[^>]*>/gi;
  for (const match of html.matchAll(re)) {
    const value = attrs(match[0]).href;
    if (value) values.push(value);
  }
  return values;
}

function pathFromUrl(value, pageUrl = `${BASE}/`) {
  if (!value) return null;
  try {
    const url = new URL(value, pageUrl);
    if (url.hostname !== BASE_HOST || url.username || url.password) return null;
    return url.pathname.replace(/^\/+/, '');
  } catch (_) {
    return null;
  }
}

function pathsFromLinks(html, pageUrl) {
  return hrefs(html).map((value) => pathFromUrl(value, pageUrl)).filter(Boolean);
}

function expectedArticlePath(series, number) {
  return `articles/${series.prefix}-${String(number).padStart(2, '0')}.html`;
}

function expectedArticleUrl(series, number) {
  return `${BASE}/${expectedArticlePath(series, number)}`;
}

function expectedIndexPath(series) {
  return `articles/${series.prefix}-index.html`;
}

function discover(series) {
  const dir = path.join(root, 'articles');
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter((name) => new RegExp(`^${series.prefix}-(\\d{2})\\.html$`).test(name))
    .map((name) => ({
      name,
      number: Number(name.match(/-(\d{2})\.html$/)[1]),
      rel: `articles/${name}`,
    }))
    .sort((a, b) => a.number - b.number);
}

function normalizeRequestedSlug(value) {
  const raw = String(value).replace(/^\/+/, '');
  const withoutArticles = raw.startsWith('articles/') ? raw.slice('articles/'.length) : raw;
  return withoutArticles;
}

const discovered = new Map(SERIES.map((series) => [series.key, discover(series)]));
const selected = [];
if (all) {
  SERIES.forEach((series) => discovered.get(series.key).forEach((article) => selected.push({ series, article })));
} else {
  for (const value of requestedSlugs) {
    const slug = normalizeRequestedSlug(value);
    const match = SERIES.flatMap((series) => discovered.get(series.key).map((article) => ({ series, article })))
      .find(({ article }) => article.name === slug);
    if (!match) fail('TARGET', `requested slug does not exist in articles/: ${value}`);
    else selected.push(match);
  }
}

// Detect duplicate logical URLs before checking individual documents. A
// duplicate canonical is a publication collision even when filenames differ.
{
  const canonicalOwners = new Map();
  for (const series of SERIES) {
    for (const article of discovered.get(series.key)) {
      const html = read(article.rel);
      if (!html) continue;
      const canonical = linkValue(html, 'canonical');
      if (!canonical) continue;
      const owners = canonicalOwners.get(canonical) || [];
      owners.push(article.rel);
      canonicalOwners.set(canonical, owners);
    }
  }
  const collisions = [...canonicalOwners.entries()]
    .filter(([, owners]) => owners.length > 1)
    .map(([canonical, owners]) => `${canonical} <- ${owners.join(' | ')}`);
  if (collisions.length) fail('COLLISION', 'duplicate canonical URLs detected', list(collisions));
  else pass('COLLISION', 'no duplicate article canonical URLs');
}

function checkSeriesStructure(series, articles) {
  const indexRel = expectedIndexPath(series);
  const indexHtml = read(indexRel);
  if (!indexHtml) {
    fail('INDEX', `${series.label} index is missing: ${indexRel}`);
  } else {
    const expected = new Set(articles.map((article) => expectedArticlePath(series, article.number)));
    const linked = new Set(pathsFromLinks(indexHtml, `${BASE}/${indexRel}`));
    const missing = [...expected].filter((item) => !linked.has(item));
    const extra = [...linked].filter((item) => new RegExp(`^articles/${series.prefix}-\\d{2}\\.html$`).test(item) && !expected.has(item));
    if (missing.length) fail('INDEX', `${series.label} index omits actual article(s)`, list(missing));
    if (extra.length) fail('INDEX', `${series.label} index links to non-existent article(s)`, list(extra));
    if (!missing.length && !extra.length) pass('INDEX', `${series.label} index covers all ${articles.length} actual article(s)`);

    const ld = parseJsonLd(indexHtml, indexRel);
    const collections = ld.nodes.filter((node) => typeIncludes(node, 'CollectionPage'));
    const counts = collections.map((node) => node.numberOfItems).filter((value) => value !== undefined);
    const badCounts = counts.filter((value) => Number(value) !== articles.length);
    if (!collections.length || !counts.length) {
      fail('COUNT', `${indexRel} has no CollectionPage numberOfItems for actual count ${articles.length}`);
    } else if (badCounts.length) {
      fail('COUNT', `${indexRel} numberOfItems disagrees with files`, `expected ${articles.length}, found ${list(badCounts.map(String))}`);
    } else {
      pass('COUNT', `${series.label} count ${articles.length} matches CollectionPage JSON-LD`);
    }
  }

  const numbers = articles.map((article) => article.number);
  const expectedNumbers = Array.from({ length: articles.length }, (_, index) => index + 1);
  if (numbers.length === 0) fail('SEQUENCE', `${series.label} has no article files in articles/`);
  else if (numbers.some((value, index) => value !== expectedNumbers[index])) {
    fail('SEQUENCE', `${series.label} episode numbers have a gap or duplicate`, `actual ${list(numbers.map(String))}; expected ${list(expectedNumbers.map(String))}`);
  } else {
    pass('SEQUENCE', `${series.label} episode filenames are contiguous from 01 to ${String(articles.length).padStart(2, '0')}`);
  }

  const hub = read('knowledge-hub.html');
  if (!hub) {
    fail('HUB', 'knowledge-hub.html is missing');
  } else {
    const linked = new Set(pathsFromLinks(hub, `${BASE}/`));
    const missing = articles.map((article) => expectedArticlePath(series, article.number)).filter((item) => !linked.has(item));
    if (missing.length) fail('HUB', `${series.label} is missing from knowledge-hub.html`, list(missing));
    else pass('HUB', `knowledge-hub.html links all ${series.label} article files`);
  }

  const allContent = read('all-content.html');
  if (!allContent) {
    fail('ALL-CONTENT', 'all-content.html is missing');
  } else {
    const linked = new Set(pathsFromLinks(allContent, `${BASE}/`));
    const missing = articles.map((article) => expectedArticlePath(series, article.number)).filter((item) => !linked.has(item));
    if (missing.length) fail('ALL-CONTENT', `all-content.html omits ${series.label} article file(s)`, list(missing));
    else pass('ALL-CONTENT', `all-content.html links all ${series.label} article files`);
  }

  const sitemap = read('sitemap.xml');
  if (!sitemap) {
    fail('SITEMAP', 'sitemap.xml is missing');
  } else {
    const locs = [...sitemap.matchAll(/<loc>\s*([^<]+?)\s*<\/loc>/gi)]
      .map((match) => pathFromUrl(match[1].trim(), `${BASE}/`)).filter(Boolean);
    const required = articles.map((article) => expectedArticlePath(series, article.number));
    required.push(indexRel);
    const missing = required.filter((item) => !locs.includes(item));
    if (missing.length) fail('SITEMAP', `sitemap.xml omits ${series.label} route(s)`, list(missing));
    else pass('SITEMAP', `sitemap.xml contains ${series.label} article routes and index`);
  }

  for (const article of articles) {
    const rootRel = `${series.prefix}-${String(article.number).padStart(2, '0')}.html`;
    const rootHtml = read(rootRel);
    const publicUrl = expectedArticleUrl(series, article.number);
    const proxyUrl = `https://laslegal.tech/hub/articles/${series.prefix}-${String(article.number).padStart(2, '0')}.html`;
    if (!rootHtml) {
      fail('REDIRECT', `${series.label} redirect stub is missing: ${rootRel}`);
      continue;
    }
    const canonical = linkValue(rootHtml, 'canonical');
    const refresh = firstTagValue(rootHtml, 'meta', (values) => (values['http-equiv'] || '').toLowerCase() === 'refresh');
    const robots = metaValue(rootHtml, 'name', 'robots').toLowerCase();
    const hasPublic = rootHtml.includes(publicUrl);
    const hasProxy = rootHtml.includes(proxyUrl);
    const ok = canonical === publicUrl && !!refresh && refresh.content.includes(proxyUrl) && robots.includes('noindex') && hasPublic && hasProxy;
    if (!ok) {
      const problems = [];
      if (canonical !== publicUrl) problems.push(`canonical=${canonical || '(missing)'}`);
      if (!refresh || !refresh.content.includes(proxyUrl)) problems.push('meta refresh does not target LAS proxy');
      if (!robots.includes('noindex')) problems.push('robots is not noindex');
      if (!hasPublic) problems.push('public article link missing');
      if (!hasProxy) problems.push('LAS proxy link missing');
      fail('REDIRECT', `${rootRel} does not preserve the exact article route`, problems.join('; '));
    } else if (selected.some((item) => item.series.key === series.key && item.article.name === article.name) || all) {
      pass('REDIRECT', `${rootRel} points to the exact public article and LAS proxy`);
    }
  }
}

function checkArticle(series, article, articles) {
  const rel = article.rel;
  const html = read(rel);
  if (!html) {
    fail('ARTICLE', `${rel} is missing or unreadable`);
    return;
  }
  const expectedUrl = expectedArticleUrl(series, article.number);
  const expectedIndexUrl = `${BASE}/${expectedIndexPath(series)}`;
  const canonical = linkValue(html, 'canonical');
  const ogUrl = metaValue(html, 'property', 'og:url');
  if (canonical !== expectedUrl) fail('META', `${rel} canonical is not exact`, `expected ${expectedUrl}; found ${canonical || '(missing)'}`);
  else pass('META', `${rel} canonical matches exact filename`);
  if (ogUrl !== expectedUrl) fail('META', `${rel} og:url is not exact`, `expected ${expectedUrl}; found ${ogUrl || '(missing)'}`);
  else pass('META', `${rel} og:url matches exact filename`);

  const ld = parseJsonLd(html, rel);
  const articleNodes = ld.nodes.filter((node) => typeIncludes(node, 'Article'));
  if (!articleNodes.length) {
    fail('JSON-LD', `${rel} has no Article JSON-LD node`);
  } else {
    const wrongMain = articleNodes
      .map((node) => {
        const value = node.mainEntityOfPage;
        return typeof value === 'string' ? value : value && (value['@id'] || value.url);
      })
      .filter((value) => value !== expectedUrl);
    if (wrongMain.length || articleNodes.some((node) => !node.mainEntityOfPage)) {
      fail('JSON-LD', `${rel} Article JSON-LD mainEntityOfPage is not exact`, `expected ${expectedUrl}`);
    } else {
      pass('JSON-LD', `${rel} Article mainEntityOfPage matches canonical`);
    }
  }

  const crumbs = ld.nodes.filter((node) => typeIncludes(node, 'BreadcrumbList'));
  const visibleBreadcrumb = /class\s*=\s*["'][^"']*\bbreadcrumb\b/i.test(html) && pathsFromLinks(html, `${BASE}/${rel}`).includes(expectedIndexPath(series));
  const jsonBreadcrumb = crumbs.some((crumb) => {
    const items = Array.isArray(crumb.itemListElement) ? crumb.itemListElement : [];
    return items.some((item) => {
      const value = item && item.item;
      const itemUrl = typeof value === 'string' ? value : value && (value['@id'] || value.url);
      return pathFromUrl(itemUrl, `${BASE}/${rel}`) === expectedIndexPath(series);
    });
  });
  if (!visibleBreadcrumb && !jsonBreadcrumb) fail('BREADCRUMB', `${rel} has no breadcrumb pointing to ${expectedIndexPath(series)}`);
  else pass('BREADCRUMB', `${rel} breadcrumb points to its series index`);

  const pageLinks = pathsFromLinks(html, `${BASE}/${rel}`);
  if (!pageLinks.includes(expectedIndexPath(series)) && !ld.nodes.some((node) => {
    const part = node.isPartOf;
    const value = typeof part === 'string' ? part : part && (part.url || part['@id']);
    return pathFromUrl(value, `${BASE}/${rel}`) === expectedIndexPath(series);
  })) {
    fail('SERIES-LINK', `${rel} does not link to ${expectedIndexPath(series)}`);
  } else {
    pass('SERIES-LINK', `${rel} links to its series index`);
  }

  const position = articles.findIndex((item) => item.name === article.name);
  const previous = position > 0 ? expectedArticlePath(series, articles[position - 1].number) : null;
  const next = position < articles.length - 1 ? expectedArticlePath(series, articles[position + 1].number) : null;
  const missingNav = [];
  if (previous && !pageLinks.includes(previous)) missingNav.push(`previous=${previous}`);
  if (next && !pageLinks.includes(next)) missingNav.push(`next=${next}`);
  if (missingNav.length) fail('NAV', `${rel} is missing adjacent series navigation`, list(missingNav));
  else pass('NAV', `${rel} has correct adjacent series navigation`);

  const th = [];
  const en = [];
  for (const tag of tags(html, 'link')) {
    const values = attrs(tag);
    if ((values.rel || '').toLowerCase() === 'alternate' && values.hreflang) th.push({ lang: values.hreflang.toLowerCase(), href: values.href || '' });
  }
  const expectedAlternates = {
    th: expectedUrl,
    'x-default': expectedUrl,
  };
  const badAlternates = Object.entries(expectedAlternates)
    .filter(([lang, url]) => !th.some((item) => item.lang === lang && item.href === url))
    .map(([lang, url]) => `${lang}=${url}`);
  const invalidAlternates = th.filter((item) => item.lang === 'en' && item.href !== `${BASE}/en/${rel}`).map((item) => `en=${item.href}`);
  if (badAlternates.length || invalidAlternates.length) {
    fail('HREFLANG', `${rel} hreflang map is incomplete or wrong`, list([...badAlternates, ...invalidAlternates]));
  } else {
    pass('HREFLANG', `${rel} has exact th/x-default hreflang (and valid en when present)`);
  }
}

const seriesToCheck = new Set(selected.map((item) => item.series.key));
for (const series of SERIES) {
  if (!seriesToCheck.has(series.key)) continue;
  checkSeriesStructure(series, discovered.get(series.key));
  const articleSet = new Set(selected.filter((item) => item.series.key === series.key).map((item) => item.article.name));
  discovered.get(series.key).forEach((article) => {
    if (all || articleSet.has(article.name)) checkArticle(series, article, discovered.get(series.key));
  });
}

// Exact filename check for requested targets (the discovery regex itself is
// deliberately narrow so an accidental unnumbered alias cannot be published).
for (const item of selected) {
  const expected = `articles/${item.series.prefix}-${String(item.article.number).padStart(2, '0')}.html`;
  if (item.article.rel !== expected) fail('FILENAME', `${item.article.rel} is not the exact registered filename`, `expected ${expected}`);
  else pass('FILENAME', `${item.article.rel} matches the registered slug`);
}

console.log(`\nValidating Knowledge routes in ${root}`);
results.forEach((result) => {
  const label = result.ok ? 'PASS' : 'FAIL';
  console.log(`  [${result.id}] ${label}  ${result.message}`);
  if (!result.ok && result.detail) console.log(`        ${result.detail}`);
});
const failed = results.filter((result) => !result.ok);
console.log(`\n${results.length - failed.length} passed, ${failed.length} failed`);
if (failed.length) {
  console.error('VALIDATION FAILED — do not publish until every requested gate passes.');
  process.exit(1);
}
console.log('All exact-slug/series checks passed.');
