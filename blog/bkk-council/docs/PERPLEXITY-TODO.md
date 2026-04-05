# TODO สำหรับน้องเพอ (Perplexity) — Post-Audit Action Items

> สร้างโดย: น้อง (Claude Code CEO) — 5 เมษายน 2569
> อ้างอิง: docs/audit-report.md (Full Audit 7 หมวด)
> สถานะ: รอน้องเพอดำเนินการ → เสร็จแล้ว Claude Code จะรับช่วงดูแลต่อ

---

## สถานะ PDF ใน downloads/ (ณ วันที่ 5 เม.ย. 2569)

### ✅ PDF ที่เพิ่มแล้ว (จาก LAS KB — Claude Code ทำให้แล้ว)

| ไฟล์ | เนื้อหา | ขนาด | ที่มา |
|------|---------|-------|-------|
| `organic-act-nacc-2561.pdf` | พ.ร.ป.ว่าด้วยการป้องกันและปราบปรามการทุจริต พ.ศ. 2561 | 548KB | LAS KB |
| `ethics-code-local-council-2565.pdf` | ประมวลจริยธรรมสมาชิกสภาท้องถิ่น พ.ศ. 2565 | 95KB | LAS KB |
| `royal-decree-sk-salary-2560.pdf` | พ.ร.ฎ.กำหนดเงินประจำตำแหน่ง/เงินเดือน ส.ก. พ.ศ. 2560 | 60KB | LAS KB |

### ❌ PDF ที่ยังขาด — น้องเพอดาวน์โหลดเพิ่ม

| ไฟล์ที่ต้องตั้งชื่อ | เนื้อหาที่ต้องการ | แหล่งดาวน์โหลด |
|---------------------|-------------------|----------------|
| `reg-ect-local-election-2562.pdf` | ระเบียบ กกต. ว่าด้วยการเลือกตั้งสมาชิกสภาท้องถิ่นหรือผู้บริหารท้องถิ่น พ.ศ. 2562 | ect.go.th หรือ ราชกิจจานุเบกษา |
| `royal-decree-sk-salary-2555-v8.pdf` | พ.ร.ฎ.กำหนดเงินประจำตำแหน่ง ฉบับที่ 8 พ.ศ. 2555 | ราชกิจจานุเบกษา (มีอ้างอิงใน ep6.html) |

> **หมายเหตุ:** พ.ร.ฎ.กำหนดให้มีการเลือกตั้ง จะออกใหม่ทุกการเลือกตั้ง — ยังไม่ต้องเตรียม PDF (รอประกาศ กกต.)

---

## Critical Fixes ที่น้องเพอต้องแก้ใน HTML

### Fix 1 — krisdika.go.th link ตาย
**ไฟล์:** `phase-d-e.html` (บรรทัด 1213, 2560), `sk-candidate-guide.html`
**ปัญหา:** `https://krisdika.go.th` DNS ไม่ resolve
**แก้ไข:** เปลี่ยนทุกจุดเป็น:
```
https://www.krisdika.go.th
```
หรือถ้ายัง fail:
```
https://ocs.go.th/searchlaw
```

### Fix 2 — เพิ่ม download links สำหรับ PDF ใหม่ 3 ไฟล์
**ไฟล์:** `phase-d-e.html` หรือ `phase-c.html` (section ที่อ้างถึงกฎหมาย)
**เพิ่ม:**
```html
<!-- ใน section ทรัพย์สิน / ป.ป.ช. -->
<a href="downloads/organic-act-nacc-2561.pdf" class="download-btn" download>
  📥 พ.ร.ป. ป.ป.ช. 2561
</a>

<!-- ใน section จริยธรรม -->
<a href="downloads/ethics-code-local-council-2565.pdf" class="download-btn" download>
  📥 ประมวลจริยธรรมสมาชิกสภาท้องถิ่น 2565
</a>

<!-- ใน section สิทธิประโยชน์ -->
<a href="downloads/royal-decree-sk-salary-2560.pdf" class="download-btn" download>
  📥 พ.ร.ฎ.เงินประจำตำแหน่ง ส.ก. 2560
</a>
```

### Fix 3 — เพิ่ม links สำหรับ Orphan PDFs ที่มีอยู่แล้ว
**ไฟล์:** `phase-d-e.html` section คลังข้อมูล (#law-full-section หรือ section ใหม่)
**Orphan PDFs ที่ควรเพิ่ม link (สำคัญที่สุด):**

```html
<!-- คู่มือ ส.ก. (เล่มหนาที่สุด — มีประโยชน์มากสำหรับ ส.ก. ใหม่) -->
<a href="downloads/bkk-council-member-handbook-vol1.pdf" class="download-btn" download>
  📥 คู่มือสมาชิกสภา กทม. เล่ม 1
</a>
<a href="downloads/bkk-council-member-handbook-vol2.pdf" class="download-btn" download>
  📥 คู่มือสมาชิกสภา กทม. เล่ม 2
</a>

<!-- ข้อบังคับการประชุม (ครบทุกฉบับ) -->
<a href="downloads/bkk-council-meeting-rules-2562.pdf" class="download-btn" download>
  📥 ข้อบังคับการประชุมสภา กทม. 2562
</a>
<a href="downloads/bkk-council-meeting-rules-amendment3-2565.pdf" class="download-btn" download>
  📥 แก้ไขครั้งที่ 3 พ.ศ. 2565
</a>
<a href="downloads/bkk-council-meeting-rules-amendment4-2566.pdf" class="download-btn" download>
  📥 แก้ไขครั้งที่ 4 พ.ศ. 2566
</a>

<!-- จรรยาบรรณ -->
<a href="downloads/bkk-council-ethics-code-2559.pdf" class="download-btn" download>
  📥 จรรยาบรรณสมาชิกสภา กทม. 2559
</a>

<!-- อำนาจหน้าที่ -->
<a href="downloads/bkk-council-powers-and-duties.pdf" class="download-btn" download>
  📥 อำนาจหน้าที่สภา กทม.
</a>

<!-- สรุปรายตอน 1-6 -->
<a href="downloads/summary-01-powers-and-duties.pdf">📥 สรุป 1: อำนาจหน้าที่</a>
<a href="downloads/summary-02-council-meetings.pdf">📥 สรุป 2: การประชุม</a>
<a href="downloads/summary-03-committees.pdf">📥 สรุป 3: คณะกรรมการ</a>
<a href="downloads/summary-04-motions-and-debates.pdf">📥 สรุป 4: ญัตติ/อภิปราย</a>
<a href="downloads/summary-05-motion-endorsement.pdf">📥 สรุป 5: การรับรองญัตติ</a>
<a href="downloads/summary-06-interpellations.pdf">📥 สรุป 6: กระทู้ถาม</a>
```

### Fix 4 — dashboard.html countdown timezone
**ไฟล์:** `dashboard.html` บรรทัด 938
**เปลี่ยนจาก:**
```javascript
new Date(2026, 6, 5, 8, 0, 0, 0)
```
**เปลี่ยนเป็น:**
```javascript
new Date('2026-07-05T08:00:00+07:00')
```

### Fix 5 — sk-candidate-guide.html election countdown time
**ไฟล์:** `sk-candidate-guide.html` บรรทัด 3793
**เปลี่ยนจาก:**
```javascript
new Date('2026-07-05T00:00:00+07:00')
```
**เปลี่ยนเป็น:**
```javascript
new Date('2026-07-05T08:00:00+07:00')
```

---

## Warning Fixes (ไม่เร่ง แต่ควรทำ)

| # | ไฟล์ | ปัญหา | แก้ไข |
|---|------|--------|-------|
| W1 | phase-d-e.html:801,886 | wiki.kpi.ac.th ไม่ใช่ approved source | ลบ credit → อ้าง ม.89 โดยตรง |
| W2 | phase-d-e.html:1367 | ม.11 อ้างผิดบริบท (45 วัน) | แก้เป็น ม.17 พ.ร.บ.กทม. |
| W3 | phase-a.html:611 | ม.102 ขาดเศษ 75,000 | เพิ่ม "(เศษเกิน 75,000 นับอีก 1)" |
| W4 | phase-d-e.html:1024 | ม.102 ใช้ผิดบริบท | ตรวจตัวบทจริง แก้เลขมาตรา |
| W5 | phase-a.html:747 | ม.12 ตำแหน่ง ผอ.กต. คลุมเครือ | ระบุชัดว่าเป็นตำแหน่งเดียวกัน |
| W6 | index.html:~750 | Phase E "7 หัวข้อ" ≠ จริง 9 | แก้ตัวเลข |
| W7 | bangkrachao.pdf | Duplicate ของ reg-2563 | ลบ หรือ แทนไฟล์จริง |

---

## Naming Convention สำหรับ PDF ใหม่

```
[ประเภท]-[ชื่อย่อ]-[ปี พ.ศ.].pdf

ประเภท:
  pra-  = พ.ร.บ. (Act)
  prb-  = พ.ร.บ. (Act — ใช้แล้วใน prb-bma-2528)
  organic-act- = พ.ร.ป. (Organic Act)
  royal-decree- = พ.ร.ฎ. (Royal Decree)
  reg-  = ระเบียบ (Regulation)
  ethics-code- = ประมวลจริยธรรม
  manual- = คู่มือ
  bmc-  = เอกสารสภา กทม.
  ect-  = เอกสาร กกต.
  summary- = สรุป
```

---

## เมื่อน้องเพอทำเสร็จ

1. Commit + Push ทุกการเปลี่ยนแปลง
2. แจ้ง Khun Tae → Claude Code จะ:
   - ตรวจ links ใหม่ทั้งหมด
   - ตรวจ magic bytes PDF ใหม่
   - Re-audit ตาม 7 หมวด
   - อัปเดต audit-report.md
   - ดูแลต่อเนื่อง

---

*สร้างโดย LAS Legal AI — CEO Window | อ้างอิง: docs/audit-report.md*
