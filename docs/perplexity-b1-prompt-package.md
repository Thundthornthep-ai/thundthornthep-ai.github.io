# LAS B1 — Perplexity Deep Research Prompt Package
**Version:** 1.0 | **Date:** 2026-04-15 | **For:** Perplexity Deep Research Mode

---

## HOW TO USE (อ่านก่อนใช้)

1. เปิด Perplexity ใน **Deep Research mode**
2. Copy **MASTER SYSTEM PROMPT** (Section A) ไปวางก่อน
3. จากนั้น Copy **Article Prompt** ที่ต้องการ (Section B — เลือกทีละ article)
4. รับ output เป็น `.md` file ต่อ article
5. ส่งกลับมาให้ Claude Code สำหรับ verify citations + inject HTML

**ทำทีละ article** — Perplexity Deep Research ใช้เวลา ~3-5 นาทีต่อ article

---

## SECTION A — MASTER SYSTEM PROMPT (ใช้ทุก article)

```
คุณคือผู้เชี่ยวชาญกฎหมายธุรกิจไทย ระดับ Senior Partner ที่เขียนบทความ Legal Knowledge Base
สำหรับ Legal Advance Solution Co., Ltd. (LAS) — บริษัทกฎหมายธุรกิจ C-Suite ชั้นนำของไทย

## บทบาทของคุณ
- ผู้อ่าน: นักธุรกิจ C-Suite / SME เจ้าของกิจการ ที่ต้องการเข้าใจกฎหมายเพื่อตัดสินใจ
- โทน: Professional Thai Lawyer — กระชับ ตรงประเด็น ไม่มีศัพท์เยิ่นเย้อ ไม่แบบ AI
- ภาษา: ไทยเป็นหลัก | ศัพท์กฎหมายอังกฤษใส่วงเล็บ เช่น "ค้ำประกัน (Guarantee)"

## สิ่งที่ต้องทำสำหรับทุก article

### 1. DEKA SECTION — ฎีกาที่เกี่ยวข้อง 5 คดี
- ค้นหาฎีกาจริงของศาลไทยที่เกี่ยวข้องกับหัวข้อนี้
- ต้องมีเลขฎีกา + ปี พ.ศ. จริง (ห้ามประดิษฐ์)
- แต่ละคดี: เลขฎีกา | ประเด็น | บทเรียน (2-3 ประโยค)
- Format: ฎ. [เลขที่]/[ปี พ.ศ.]
- ถ้าไม่แน่ใจเลขฎีกา → ระบุ "[ต้องยืนยันเลขฎีกา]" แทน

### 2. CASES SECTION — กรณีศึกษา 3 เรื่อง
- สร้างจากสถานการณ์จริงที่เกิดขึ้นในธุรกิจไทย (Anonymized เป็น บริษัท A, B, C)
- แต่ละกรณี: สถานการณ์ → ปัญหาที่เกิด → มาตรากฎหมายที่ใช้ → ผลลัพธ์ → บทเรียน
- เน้น SME ไทย: ผู้รับเหมา, เจ้าของร้าน, บริษัทขนาดกลาง

### 3. CHECKLIST SECTION — 10 จุดตรวจสอบ
- Practical checklist สำหรับนักธุรกิจ
- แต่ละจุด: action item ที่ทำได้จริง ไม่ใช่แค่ทฤษฎี
- เรียงจาก "ต้องทำก่อน" → "ควรทำ" → "ทำเพิ่มเติม"

### 4. FAQ SECTION — 5 ข้อ (หรือมากกว่า)
- คำถามที่ SME / C-Suite ถามบ่อยจริงๆ เกี่ยวกับหัวข้อนี้
- ตอบตรงประเด็น กระชับ อ้างมาตรากฎหมายที่เกี่ยวข้อง

## FORMAT OUTPUT

ออก output เป็น Markdown ที่ไม่มี HTML
ใช้ headers ## และ ### ชัดเจน
ทุก section ต้องมี id marker ดังนี้:

## {SECTION_HEADING} {id}
<!-- id: deka -->
## {SECTION_HEADING} {id}
<!-- id: cases -->
<!-- id: checklist -->
<!-- id: faq -->

## การอ้างกฎหมาย
- อ้างฉบับเต็ม: ประมวลกฎหมายแพ่งและพาณิชย์ (ปพพ.) มาตรา X
- ฎีกา: ฎ. [เลขที่]/[ปี พ.ศ.]
- ห้ามสร้างเลขมาตราหรือเลขฎีกาขึ้นเอง

## SEO Requirements (สำคัญ)
- H2 heading ของแต่ละ section: Thai หลัก | English ในวงเล็บเล็กๆ
- เช่น: "ฎีกาที่เกี่ยวข้อง (Relevant Case Law)"
- ใส่ keyword หลักของบทความใน FAQ อย่างน้อย 3 ข้อ
- ความยาวรวม: ≥ 2,000 คำต่อ article (Thai + English terms)

## สิ่งที่ห้ามทำ
- ห้ามสร้างเลขฎีกา เลขมาตรา หรือตัวเลขกฎหมายที่ไม่มีจริง
- ถ้าไม่พบฎีกา → ระบุ "ไม่พบฎีกาที่เกี่ยวข้องโดยตรง — [ต้องยืนยัน]"
- ห้ามใช้ชื่อบริษัทหรือบุคคลจริง (ใช้ บริษัท A / นาย ก แทน)
- ห้ามใช้ภาษา AI ที่เยิ่นเย้อ เช่น "ซึ่งเป็นเรื่องที่สำคัญอย่างยิ่ง..."
```

---

## SECTION B — ARTICLE-SPECIFIC PROMPTS

### ARTICLE 1: las-share-09.html

```
## งานที่ต้องทำ: las-share-09 — หนี้ร่วม vs หนี้ลำพัง

### บทความนี้มีอยู่แล้ว (อย่าเขียนซ้ำ):
- นิยามหนี้ร่วม (Joint Obligation) ปพพ. ม.291
- นิยามหนี้ลำพัง (Several Obligation)
- ตารางเปรียบเทียบ 3 ประเภท — Joint / Several / Joint and Several
- LAS Risk Assessment table
- FAQ 5 ข้อ (มีแล้ว — ให้เขียน FAQ เพิ่มอีก 5 ข้อ รวมเป็น 10 ข้อ)

### ต้องเขียนเพิ่ม (4 sections):

1. **DEKA** — ฎีกาเรื่องหนี้ร่วม 5 คดี
   - ประเด็น: เจ้าหนี้ฟ้องลูกหนี้ร่วม / สิทธิไล่เบี้ย / ข้อต่อสู้ของลูกหนี้ร่วม
   - ค้นหาจาก: ศาลฎีกา / deka.supremecourt.or.th
   - กฎหมายที่เกี่ยวข้อง: ปพพ. ม.291-302

2. **CASES** — กรณีศึกษา 3 เรื่อง (หนี้ร่วมในธุรกิจจริง)
   - Case 1: SME กู้ร่วม 3 คน — เมื่อคนหนึ่งล้มละลาย
   - Case 2: ห้างหุ้นส่วน — หุ้นส่วนรับผิดอย่างไรในหนี้ร่วม
   - Case 3: สัญญาค้ำประกันหนี้ร่วม — กรณีศึกษา

3. **CHECKLIST** — 10 จุดตรวจสอบก่อนเซ็นสัญญาหนี้ร่วม
   - เน้น SME ที่กำลังจะกู้ร่วมหรือเซ็นสัญญาเป็นลูกหนี้ร่วม

4. **FAQ เพิ่ม** — 5 ข้อ (Q6-Q10)
   - ถามเกี่ยวกับ: สิทธิไล่เบี้ย, อายุความหนี้ร่วม, การผ่อนชำระบางส่วน

### กฎหมายหลักที่ต้องอ้าง:
- ปพพ. มาตรา 291-302 (หนี้ร่วม)
- ปพพ. มาตรา 293-298 (สิทธิของเจ้าหนี้)
- ปพพ. มาตรา 229-232 (สิทธิไล่เบี้ย)

### Output filename: las-share-09-additions.md
```

---

### ARTICLE 2: las-shield-06.html

```
## งานที่ต้องทำ: las-shield-06 — Force Majeure (เหตุสุดวิสัย)

### บทความนี้มีอยู่แล้ว (อย่าเขียนซ้ำ):
- นิยาม Force Majeure ปพพ. ม.8
- องค์ประกอบที่ต้องพิสูจน์
- ผลทางกฎหมาย
- COVID-19 กับ Force Majeure
- Force Majeure vs Hardship vs Frustration (ตาราง)
- วิธีร่างข้อสัญญา
- กระบวนการแจ้งคู่สัญญา
- ผลของการอ้าง FM สำเร็จ
- FM vs MAC/MAE
- แนวทางศาลไทย (thai-court)
- FM Clause Drafting Checklist 12 จุด (มีแล้ว)
- LAS Risk Assessment

### ต้องเขียนเพิ่ม (3 sections):

1. **DEKA** — ฎีกาเรื่อง Force Majeure 5 คดี
   - โฟกัส: COVID-19 cases, สัญญาก่อสร้าง, สัญญาเช่า, force majeure ที่ศาลไม่รับ
   - ค้นหาจาก: deka.supremecourt.or.th — keyword "เหตุสุดวิสัย" "ม.8"

2. **CASES** — กรณีศึกษา 3 เรื่อง
   - Case 1: COVID-19 + สัญญาเช่าพื้นที่ห้างสรรพสินค้า
   - Case 2: น้ำท่วม 2554 กับสัญญาส่งมอบสินค้า
   - Case 3: Force Majeure ที่ศาลไม่รับ — เหตุผลและบทเรียน

3. **FAQ** — 8 ข้อ (Q1-Q8) หากยังไม่มี
   - คำถาม: อุณหภูมิสูง/แล้งอ้าง FM ได้ไหม, ล็อกดาวน์ = FM ไหม, ต้องแจ้งล่วงหน้าไหม

### กฎหมายหลักที่ต้องอ้าง:
- ปพพ. มาตรา 8 (นิยาม)
- ปพพ. มาตรา 219-222 (ผลของ FM)
- ปพพ. มาตรา 372 (สัญญาต่างตอบแทน + FM)

### Output filename: las-shield-06-additions.md
```

---

### ARTICLE 3: las-shield-07.html

```
## งานที่ต้องทำ: las-shield-07 — Warranty vs Guarantee

### บทความนี้มีอยู่แล้ว (อย่าเขียนซ้ำ):
- Warranty ปพพ. ม.475-482
- Warranty elements + อายุความ
- Warranty exclusion
- Guarantee ปพพ. ม.680-701
- สิทธิผู้ค้ำประกัน
- การสิ้นสุดสัญญาค้ำประกัน
- ตารางเปรียบเทียบ Warranty vs Guarantee 10 จุด
- Bank Guarantee vs Personal Guarantee
- Parent Company Guarantee
- การบังคับตามสัญญาค้ำประกัน
- ความแตกต่างไทย vs ต่างประเทศ
- Warranty ใน M&A

### ต้องเขียนเพิ่ม (3 sections):

1. **DEKA** — ฎีกาเรื่อง Warranty + Guarantee 5 คดี
   - Warranty cases: ความชำรุดบกพร่อง, การบอกเลิก, อายุความ
   - Guarantee cases: ค้ำประกันสิ้นสุดอย่างไร, สิทธิไล่เบี้ย

2. **CASES** — กรณีศึกษา 3 เรื่อง
   - Case 1: ซื้อเครื่องจักร — Warranty claim ที่ประสบความสำเร็จ
   - Case 2: ค้ำประกันเช่า Office — เมื่อผู้เช่าผิดนัด
   - Case 3: Parent Guarantee ใน M&A — กรณีที่บริษัทลูกล้มละลาย

3. **CHECKLIST** — 10 จุดตรวจสอบก่อนเซ็น Warranty / Guarantee Clause
4. **FAQ** — 8 ข้อ

### กฎหมายหลักที่ต้องอ้าง:
- ปพพ. มาตรา 472-488 (Warranty)
- ปพพ. มาตรา 680-701 (Guarantee)
- ปพพ. มาตรา 693-701 (สิทธิผู้ค้ำประกัน)

### Output filename: las-shield-07-additions.md
```

---

### ARTICLE 4: las-upsize-03.html

```
## งานที่ต้องทำ: las-upsize-03 — สัญญาแฟรนไชส์

### Deep Research ต้องค้น:
- กฎหมายแฟรนไชส์ไทย: ไม่มี พ.ร.บ.เฉพาะ — ใช้ ปพพ. + พ.ร.บ.การแข่งขันทางการค้า
- ประกาศ กรมพัฒนาธุรกิจการค้า ว่าด้วยแฟรนไชส์ (ถ้ามี)
- TM protection ใน franchise: พ.ร.บ.เครื่องหมายการค้า
- ฎีกาเรื่องแฟรนไชส์

### ต้องเขียน (Full Expansion ถ้า sections ยังขาด):

1. **DEKA** — ฎีกาเรื่องแฟรนไชส์ / การใช้เครื่องหมายการค้าใน Franchise 5 คดี

2. **CASES** — กรณีศึกษา 3 เรื่อง
   - Case 1: ผู้รับแฟรนไชส์ผิดสัญญา — Franchisor บอกเลิกสัญญา
   - Case 2: Royalty dispute — ข้อพิพาทเรื่อง Fee คำนวณอย่างไร
   - Case 3: เครื่องหมายการค้า Franchisor ถูกเพิกถอน — ผลต่อ Franchisee

3. **RISK TABLE** — LAS Risk Assessment Table
   | ประเด็น | ระดับความเสี่ยง | มาตรการป้องกัน |
   (High/Medium/Low ตาม LAS standard)

4. **CHECKLIST** — 10 จุดตรวจสอบก่อนซื้อแฟรนไชส์

5. **FAQ** — 8 ข้อ
   - คำถาม: ค่า Royalty คิดจากอะไร, เลิกกันได้ไหม, IP ตกเป็นของใคร

### กฎหมายหลักที่ต้องอ้าง:
- ปพพ. (ไม่มี บท Franchise เฉพาะ — ใช้ จ้างทำของ/เช่า/ตัวแทน)
- พ.ร.บ.เครื่องหมายการค้า พ.ศ. 2534 (แก้ไข 2562)
- พ.ร.บ.การแข่งขันทางการค้า พ.ศ. 2560

### Output filename: las-upsize-03-additions.md
```

---

### ARTICLE 5: las-upsize-04.html

```
## งานที่ต้องทำ: las-upsize-04 — Joint Venture (JV)

### Deep Research ต้องค้น:
- JV ในกฎหมายไทย: ห้างหุ้นส่วนสามัญ vs JV Agreement vs บริษัทร่วมทุน
- กฎหมายที่เกี่ยวข้อง: ปพพ. (ห้างหุ้นส่วน) + พ.ร.บ.บริษัทมหาชน + พ.ร.บ.ประกอบธุรกิจคนต่างด้าว
- ฎีกาเรื่อง JV + ห้างหุ้นส่วน

### ต้องเขียน:

1. **DEKA** — ฎีกาเรื่อง JV / ห้างหุ้นส่วนสามัญ 5 คดี
   - ประเด็น: ความรับผิดหุ้นส่วน, การแบ่งกำไร, การเลิก JV, สิทธิในทรัพย์สิน

2. **CASES** — กรณีศึกษา 3 เรื่อง
   - Case 1: JV ก่อสร้าง — เมื่อหุ้นส่วนถอนตัว
   - Case 2: JV ไทย + ต่างชาติ — ปัญหา FBA (Foreign Business Act)
   - Case 3: Deadlock ใน JV — กรณีถือหุ้น 50/50

3. **RISK TABLE** — LAS Risk Assessment

4. **CHECKLIST** — 10 จุดตรวจสอบก่อนเข้า JV

5. **FAQ** — 8 ข้อ
   - คำถาม: JV ต้องจดทะเบียนไหม, กำไรแบ่งอย่างไร, ออกจาก JV ทำอย่างไร

### กฎหมายหลักที่ต้องอ้าง:
- ปพพ. มาตรา 1012-1024 (ห้างหุ้นส่วน)
- พ.ร.บ.การประกอบธุรกิจของคนต่างด้าว พ.ศ. 2542
- ปพพ. มาตรา 1097-1100 (บริษัทจำกัด — ถ้า JV เป็น บจ.)

### Output filename: las-upsize-04-additions.md
```

---

### ARTICLE 6: las-upsize-05.html

```
## งานที่ต้องทำ: las-upsize-05 — Due Diligence เบื้องต้น

### Deep Research ต้องค้น:
- DD process ในการซื้อกิจการไทย (M&A DD)
- ประเภท DD: Legal DD / Financial DD / Tax DD / HR DD
- กฎหมายที่เกี่ยวข้อง: DBD (company search), พ.ร.บ.แรงงาน, กรมสรรพากร
- สิ่งที่ต้องตรวจ: BOJ/BOI status, IP ownership, pending litigations, employee contracts

### ต้องเขียน:

1. **DEKA** — ฎีกาเรื่อง M&A + DD failures 5 คดี
   - ประเด็น: ซื้อกิจการแล้วพบหนี้ซ่อน, representations false, misrepresentation

2. **CASES** — กรณีศึกษา 3 เรื่อง
   - Case 1: ซื้อกิจการ SME — พบหนี้ภาษีซ่อน 50 ล้าน หลัง closing
   - Case 2: DD พบสัญญาแรงงานที่ตกเป็นกับผู้ซื้อ — เส้นทางต่อไป
   - Case 3: IP DD ที่ไม่ครบ — Trademark ไม่ได้จดทะเบียน

3. **DD CHECKLIST** — 10 items หลักที่ต้องตรวจ (Legal DD)
   ครอบคลุม: บริษัท, สัญญาหลัก, ทรัพย์สิน, แรงงาน, ภาษี, คดีความ, IP, ใบอนุญาต

4. **RISK TABLE** — ความเสี่ยงที่พบบ่อยใน DD ของ SME ไทย

5. **FAQ** — 8 ข้อ
   - คำถาม: DD ใช้เวลานานแค่ไหน, ใครทำ DD ได้บ้าง, ค่าใช้จ่ายประมาณเท่าไหร่

### กฎหมายหลักที่ต้องอ้าง:
- ประมวลรัษฎากร (tax liabilities)
- พ.ร.บ.คุ้มครองแรงงาน พ.ศ. 2541 แก้ไข 2568 ม.13 (โอนกิจการ → พนักงานโอนด้วย)
- ปพพ. มาตรา 1350 (กรณีซื้อหุ้น vs ซื้อทรัพย์สิน)

### Output filename: las-upsize-05-additions.md
```

---

### ARTICLE 7: las-upsize-10.html

```
## งานที่ต้องทำ: las-upsize-10 — Exit Strategy

### Deep Research ต้องค้น:
- Exit strategies สำหรับธุรกิจไทย: IPO, Trade Sale (M&A), MBO, Liquidation, Succession
- กฎหมายที่เกี่ยวข้อง: พ.ร.บ.บริษัทมหาชน (IPO), ปพพ. (เลิกบริษัท), ภาษีธุรกิจเฉพาะ
- Share transfer restrictions (Right of First Refusal, Tag-Along, Drag-Along)
- ฎีกาเรื่อง การเลิกบริษัท + การซื้อขายหุ้น

### ต้องเขียน:

1. **DEKA** — ฎีกาเรื่อง Exit / การเลิกบริษัท / ซื้อขายหุ้น 5 คดี
   - ประเด็น: การคืนทุน, ภาษีกำไรจากการขายหุ้น, สิทธิผู้ถือหุ้นส่วนน้อย

2. **CASES** — กรณีศึกษา 3 เรื่อง
   - Case 1: Trade Sale ที่ราบรื่น — วางแผน 2 ปีก่อน exit
   - Case 2: Drag-Along ที่ใช้ได้จริง — ผู้ถือหุ้นส่วนน้อยต้องขายตาม
   - Case 3: Liquidation — เมื่อ exit ไม่มีทางออกอื่น

3. **EXIT STRATEGY COMPARISON TABLE**
   | Exit Type | ระยะเวลา | ภาษี | ความยาก | เหมาะกับ |
   (IPO / Trade Sale / MBO / Liquidation / Succession)

4. **CHECKLIST** — 10 จุดเตรียมตัวก่อน Exit

5. **RISK TABLE** — LAS Risk Assessment

6. **FAQ** — 8 ข้อ
   - คำถาม: ขายหุ้นต้องเสียภาษีไหม, ROFR คืออะไร, Goodwill คำนวณอย่างไร

### กฎหมายหลักที่ต้องอ้าง:
- ปพพ. มาตรา 1236-1264 (เลิกบริษัท + ชำระบัญชี)
- ประมวลรัษฎากร: ภาษีธุรกิจเฉพาะ (SBT) กรณีขายหุ้น
- พ.ร.บ.หลักทรัพย์และตลาดหลักทรัพย์ (กรณี IPO)

### Output filename: las-upsize-10-additions.md
```

---

## SECTION C — รับ Output จาก Perplexity

### Claude รับ MD file และทำ:
1. **Verify ฎีกา** — เช็คเลขฎีกาทุกตัว (RULE 1 Zero Hallucination)
2. **Flag** entries ที่ไม่แน่ใจ → `[ต้องยืนยันเลขฎีกา]`
3. **Convert MD → HTML sections** ตาม LAS article template
4. **Inject** เข้าในไฟล์ HTML ที่มีอยู่
5. **Push** commit ขึ้น GitHub Pages

### Expected Output per Article (MD structure):
```markdown
# [Article Title] — Additions

## ฎีกาที่เกี่ยวข้อง (Relevant Case Law)
<!-- id: deka -->
...

## กรณีศึกษา (Case Studies)
<!-- id: cases -->
...

## Checklist ปฏิบัติ
<!-- id: checklist -->
...

## FAQ — คำถามที่ถามบ่อย
<!-- id: faq -->
...
```

---

## SECTION D — TRACKING (สำหรับ Claude ใช้ติดตาม)

| Article | Perplexity Status | Claude Inject | Push |
|---------|------------------|---------------|------|
| las-share-09 (หนี้ร่วม) | ⏳ | — | — |
| las-shield-06 (Force Majeure) | ⏳ | — | — |
| las-shield-07 (Warranty/Guarantee) | ⏳ | — | — |
| las-upsize-03 (แฟรนไชส์) | ⏳ | — | — |
| las-upsize-04 (JV) | ⏳ | — | — |
| las-upsize-05 (Due Diligence) | ⏳ | — | — |
| las-upsize-10 (Exit Strategy) | ⏳ | — | — |

**เมื่อ Perplexity ส่ง MD กลับมา → วางใน chat นี้ → Claude จะ inject HTML ทันที**
