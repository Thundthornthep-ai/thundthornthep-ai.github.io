#!/usr/bin/env node
// validate-bkk-election.js — Fact-drift validator for BKK Council election 2569 pages
// Diffs HTML content in blog/bkk-council/ against canonical data-provenance.json.
// Usage: node scripts/validate-bkk-election.js [--file FILENAME]
// Exit 0 = pass, 1 = fail

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const BKK_DIR = path.join(ROOT, 'blog', 'bkk-council');
const PROVENANCE = path.join(BKK_DIR, 'data-provenance.json');

const COLORS = { reset: '\x1b[0m', bold: '\x1b[1m', red: '\x1b[31m', green: '\x1b[32m', yellow: '\x1b[33m', gray: '\x1b[90m' };
const c = (color, text) => `${COLORS[color]}${text}${COLORS.reset}`;

if (!fs.existsSync(PROVENANCE)) {
  console.error(c('red', `FATAL: ${PROVENANCE} not found`));
  process.exit(1);
}
const prov = JSON.parse(fs.readFileSync(PROVENANCE, 'utf8'));

const PAGES = ['campaign-tracker.html', 'campaign-dashboard.html', 'sk-candidate-guide.html'];

const CHECKS = [
  {
    id: 'E1',
    name: 'No "ม.109" for 90-day filing (should be ม.62)',
    run: (html) => {
      const matches = [];
      const regex = /(?:มาตรา|ม\.)\s*109/g;
      let m;
      while ((m = regex.exec(html)) !== null) {
        const ctx = html.substring(Math.max(0, m.index - 60), Math.min(html.length, m.index + 60));
        if (/90\s*วัน|ยื่นบัญชี/.test(ctx)) {
          matches.push({ line: html.substring(0, m.index).split('\n').length, ctx });
        }
      }
      return {
        pass: matches.length === 0,
        message: matches.length ? `Found ${matches.length} occurrence(s):\n${matches.map(x => `    line ${x.line}`).join('\n')}` : null,
        severity: 'error',
      };
    },
  },
  {
    id: 'E2',
    name: 'No "เพิกถอนสิทธิ มาตรา 63" (ม.63 is procedure, not penalty)',
    run: (html) => {
      const re = /เพิกถอนสิทธิ\s*(?:มาตรา|ม\.)\s*63\b/;
      const m = html.match(re);
      return {
        pass: !m,
        message: m ? `Found "${m[0]}" — ม.63 = กระบวนการสอบสวน. Use ม.128 for penalty of ม.62 violation.` : null,
        severity: 'error',
      };
    },
  },
  {
    id: 'E6',
    name: 'No "ม.63" + "ห้ามจัดเลี้ยง/มหรสพ" (ม.63 is not that — use ม.65(3)(4))',
    run: (html) => {
      const re = /(?:มาตรา|ม\.)\s*63[^0-9].{0,80}(ห้ามจัดเลี้ยง|ห้ามจัดงานรื่นเริง|ห้ามมหรสพ|จัดเลี้ยง)/;
      const m = html.match(re);
      return {
        pass: !m,
        message: m ? `Found "${m[0]}" — ม.63 = กระบวนการสอบสวนค่าใช้จ่าย · ห้ามจัดเลี้ยง/มหรสพ = ม.65(3)(4)` : null,
        severity: 'error',
      };
    },
  },
  {
    id: 'E7',
    name: 'No "ม.127" + "จำคุก 1-10 ปี" (that is ม.126 — ม.127 = 1-5 ปี)',
    run: (html) => {
      const re = /(?:มาตรา|ม\.)\s*127[^0-9].{0,80}(1\s*[-–]\s*10\s*ปี|จำคุก\s*1\s*[-–]\s*10)/;
      const m = html.match(re);
      return {
        pass: !m,
        message: m ? `Found "${m[0]}" — ม.127 = 1-5 ปี (ฝ่าฝืน ม.60 วรรคสาม) · 1-10 ปี คือ ม.126 (ฝ่าฝืน ม.65)` : null,
        severity: 'error',
      };
    },
  },
  {
    id: 'E8',
    name: 'No "ม.65(4)" + "มหรสพ" (มหรสพ = ม.65(3), not (4))',
    run: (html) => {
      const re = /(?:มาตรา|ม\.)\s*65\s*\(4\).{0,30}มหรสพ|มหรสพ.{0,30}(?:มาตรา|ม\.)\s*65\s*\(4\)/;
      const m = html.match(re);
      return {
        pass: !m,
        message: m ? `Found "${m[0]}" — มหรสพ = ม.65(3) · ม.65(4) = เลี้ยงหรือรับจะจัดเลี้ยง` : null,
        severity: 'error',
      };
    },
  },
  {
    id: 'E9',
    name: 'No "ม.49(5)" — ม.49 has only 4 subsections (1)-(4)',
    run: (html) => {
      const re = /(?:มาตรา|ม\.)\s*49\s*\(5\)/;
      const m = html.match(re);
      return {
        pass: !m,
        message: m ? `Found "${m[0]}" — ม.49 มี 4 ข้อย่อย (1)-(4) · ไม่มี (5) · ผู้ไม่ใช้สิทธิ = ม.39` : null,
        severity: 'error',
      };
    },
  },
  {
    id: 'E10',
    name: 'No "ม.54" for "ประกาศรายชื่อผู้สมัคร" (= ม.52 วรรค 3)',
    run: (html) => {
      const re = /(?:มาตรา|ม\.)\s*54[^0-9,].{0,60}ประกาศ(?:บัญชี)?รายชื่อผู้สมัคร|ประกาศ(?:บัญชี)?รายชื่อผู้สมัคร.{0,60}(?:มาตรา|ม\.)\s*54[^0-9,]/;
      const m = html.match(re);
      return {
        pass: !m,
        message: m ? `Found "${m[0]}" — ประกาศรายชื่อผู้สมัคร = ม.52 วรรค 3 · ม.54 = ห้ามเรียก/รับเงินเพื่อสมัคร` : null,
        severity: 'error',
      };
    },
  },
  {
    id: 'E11',
    name: 'No "ม.55" for "จับเบอร์/หมายเลขผู้สมัคร" (= ม.57)',
    run: (html) => {
      const re = /(?:มาตรา|ม\.)\s*55[^0-9].{0,80}(จับสลาก|หมายเลข(?:ประจำตัว)?ผู้สมัคร|เบอร์ผู้สมัคร)|(?:จับสลาก|หมายเลขประจำตัวผู้สมัคร).{0,60}(?:มาตรา|ม\.)\s*55[^0-9]/;
      const m = html.match(re);
      return {
        pass: !m,
        message: m ? `Found "${m[0]}" — การกำหนดหมายเลข/จับสลาก = ม.57 · ม.55 = ยื่นคำร้องกรณีไม่มีชื่อในประกาศ` : null,
        severity: 'error',
      };
    },
  },
  {
    id: 'E12',
    name: 'No "ม.62" + "1-10 ปี" or "200,000" (ม.62 no direct penalty — ม.128 is)',
    run: (html) => {
      const re = /(?:มาตรา|ม\.)\s*62[^0-9].{0,120}(1\s*[-–]\s*10\s*ปี|200,?000)/;
      const m = html.match(re);
      return {
        pass: !m,
        message: m ? `Found "${m[0]}" — ม.62 = procedure (ยื่นบัญชี 90 วัน) ไม่มีโทษโดยตรง · โทษอยู่ใน ม.128` : null,
        severity: 'error',
      };
    },
  },
  {
    id: 'E3',
    name: 'No stale "รอประกาศใหม่ 2569" text',
    run: (html) => {
      const m = html.match(/รอประกาศ.*กกต.*2569|รอประกาศใหม่.*2569/);
      return {
        pass: !m,
        message: m ? `Stale text: "${m[0]}" — ประกาศ 25 พ.ย. 2564 ข้อ 5 ยังใช้` : null,
        severity: 'warn',
      };
    },
  },
  {
    id: 'E4',
    name: 'No "950,000" tier (tier 2 is 900,000)',
    run: (html) => {
      const re = /950,?000/g;
      const lines = [];
      let m;
      while ((m = re.exec(html)) !== null) {
        lines.push(html.substring(0, m.index).split('\n').length);
      }
      return {
        pass: lines.length === 0,
        message: lines.length ? `950,000 at lines: ${lines.join(', ')}` : null,
        severity: 'warn',
      };
    },
  },
  {
    id: 'E5',
    name: 'No "22 พ.ค. 69" for term-end (should be 21 พ.ค.)',
    run: (html) => {
      const re = /22\s*พ\.ค\.\s*(?:69|2569)/g;
      const matches = [];
      let m;
      while ((m = re.exec(html)) !== null) {
        const ctx = html.substring(Math.max(0, m.index - 80), Math.min(html.length, m.index + 20));
        if (/วาระ|term/i.test(ctx)) {
          matches.push(html.substring(0, m.index).split('\n').length);
        }
      }
      return {
        pass: matches.length === 0,
        message: matches.length ? `"22 พ.ค." near "วาระ" at lines: ${matches.join(', ')} — should be 21 พ.ค. 2569` : null,
        severity: 'error',
      };
    },
  },
  {
    id: 'D1',
    name: 'Contains election day 28 มิ.ย. 2569',
    run: (html) => {
      const present = /28\s*มิ\.?ย\.?\s*(?:69|2569)/.test(html) || /วันเลือกตั้ง.*28\s*มิถุนายน\s*2569/.test(html);
      return { pass: present, message: present ? null : 'Missing election day 28 มิ.ย. 2569', severity: 'warn' };
    },
  },
  {
    id: 'D2',
    name: 'District dropdown total = 50',
    run: (html) => {
      const optRe = /<option[^>]*value="(820000|900000|1000000|1050000|1150000)"/g;
      const counts = {};
      let m;
      while ((m = optRe.exec(html)) !== null) {
        counts[m[1]] = (counts[m[1]] || 0) + 1;
      }
      const total = Object.values(counts).reduce((a, b) => a + b, 0);
      if (total === 0) return { pass: true, message: null };
      const expected = prov.election_2569.spending_limits.sk_tiers.reduce((a, t) => a + t.count, 0);
      return {
        pass: total === expected,
        message: total === expected ? null : `Total=${total}, expected=${expected}. Per-tier: ${JSON.stringify(counts)}`,
        severity: 'error',
      };
    },
  },
  {
    id: 'D3',
    name: 'Tier counts match provenance (5/11/18/8/8)',
    run: (html) => {
      const optRe = /<option[^>]*value="(820000|900000|1000000|1050000|1150000)"/g;
      const counts = {};
      let m;
      while ((m = optRe.exec(html)) !== null) {
        counts[m[1]] = (counts[m[1]] || 0) + 1;
      }
      if (Object.keys(counts).length === 0) return { pass: true, message: null };
      const mismatches = [];
      prov.election_2569.spending_limits.sk_tiers.forEach((t) => {
        const actual = counts[String(t.amount)] || 0;
        if (actual !== t.count) mismatches.push(`${t.display}: expected ${t.count}, got ${actual}`);
      });
      return {
        pass: mismatches.length === 0,
        message: mismatches.length ? `Mismatch:\n    ${mismatches.join('\n    ')}` : null,
        severity: 'error',
      };
    },
  },
];

function validateFile(filename) {
  const full = path.join(BKK_DIR, filename);
  if (!fs.existsSync(full)) {
    console.log(c('yellow', `  SKIP ${filename}`));
    return { pass: 0, fail: 0, warn: 0 };
  }
  const html = fs.readFileSync(full, 'utf8');
  console.log(c('bold', `\nValidating: ${filename}`));
  let pass = 0, fail = 0, warn = 0;
  for (const check of CHECKS) {
    const result = check.run(html);
    if (result.pass) {
      console.log(`  [${check.id}] ${c('green', 'PASS')}  ${check.name}`);
      pass++;
    } else {
      const sev = result.severity === 'error' ? c('red', 'FAIL') : c('yellow', 'WARN');
      console.log(`  [${check.id}] ${sev}  ${check.name}`);
      if (result.message) console.log(c('gray', `         ${result.message.split('\n').join('\n         ')}`));
      if (result.severity === 'error') fail++; else warn++;
    }
  }
  return { pass, fail, warn };
}

const args = process.argv.slice(2);
const fileArg = args.indexOf('--file');
const targets = fileArg !== -1 ? [args[fileArg + 1]] : PAGES;

let totalPass = 0, totalFail = 0, totalWarn = 0;
for (const f of targets) {
  const r = validateFile(f);
  totalPass += r.pass; totalFail += r.fail; totalWarn += r.warn;
}

console.log('');
console.log(c('bold', `${totalPass} passed, ${totalFail} failed, ${totalWarn} warnings`));
if (totalFail > 0) {
  console.log(c('red', c('bold', 'CITATION DRIFT DETECTED')));
  process.exit(1);
} else {
  console.log(c('green', c('bold', totalWarn > 0 ? 'Passed with warnings' : 'All checks passed')));
  process.exit(0);
}
