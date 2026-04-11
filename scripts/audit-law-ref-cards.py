#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit-law-ref-cards.py — Site-wide audit of law-ref-card link/label consistency

Finds law-reference cards across all articles and flags mismatches where
the card's visible name references one law but the href points to a
different law's PDF.

Usage:
  python3 scripts/audit-law-ref-cards.py [--fix]
"""
import re
import os
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRS = ["articles", "blog/bkk-council", "en/articles"]

# Extract each <a|<span class="law-ref-card...">...</a|</span>
# <a> cards have an href and are clickable; <span> cards are informational only
CARD_A_RE = re.compile(
    r'<a\s+[^>]*?href="([^"]+)"[^>]*class="law-ref-card[^"]*"[^>]*>(.*?)</a>',
    re.DOTALL
)
CARD_A_ALT_RE = re.compile(
    r'<a\s+[^>]*?class="law-ref-card[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
    re.DOTALL
)
CARD_SPAN_RE = re.compile(
    r'<span\s+[^>]*?class="law-ref-card[^"]*"[^>]*>(.*?)</span>',
    re.DOTALL
)
NAME_RE = re.compile(r'class="law-name"[^>]*>([^<]+)<')
SOURCE_RE = re.compile(r'class="law-source"[^>]*>([^<]+)<')


def classify_href(href):
    h = href.lower()
    if 'labour-protection' in h: return 'LPA'
    if 'civil-commercial' in h: return 'CCC'
    if 'pdpa' in h: return 'PDPA'
    if 'condominium' in h: return 'CONDO'
    if 'consumer-protection' in h: return 'CONSUMER'
    if 'arbitration' in h: return 'ARBITRATION'
    if 'foreign-business' in h: return 'FBA'
    if 'revenue-code' in h: return 'REVENUE'
    if 'copyright' in h: return 'COPYRIGHT'
    if 'trademark' in h: return 'TRADEMARK'
    if 'patent' in h: return 'PATENT'
    if 'hotel' in h: return 'HOTEL'
    if 'computer-crime' in h: return 'COMPUTER'
    if 'securities' in h: return 'SECURITIES'
    if 'trade-competition' in h: return 'COMPETITION'
    if 'trade-secrets' in h: return 'TRADE_SECRET'
    if 'unfair-contract' in h: return 'UNFAIR'
    if 'investment-promotion' in h or 'boi' in h: return 'BOI'
    if 'ocs.go.th' in h or 'gdcatalog' in h: return 'EXTERNAL_LEGAL'
    if h.startswith('http') or h.startswith('//'): return 'EXTERNAL'
    if h.startswith('#') or '.html' in h: return 'INTERNAL_PAGE'
    return 'UNKNOWN'


# Section → law canonical mapping (domain knowledge from Thai law sources)
LPA_SECTIONS = {
    '4/1','5','9','10','11','11/1','13','14/1','15','16','17','17/1','18','23','23/1',
    '30','32','34','38','39','39/1','41','41/1','43','50','51','53','57/1','59','59/1','59/2',
    '65','67','70','75','79','82','84','87','108','118','118/1','119','120','123','144',
}
CCC_SECTIONS = {
    '150','171','193','291','295','420','575','587','680','681','683','684','685','686',
    '690','694','695','696','697','698','699','700','701','797','798','799','800','801',
    '810','811','812','813','814','1098','1129','1194','1457',
}
REV_SECTIONS = {'40','65','66','70','77','78','80','82'}


def classify_name(text):
    if not text:
        return 'UNKNOWN'
    t = text
    # Authoritative source signatures (highest priority)
    if 'pdpc.or.th' in t or 'PDPC' in t: return 'PDPA'
    if 'labour.go.th' in t or 'กรมสวัสดิการ' in t: return 'LPA'
    if 'sso.go.th' in t: return 'SSO'
    if 'rd.go.th' in t: return 'REVENUE'
    if 'sec.or.th' in t: return 'SECURITIES'
    if 'ocpb.go.th' in t: return 'CONSUMER'

    # Direct law-name mentions
    if 'คุ้มครองแรงงาน' in t or ' LPA' in t or 'Labour Protection' in t: return 'LPA'
    if 'ประมวลกฎหมายแพ่ง' in t or 'Civil and Commercial' in t or 'ป.พ.พ.' in t or 'ปพพ.' in t: return 'CCC'
    if 'PDPA' in t or 'คุ้มครองข้อมูลส่วนบุคคล' in t or 'DPO' in t or 'DPA' in t: return 'PDPA'
    if 'อาคารชุด' in t or 'Condominium' in t: return 'CONDO'
    if 'คุ้มครองผู้บริโภค' in t or 'Consumer Protection' in t: return 'CONSUMER'
    if 'อนุญาโตตุลาการ' in t or 'Arbitration' in t: return 'ARBITRATION'
    if 'ต่างด้าว' in t or 'Foreign Business' in t: return 'FBA'
    if 'ประมวลรัษฎากร' in t or 'Revenue Code' in t: return 'REVENUE'
    if 'ลิขสิทธิ์' in t or 'Copyright' in t: return 'COPYRIGHT'
    if 'เครื่องหมายการค้า' in t or 'Trademark' in t: return 'TRADEMARK'
    if 'สิทธิบัตร' in t or 'Patent' in t: return 'PATENT'
    if 'โรงแรม' in t or 'Hotel Act' in t: return 'HOTEL'
    if 'คอมพิวเตอร์' in t or 'Computer Crime' in t: return 'COMPUTER'
    if 'หลักทรัพย์' in t or 'Securities' in t: return 'SECURITIES'
    if 'แข่งขันทางการค้า' in t or 'Trade Competition' in t: return 'COMPETITION'
    if 'ความลับทางการค้า' in t or 'Trade Secret' in t: return 'TRADE_SECRET'
    if 'ข้อสัญญาไม่เป็นธรรม' in t or 'Unfair Contract' in t: return 'UNFAIR'
    if 'BOI' in t or 'ส่งเสริมการลงทุน' in t: return 'BOI'

    # Section number heuristics (only if no other signals found)
    m = re.search(r'มาตรา\s*([0-9]+(?:/[0-9]+)?)', t)
    if m:
        sec = m.group(1)
        if sec in LPA_SECTIONS: return 'LPA'
        if sec in CCC_SECTIONS: return 'CCC'
        if sec in REV_SECTIONS: return 'REVENUE'

    return 'UNKNOWN'


def main():
    all_cards = []
    for d in DIRS:
        full = os.path.join(REPO, d)
        if not os.path.isdir(full):
            continue
        for f in sorted(os.listdir(full)):
            if not f.endswith('.html'):
                continue
            rel = os.path.join(d, f).replace(os.sep, '/')
            with open(os.path.join(REPO, rel), 'r', encoding='utf-8') as fp:
                s = fp.read()
            # Collect <a>-based cards (both href-first and class-first ordering)
            seen_spans = set()
            for pat in (CARD_A_RE, CARD_A_ALT_RE):
                for m in pat.finditer(s):
                    href = m.group(1)
                    inner = m.group(2)
                    seen_spans.add((m.start(), m.end()))
                    name_m = NAME_RE.search(inner)
                    source_m = SOURCE_RE.search(inner)
                    name = (name_m.group(1).strip() if name_m else '')
                    source = (source_m.group(1).strip() if source_m else '')
                    all_cards.append({
                        'file': rel, 'kind': 'a',
                        'href': href, 'name': name, 'source': source,
                        'href_law': classify_href(href),
                        'name_law': classify_name(name),
                        'source_law': classify_name(source),
                    })
            # Collect <span>-based cards (informational, no href)
            for m in CARD_SPAN_RE.finditer(s):
                inner = m.group(1)
                name_m = NAME_RE.search(inner)
                source_m = SOURCE_RE.search(inner)
                name = (name_m.group(1).strip() if name_m else '')
                source = (source_m.group(1).strip() if source_m else '')
                all_cards.append({
                    'file': rel, 'kind': 'span',
                    'href': '(no href)', 'name': name, 'source': source,
                    'href_law': 'N/A',
                    'name_law': classify_name(name),
                    'source_law': classify_name(source),
                })

    print(f"Total law-ref-cards found: {len(all_cards)}\n")

    mismatches = []
    for c in all_cards:
        hl = c['href_law']
        nl = c['name_law']
        sl = c['source_law']

        if c['kind'] == 'a':
            # For <a> cards: check name and source against href
            if hl in ('EXTERNAL', 'EXTERNAL_LEGAL', 'INTERNAL_PAGE', 'UNKNOWN'):
                continue
            # If source agrees with href, the card is internally consistent —
            # any name-based heuristic (section number in wrong bucket) is a
            # false positive because the authoritative source signature wins.
            if sl == hl:
                continue
            name_conflict = nl != 'UNKNOWN' and nl != hl
            source_conflict = sl != 'UNKNOWN' and sl != hl
            if name_conflict or source_conflict:
                mismatches.append((c, name_conflict, source_conflict))
        else:
            # For <span> cards: check name against source (internal consistency)
            if nl == 'UNKNOWN' or sl == 'UNKNOWN':
                continue
            if nl != sl:
                # The card's title claims one law, the description claims another
                mismatches.append((c, True, True))

    print(f"=== MISMATCHES ({len(mismatches)}) ===")
    for c, nc, sc in mismatches:
        print()
        print(f"  {c['file']}")
        print(f"    href   = {c['href']} [{c['href_law']}]")
        flag_n = ' <-- CONFLICT' if nc else ''
        flag_s = ' <-- CONFLICT' if sc else ''
        print(f"    name   = {c['name'][:80]!r} [{c['name_law']}]{flag_n}")
        print(f"    source = {c['source'][:80]!r} [{c['source_law']}]{flag_s}")

    by_file = defaultdict(int)
    for c, _, _ in mismatches:
        by_file[c['file']] += 1
    print(f"\n=== Files with mismatches: {len(by_file)} ===")
    for f, n in sorted(by_file.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {n}  {f}")

    return 1 if mismatches else 0


if __name__ == '__main__':
    sys.exit(main())
