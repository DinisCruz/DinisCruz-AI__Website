#!/usr/bin/env node
// diniscruz.ai pre-release gate (adapted from open-source.sgit.ai). Run from anywhere: node admin/build/validate.js
// Checks, in order:
//   1. version agreement — admin/build/version.txt vs every page's version badge,
//      the versions table and llms.txt
//   2. internal links — every relative href/src in every .html file resolves to a
//      file in the tree (fragments stripped; external and mailto links skipped)
//   3. canonical host — every <link rel="canonical"> and og:url points at the host
//      in CNAME
//   4. markdown twins — every .html has a .md twin, and llms-full.txt mentions
//      every page. This site's whole agent-discovery argument rests on the twin
//      existing at every URL, so a missing one is a release-stopping defect here
//      rather than a nice-to-have. (build.py writes them; CI separately
//      fails if the committed twins are stale.)
//   5. licence footers — every raw markdown document under briefs/ and every
//      generated twin carries the CC BY 4.0 line. The site holds others to
//      declaring their licensing; it does not get to be sloppy about its own.
//   6. key-leak tripwire — nothing in the tree may look like an sgit vault key
//      (a >=20-char passphrase joined by a colon to a uuid-shaped id).
// Any failure exits 1: no tag, no publish.
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const errors = [];

function walk(dir, out = []) {
  for (const name of fs.readdirSync(dir)) {
    if (name === '.git' || name === '.github' || name === 'node_modules' || name === '.sg_vault' || name === 'content') continue;
    const p = path.join(dir, name);
    const st = fs.statSync(p);
    if (st.isDirectory()) walk(p, out);
    else out.push(p);
  }
  return out;
}

const files = walk(ROOT);
const htmlFiles = files.filter(f => f.endsWith('.html'));
// redirect stubs (about.html) carry a canonical but are not pages: no twin, no nav
const isStub = f => /http-equiv="refresh"/.test(fs.readFileSync(f, 'utf8'));
const pageFiles = htmlFiles.filter(f => !isStub(f));

// --- 1. version agreement -------------------------------------------------
const VERSION = fs.readFileSync(path.join(ROOT, 'admin/build/version.txt'), 'utf8').trim();
if (!/^v\d+\.\d+\.\d+$/.test(VERSION)) {
  errors.push(`version.txt does not carry a vX.Y.Z version: "${VERSION}"`);
}
for (const f of htmlFiles) {
  const t = fs.readFileSync(f, 'utf8');
  const badges = [...t.matchAll(/class="ver"[^>]*>(v\d+\.\d+\.\d+)</g)].map(m => m[1]);
  for (const b of badges) if (b !== VERSION) {
    errors.push(`${path.relative(ROOT, f)}: version badge ${b} != ${VERSION}`);
  }
}
for (const extra of ['llms.txt', 'llms-full.txt']) {
  const p = path.join(ROOT, extra);
  if (!fs.existsSync(p)) { errors.push(`${extra} is missing`); continue; }
  if (!fs.readFileSync(p, 'utf8').includes(VERSION)) errors.push(`${extra} does not mention ${VERSION}`);
}
const versPath = path.join(ROOT, 'admin/versions.html');
const versTable = fs.existsSync(versPath) ? fs.readFileSync(versPath, 'utf8') : '';
if (!versTable.includes(`class="vnum">${VERSION}<`)) {
  errors.push(`admin/versions.html has no row for ${VERSION}`);
}
// each release appears exactly once — a blanket version-bump sed that touches
// the history table produces duplicates, which shipped once on a sibling site
const rows = [...versTable.matchAll(/class="vnum">(v\d+\.\d+\.\d+)</g)].map(m => m[1]);
for (const v of rows) if (rows.filter(x => x === v).length > 1) {
  errors.push(`admin/versions.html lists ${v} more than once`);
  break;
}

// --- 2. internal links ----------------------------------------------------
for (const f of htmlFiles) {
  const t = fs.readFileSync(f, 'utf8');
  const dir = path.dirname(f);
  for (const m of t.matchAll(/(?:href|src)="([^"#]+)(?:#[^"]*)?"/g)) {
    const target = m[1];
    if (/^(https?:|mailto:|data:|\/\/)/.test(target) || target === '') continue;
    const resolved = target.startsWith('/') ? path.join(ROOT, target) : path.resolve(dir, target);
    if (!fs.existsSync(resolved)) {
      errors.push(`${path.relative(ROOT, f)}: broken link -> ${target}`);
    }
  }
}

// --- 3. canonical host ----------------------------------------------------
const HOST = fs.readFileSync(path.join(ROOT, 'CNAME'), 'utf8').trim();
if (!/^[a-z0-9.-]+$/.test(HOST)) errors.push(`CNAME does not carry a hostname: "${HOST}"`);
for (const f of htmlFiles) {
  const t = fs.readFileSync(f, 'utf8');
  const claimed = [
    ...[...t.matchAll(/<link[^>]+rel="canonical"[^>]+href="([^"]+)"/g)].map(m => m[1]),
    ...[...t.matchAll(/<meta[^>]+property="og:url"[^>]+content="([^"]+)"/g)].map(m => m[1]),
  ];
  for (const url of claimed) if (!url.startsWith(`https://${HOST}/`)) {
    errors.push(`${path.relative(ROOT, f)}: canonical/og:url is not on ${HOST} -> ${url}`);
  }
  // every page must declare where it canonically lives
  if (!/rel="canonical"/.test(t)) {
    errors.push(`${path.relative(ROOT, f)}: no canonical link`);
  }
}

// --- 4. markdown twins ----------------------------------------------------
const llmsFull = fs.existsSync(path.join(ROOT, 'llms-full.txt'))
  ? fs.readFileSync(path.join(ROOT, 'llms-full.txt'), 'utf8') : '';
const llms = fs.existsSync(path.join(ROOT, 'llms.txt'))
  ? fs.readFileSync(path.join(ROOT, 'llms.txt'), 'utf8') : '';
for (const f of pageFiles) {
  const rel = path.relative(ROOT, f).split(path.sep).join('/');
  if (rel === '404.html') continue;
  const twin = f.replace(/\.html$/, '.md');
  if (!fs.existsSync(twin)) {
    errors.push(`${rel}: no markdown twin (run admin/build/build.py)`);
    continue;
  }
  const mdRel = rel.replace(/\.html$/, '.md');
  if (!llmsFull.includes(`PAGE: /${rel}`)) {
    errors.push(`llms-full.txt does not carry ${rel}`);
  }
  if (!llms.includes(mdRel)) {
    errors.push(`llms.txt does not list ${mdRel}`);
  }
}

// --- 5. licence footers ---------------------------------------------------
const CCBY = 'Creative Commons Attribution 4.0 International licence (CC BY 4.0)';
for (const f of files) {
  if (!f.endsWith('.md')) continue;
  const rel = path.relative(ROOT, f).split(path.sep).join('/');
  if (rel === 'README.md' || rel.endsWith('/README.md')) continue;
  if (!fs.readFileSync(f, 'utf8').includes(CCBY)) {
    errors.push(`${rel}: no CC BY 4.0 licence line`);
  }
}

// --- 6. key-leak tripwire -------------------------------------------------
const KEY_SHAPE = /[A-Za-z0-9_-]{20,}:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/;
for (const f of files) {
  if (/\.(png|jpg|jpeg|gif|webp|ico|woff2?|zip)$/.test(f)) continue;
  const t = fs.readFileSync(f, 'utf8');
  if (KEY_SHAPE.test(t)) {
    errors.push(`${path.relative(ROOT, f)}: contains a vault-key-shaped string`);
  }
}

// --- 7. search essentials -------------------------------------------------
// Every indexable page: a description, a title, one h1, preview-friendly robots,
// a share image, and a <loc> in sitemap.xml equal to its canonical URL.
const sitemapXml = fs.existsSync(path.join(ROOT, 'sitemap.xml'))
  ? fs.readFileSync(path.join(ROOT, 'sitemap.xml'), 'utf8') : '';
if (!sitemapXml) errors.push('sitemap.xml is missing');
const locs = new Set([...sitemapXml.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1]));
for (const f of pageFiles) {
  const rel = path.relative(ROOT, f).split(path.sep).join('/');
  const t = fs.readFileSync(f, 'utf8');
  if (/name="robots" content="noindex/.test(t)) continue;
  const canon = (t.match(/<link rel="canonical" href="([^"]+)"/) || [])[1];
  if (canon && !locs.has(canon)) errors.push(`${rel}: canonical ${canon} is not in sitemap.xml`);
  const desc = (t.match(/<meta name="description" content="([^"]*)"/) || [])[1] || '';
  if (desc.length < 50) errors.push(`${rel}: meta description missing or under 50 characters`);
  if (!/<title>[^<]{10,}<\/title>/.test(t)) errors.push(`${rel}: title missing or too short`);
  if ((t.match(/<h1[\s>]/g) || []).length !== 1) errors.push(`${rel}: expected exactly one <h1>`);
  if (!/name="robots" content="index, follow, max-snippet:-1/.test(t)) errors.push(`${rel}: no robots preview directives`);
  if (!/property="og:image"/.test(t)) errors.push(`${rel}: no og:image`);
}
for (const loc of locs) {
  const rel = loc.replace(`https://${HOST}/`, '') || 'index.html';
  if (!fs.existsSync(path.join(ROOT, rel))) errors.push(`sitemap.xml lists ${loc}, which has no file`);
}

// --- report ---------------------------------------------------------------
if (errors.length) {
  console.error(`validate: ${errors.length} error(s)`);
  for (const e of errors) console.error('  ✗ ' + e);
  process.exit(1);
}
console.log(`validate: OK — ${VERSION} on ${HOST}, ${htmlFiles.length} pages, `
  + `every page has a markdown twin, links resolve, no key-shaped strings`);
