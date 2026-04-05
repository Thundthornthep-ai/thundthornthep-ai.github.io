# 🔍 AUDIT INSTRUCTIONS สำหรับ Claude Code

> สร้างโดย: น้องเพอ (Perplexity Computer) — 5 เมษายน 2569
> วัตถุประสงค์: ตรวจสอบความถูกต้องทุกมิติของเว็บคู่มือเลือกตั้ง ส.ก. กทม. 2569

## คำสั่งสำหรับ Claude Code

กรุณาทำ Full Audit ทั้ง 7 หมวด แล้วสร้าง report เป็นไฟล์ `docs/audit-report.md`

---

## หมวด 1: ตรวจข้อกฎหมาย (Legal Accuracy)

### 1.1 ตรวจมาตราทุกจุด
- เปิดไฟล์ HTML ทั้ง 5: `index.html`, `phase-a.html`, `phase-b.html`, `phase-c.html`, `phase-d-e.html`
- grep หาทุก `มาตรา XX` หรือ `ม.XX`
- ตรวจว่าแต่ละมาตราอ้างอิง **พ.ร.บ. ถูกฉบับ**:
  - ม.10-42, 89, 97-102 → พ.ร.บ.ระเบียบบริหารราชการ กทม. 2528 (แก้ไขถึง ฉบับที่ 6 พ.ศ. 2562)
  - ม.11-12, 23, 28, 49-55, 60-68, 75-88, 106-109, 126-128 → พ.ร.บ.เลือกตั้งสมาชิกสภาท้องถิ่น 2562
  - ม.102 ทรัพย์สิน → พ.ร.ป.ว่าด้วย ป.ป.ช. 2561
- ตรวจว่าฉบับแก้ไข (ฉบับที่ 6) ถูกระบุถูกต้อง:
  - ม.10: เขตละ 1 คน + เกิน 150,000 = เพิ่ม 1 คน (ฉบับที่ 6)
  - ม.11: ยกเลิก (ฉบับที่ 6) → ใช้ พ.ร.บ.เลือกตั้งท้องถิ่น
  - ม.12: คุณสมบัติตามกฎหมายเลือกตั้ง (ฉบับที่ 6)
  - ม.21: สมาชิกภาพเริ่มวันเลือกตั้ง (ฉบับที่ 6)
  - ม.23 (4)(5): แก้ไข (ฉบับที่ 6), ยกเลิก (6)
  - ม.37: 2 ใน 5 (ไม่ใช่ 1/3) — ต้องเช็คว่าถูกหรือผิด (ฉบับที่ 6 เพิ่มจาก ม.37 เป็น 2/5 จริงหรือไม่?)
  - ม.89 (7): "การจัดการจราจรและการวิศวกรรมจราจร" (ฉบับที่ 6)

### 1.2 แหล่งอ้างอิง
- ตรวจว่าทุกแหล่งอ้างอิงเป็น:
  - ✅ ตัวบทกฎหมาย (ราชกิจจานุเบกษา)
  - ✅ คู่มือ กกต.
  - ✅ เว็บ กกต. (ect.go.th)
  - ✅ เว็บสภา กทม. (bmc.go.th)
  - ✅ กฤษฎีกา (krisdika.go.th)
  - ❌ ไม่ใช้: บทความวิชาการ, สื่อ, Wikipedia, Blog (ละเมิดลิขสิทธิ์)

---

## หมวด 2: ตรวจ PDF ทุกไฟล์

ไฟล์อยู่ที่ `downloads/`

### 2.1 ตรวจว่าเป็น PDF จริง
```bash
for f in downloads/*.pdf; do
  magic=$(head -c 5 "$f" | cat -v)
  echo "$f → $magic"
done
```

### 2.2 ตรวจเนื้อหา PDF ตรงกับชื่อ
```bash
for f in downloads/*.pdf; do
  text=$(pdftotext "$f" - 2>/dev/null | head -50 | tr '\n' ' ' | head -c 200)
  echo "=== $f ==="
  echo "$text"
done
```

### 2.3 ตรวจว่า PDF ทุกตัวมีกฎหมายอ้างอิงถูกต้อง
| ไฟล์ | ควรเป็น |
|------|---------|
| pra-local-election-2562.pdf | พ.ร.บ.เลือกตั้งสมาชิกสภาท้องถิ่น 2562 |
| prb-bma-2528.pdf | พ.ร.บ.ระเบียบบริหารราชการ กทม. 2528 |
| manual-registration.pdf | คู่มือรับสมัครเลือกตั้ง (กกต.) |
| local-election-guide.pdf | คู่มือเลือกตั้งท้องถิ่น สำหรับผู้บริหาร/สมาชิก (กกต.) |
| citizen-guide.pdf | คู่มือประชาชน (กกต.) — หมายเหตุ: เป็น อบต. ไม่ใช่ กทม. โดยเฉพาะ |
| election-offenses.pdf | ฐานความผิดตามกฎหมายเลือกตั้ง |
| election-law-basics.pdf | ความรู้เบื้องต้น พ.ร.บ.เลือกตั้งท้องถิ่น 2562 |
| reg-campaign-method-2563.pdf | ระเบียบ กกต. วิธีการหาเสียง 2563 (ราชกิจจาฯ) |
| reg-campaign-method-2563-v2.pdf | ฉบับที่ 2 (ราชกิจจาฯ) |
| reg-campaign-method-2563-combined.pdf | ฉบับรวม (ต้อง verify ด้วยตา — scan) |
| reg-campaign-method-2563-bangkrachao.pdf | อาจซ้ำกับ reg-campaign-method-2563.pdf |
| ect-news-campaign-rules-2568.pdf | ข่าว กกต. (scan — ต้อง verify ด้วยตา) |
| bmc-council-rules.pdf | ข้อบังคับสภา กทม. (ฉบับเก่า 2541) |
| bmc-rules-2563-v2.pdf | ข้อบังคับสภา กทม. ฉบับที่ 2 พ.ศ. 2563 |

---

## หมวด 3: ตรวจ Links ทั้งหมด

### 3.1 Internal links (# anchors)
```bash
# ตรวจว่า internal links ชี้ไป section ที่มีอยู่จริง
for f in index.html phase-*.html; do
  echo "=== $f ==="
  grep -oP 'href="#([^"]+)"' "$f" | while read link; do
    id=$(echo "$link" | grep -oP '(?<=#)[^"]+')
    found=$(grep -c "id=\"$id\"" "$f")
    if [ "$found" -eq 0 ]; then
      echo "  ❌ BROKEN: #$id"
    fi
  done
done
```

### 3.2 Cross-page links
```bash
# ตรวจว่า link ไปหน้าอื่นมีไฟล์จริง
for f in *.html; do
  grep -oP 'href="(phase-[^"#]+|index\.html)' "$f" | while read link; do
    target=$(echo "$link" | grep -oP '(?<=href=")[^"]+')
    if [ ! -f "$target" ]; then
      echo "  ❌ BROKEN: $target (from $f)"
    fi
  done
done
```

### 3.3 Download links
```bash
# ตรวจว่า download links ชี้ไปไฟล์ที่มีจริง
for f in *.html; do
  grep -oP 'href="downloads/[^"]+' "$f" | while read link; do
    target=$(echo "$link" | grep -oP '(?<=href=")[^"]+')
    if [ ! -f "$target" ]; then
      echo "  ❌ MISSING: $target (from $f)"
    fi
  done
done
```

### 3.4 External links
```bash
# ตรวจ external links ว่ายังใช้ได้
grep -ohP 'href="https?://[^"]+' *.html | sort -u | while read link; do
  url=$(echo "$link" | grep -oP '(?<=href=")[^"]+')
  code=$(curl -sL -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null)
  if [ "$code" != "200" ] && [ "$code" != "301" ] && [ "$code" != "302" ]; then
    echo "  ⚠️ $code: $url"
  fi
done
```

---

## หมวด 4: ตรวจ Design & Responsive

### 4.1 Desktop (1440px)
- ทุกหน้า sidebar แสดงถูกต้อง
- เนื้อหาไม่ล้น max-width 780px
- Phase cards เรียงสวย

### 4.2 Mobile (375px)
- Hamburger menu ทำงาน
- เนื้อหาไม่ตัด/ล้น
- ตาราง responsive (horizontal scroll)

### 4.3 Typography
- ภาษาไทย Sarabun แสดงถูกต้อง
- ภาษาอังกฤษ Space Grotesk
- ขนาดหัวข้อ consistent

---

## หมวด 5: ตรวจเนื้อหาซ้ำ / ขาด

### 5.1 ตรวจว่าทั้ง 24 หัวข้อมีครบ
| # | หัวข้อ | อยู่ในหน้า |
|---|--------|-----------|
| 2.1 | คุณสมบัติ | phase-a.html |
| 2.2 | ก่อนประกาศ | phase-a.html |
| 2.3 | ประกาศเลือกตั้ง | phase-a.html |
| 2.4 | สมัคร | phase-a.html |
| 2.5 | จับเบอร์ | phase-a.html |
| 2.6 | หาเสียง | phase-b.html |
| 2.7 | ยุติหาเสียง | phase-b.html |
| 2.8 | วันเลือกตั้ง | phase-b.html |
| 2.9 | หลังเลือกตั้ง | phase-c.html |
| 2.10 | รายงานตัว | phase-c.html |
| 2.11 | ปฏิบัติหน้าที่ | phase-c.html |
| 2.12 | ทรัพย์สิน | phase-c.html |
| 2.13-2.19 | สภา | phase-d-e.html |
| 2.20-2.24 | คลังข้อมูล | phase-d-e.html |

### 5.2 ตรวจว่าเนื้อหาตรงกันระหว่าง sk-candidate-guide.html (backup) กับ phase pages

---

## หมวด 6: ตรวจ JavaScript

- Countdown timer ทำงานถูกต้อง (target: 2026-05-01 + 2026-07-05)
- Checklist interactive ทำงาน (save to localStorage?)
- Search box ทำงาน
- Sidebar active highlighting
- Hamburger menu toggle

---

## หมวด 7: ตรวจวันที่ทั้งหมด

- สมมติฐาน: วันเลือกตั้ง 5 กรกฎาคม 2569
- Countdown target: `2026-07-05T00:00:00+07:00`
- เปิดตัวทีม: `2026-05-01T00:00:00+07:00`
- ตรวจว่าไม่มีวันที่ผิด/เก่า

---

## Output

สร้างไฟล์ `docs/audit-report.md` ที่มี:
1. สรุป PASS / FAIL สำหรับแต่ละหมวด
2. รายการปัญหาที่พบ พร้อมระดับความรุนแรง (Critical / Warning / Info)
3. คำแนะนำการแก้ไข
4. ให้คะแนนโดยรวม (x/100)

---

## วิธีรัน

```bash
cd /path/to/thundthornthep-ai.github.io/blog/bkk-council
# รันคำสั่งในแต่ละหมวดตามลำดับ
# บันทึกผลลัพธ์ใน docs/audit-report.md
```
