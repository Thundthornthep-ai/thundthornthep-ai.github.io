# Design Spec: Law-Ref-Card Direct PDF Links

**Date:** 2026-04-08
**Author:** CEO (Nong AI)
**Status:** Approved by Khun Tae
**Scope:** 16 articles, 74 law-ref-card entries, 22+ PDFs

---

## Problem

Law-ref-cards across 16 articles point to generic `ocs.go.th/searchlaw-law` search page. Users must then search for the specific law. We have 22 PDF files hosted locally at `/laws/` that are unused. When URLs change (like the krisdika incident), 74+ entries need manual updates.

## Solution: Hybrid Static + JS Enhancement

### Architecture

```
HTML (static href — SEO safe)
  + legal-links.js LAW_CARD_MAP (runtime enhancement)
  = Best of both worlds
```

### Link Resolution Priority

1. **PDF local** (`/laws/*.pdf`) — if we host the PDF
2. **Internal article** — for concept cards (SEO internal linking)
3. **OCS search** (`ocs.go.th/searchlaw-law?q=...`) — fallback for laws without PDF

### Implementation

#### 1. Add `LAW_CARD_MAP` to `legal-links.js`

```javascript
var LAW_CARD_MAP = {
  'ปพพ.': { pdf: '/laws/civil-commercial-code-2568.pdf', name: 'ประมวลกฎหมายแพ่งและพาณิชย์' },
  'FBA': { pdf: '/laws/foreign-business-act-2542.pdf', name: 'พ.ร.บ.ประกอบธุรกิจของคนต่างด้าว พ.ศ. 2542' },
  // ...22+ entries
};
```

#### 2. Add `resolveLawRefCards()` function

- Scans all `.law-ref-card[data-law]` elements
- Resolves `href` from `LAW_CARD_MAP`
- Updates `.law-source` text to "ดาวน์โหลด PDF {ชื่อเต็ม}"
- Fallback: `https://www.ocs.go.th/searchlaw-law?q={encodeURIComponent(name)}`

#### 3. HTML changes per article

Before:
```html
<a class="law-ref-card cat-code" href="https://www.ocs.go.th/searchlaw-law" target="_blank">
```

After:
```html
<a class="law-ref-card cat-code" href="/laws/civil-commercial-code-2568.pdf" data-law="ปพพ." target="_blank">
```

- Static `href` = correct link (SEO crawlers see it)
- `data-law` = key for JS to verify/enhance at runtime

#### 4. Concept cards → internal articles

```html
<a class="law-ref-card cat-concept" href="/articles/mergers-acquisitions-thailand.html" data-law="concept:ma">
```

### PDF Mapping Table (Complete)

| Key | PDF File | Full Name |
|-----|----------|-----------|
| ปพพ. | civil-commercial-code-2568.pdf | ประมวลกฎหมายแพ่งและพาณิชย์ |
| FBA | foreign-business-act-2542.pdf | พ.ร.บ.ประกอบธุรกิจของคนต่างด้าว พ.ศ. 2542 |
| PDPA | pdpa-2562.pdf | พ.ร.บ.คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562 |
| LPA | labour-protection-act-2541-amendment9.pdf | พ.ร.บ.คุ้มครองแรงงาน (แก้ไขครั้งที่ 9) พ.ศ. 2568 |
| คอนโด | condominium-act-2522.pdf | พ.ร.บ.อาคารชุด พ.ศ. 2522 |
| โรงแรม | hotel-act-2547.pdf | พ.ร.บ.โรงแรม พ.ศ. 2547 |
| แข่งขัน | trade-competition-act-2560.pdf | พ.ร.บ.การแข่งขันทางการค้า พ.ศ. 2560 |
| คุ้มครองผู้บริโภค | consumer-protection-act.pdf | พ.ร.บ.คุ้มครองผู้บริโภค พ.ศ. 2522 |
| เครื่องหมายการค้า | trademark-act.pdf | พ.ร.บ.เครื่องหมายการค้า พ.ศ. 2534 |
| ความลับทางการค้า | trade-secrets-act-2545.pdf | พ.ร.บ.ความลับทางการค้า พ.ศ. 2545 |
| ลิขสิทธิ์ | copyright-act.pdf | พ.ร.บ.ลิขสิทธิ์ พ.ศ. 2537 |
| สิทธิบัตร | patent-act.pdf | พ.ร.บ.สิทธิบัตร พ.ศ. 2522 |
| หลักทรัพย์ | securities-act-2535.pdf | พ.ร.บ.หลักทรัพย์และตลาดหลักทรัพย์ พ.ศ. 2535 |
| ข้อสัญญาไม่เป็นธรรม | unfair-contract-terms-act-2540.pdf | พ.ร.บ.ว่าด้วยข้อสัญญาที่ไม่เป็นธรรม พ.ศ. 2540 |
| อนุญาโตตุลาการ | arbitration-act-2545.pdf | พ.ร.บ.อนุญาโตตุลาการ พ.ศ. 2545 |
| คอมพิวเตอร์ | computer-crime-act-2550.pdf | พ.ร.บ.ว่าด้วยการกระทำความผิดเกี่ยวกับคอมพิวเตอร์ พ.ศ. 2550 |
| รัษฎากร | revenue-code.pdf | ประมวลรัษฎากร |
| BOI | investment-promotion-act-boi.pdf | พ.ร.บ.ส่งเสริมการลงทุน พ.ศ. 2520 |

### OCS Fallback (laws without PDF — Khun Tae will add later)

| Key | OCS Search Query |
|-----|-----------------|
| เครื่องสำอาง | พระราชบัญญัติเครื่องสำอาง |
| อาหาร | พระราชบัญญัติอาหาร |
| โรงงาน | พระราชบัญญัติโรงงาน |
| ที่ดิน | ประมวลกฎหมายที่ดิน |
| EEC | พระราชบัญญัติเขตพัฒนาพิเศษภาคตะวันออก |

### Success Criteria

1. All 74 law-ref-cards have correct, working links
2. PDFs open directly when clicked (22 laws)
3. OCS search works for laws without PDF
4. Concept cards link to relevant LAS articles
5. `law-source` text says "ดาวน์โหลด PDF {ชื่อเต็ม}" for PDF links
6. Future URL changes require editing only `legal-links.js` LAW_CARD_MAP
7. Static href in HTML = SEO safe (works without JS)

---

*Approved by Khun Tae — 8 April 2026*
