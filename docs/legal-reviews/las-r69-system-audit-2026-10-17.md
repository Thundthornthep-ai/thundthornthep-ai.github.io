# R69: การแก้ไขตามผลการตรวจระบบ Legal Knowledge Hub (17 ตุลาคม 2569)

## ที่มา

การตรวจระบบแบบอ่านอย่างเดียวเมื่อวันที่ 17 ตุลาคม 2569 ครอบคลุมด่านการเผยแพร่ โครงสร้างเว็บไซต์ บันทึกการเผยแพร่ ข้อมูลที่สร้างจากสคริปต์ ทะเบียนการตรวจทาน ทะเบียนเลขมาตรา มาตรฐานเนื้อหา ระบบอัตโนมัติ งานค้าง ฝั่งแอปพลิเคชัน และทะเบียนใน Notion ผู้ประสานงานตัดสินตามคำสั่งถาวรของเจ้าของเมื่อวันที่ 14 ตุลาคม 2569 ตามบันทึก las-billing `docs/legal-kb/knowledge-hub/audit-2026-11-09/` (approval.json, AUDIT-NOTES.md)

## การตัดสิน

- R69-a: เลขคำพิพากษาศาลฎีกาที่บันทึกระบุว่าไม่พบหรือยืนยันไม่ได้ หรือที่หน้าเว็บเองระบุว่ายังไม่ได้ตรวจ ถูกนำออกจากหน้าภาษาไทยและภาษาอังกฤษพร้อมธงและหมายเหตุของผู้ตรวจ หลักกฎหมายที่เกี่ยวข้องเขียนใหม่จากตัวบทในคลังที่ตรวจแล้ว เพราะฐานข้อมูลคำพิพากษาของศาลฎีกาเข้าถึงไม่ได้จากสภาพแวดล้อมการทำงาน
- R69-b: การอ้างเลขมาตราที่ผิดซึ่งค้างอยู่ในรูป "ม." บนหน้า LAS UP EP03, LAS C&C EP08 และหน้าคู่มืออ่านสัญญา ได้รับการแก้จากตัวบทและเขียนคำว่า "มาตรา" เต็ม
- R69-c: ข้อสงวนสิทธิ์ที่ขาดไป คำนำหน้า "ดร." ตัวอักษรเสีย ลิงก์ภายในที่เสีย ลิงก์ hreflang ไปยังหน้าภาษาอังกฤษที่ไม่มีอยู่ และชื่อผู้เขียนที่ไม่ตรงรูปแบบ

## ด่านการตรวจที่เพิ่มขึ้น

- ด่านการอ้างอิงอ่านรูปแบบ "ม.N", "มาตราN", "Sec. N" และรายการเลขมาตรา และผูกเลขมาตรากับกฎหมายที่ระบุด้วย "แห่ง" หรือ "ตาม" การอ่านไม่ออกถือว่าไม่ผ่าน
- ด่านกฎเนื้อหา ด่านลิงก์ภายใน และด่าน sitemap ทำงานใน CI และครอบคลุมหน้าในบล็อกที่ทบทวนแล้ว
- ทะเบียนเลขคำพิพากษาศาลฎีกาที่ยืนยันแล้ว `scripts/legal-kb/supreme-court-verified.json`

## ทะเบียนเลขมาตรา
- พระราชบัญญัติการเดินอากาศ พ.ศ. 2497 (ฐานข้อมูลกฤษฎีกา เอกสาร 10334 ณ 30 เมษายน 2569 · แก้ไขถึงฉบับที่ 13 พ.ศ. 2562 ในฐานข้อมูล และรวมฉบับที่ 14 พ.ศ. 2562 ด้วยโปรแกรม (ไม่พบฉบับที่ 15 ณ 13 ตุลาคม 2569)) มาตรา 15/22 → `scripts/legal-kb/air-navigation-act.md` — มีในฉบับรวม OCS `OCS doc 10334 · Drive 11rekiAlmI8kb9MHr7RdgyJoxMRfRE-QJ · https://searchlaw.ocs.go.th/council-of-state/#/public/doc/ak4rSG1WUWNobGxDNnFNSTlLZS9KUT09` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พ.ร.บ.โรงแรม พ.ศ. 2547 มาตรา 26 → `scripts/legal-kb/hotel-act.md` — มีในฉบับรวม OCS `laws/hotel-act-2547.pdf` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พ.ร.บ.ลิขสิทธิ์ พ.ศ. 2537 มาตรา 44 → `scripts/legal-kb/copyright-act.md` — มีในฉบับรวม OCS `laws/copyright-act.pdf` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พ.ร.บ.ลิขสิทธิ์ พ.ศ. 2537 มาตรา 45 → `scripts/legal-kb/copyright-act.md` — มีในฉบับรวม OCS `laws/copyright-act.pdf` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พ.ร.บ.ลิขสิทธิ์ พ.ศ. 2537 มาตรา 65 → `scripts/legal-kb/copyright-act.md` — มีในฉบับรวม OCS `laws/copyright-act.pdf` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พระราชบัญญัติการขนส่งต่อเนื่องหลายรูปแบบ พ.ศ. 2548 (ฐานข้อมูลกฤษฎีกา เอกสาร 6489 ณ 30 เมษายน 2569 · ไม่พบฉบับแก้ไขในสำเนา) มาตรา 27 → `scripts/legal-kb/multimodal-transport-act.md` — มีในฉบับรวม OCS `OCS doc 6489 · Drive 1Xfx7L1ANanLZ8J8FGnY8iiNPETJHPXNM · https://searchlaw.ocs.go.th/council-of-state/#/public/doc/M2UyTTM0bzJsTDhOR013cjlGSmJzdz09` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พระราชบัญญัติการขนส่งต่อเนื่องหลายรูปแบบ พ.ศ. 2548 (ฐานข้อมูลกฤษฎีกา เอกสาร 6489 ณ 30 เมษายน 2569 · ไม่พบฉบับแก้ไขในสำเนา) มาตรา 30 → `scripts/legal-kb/multimodal-transport-act.md` — มีในฉบับรวม OCS `OCS doc 6489 · Drive 1Xfx7L1ANanLZ8J8FGnY8iiNPETJHPXNM · https://searchlaw.ocs.go.th/council-of-state/#/public/doc/M2UyTTM0bzJsTDhOR013cjlGSmJzdz09` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พระราชบัญญัติการขนส่งต่อเนื่องหลายรูปแบบ พ.ศ. 2548 (ฐานข้อมูลกฤษฎีกา เอกสาร 6489 ณ 30 เมษายน 2569 · ไม่พบฉบับแก้ไขในสำเนา) มาตรา 38 → `scripts/legal-kb/multimodal-transport-act.md` — มีในฉบับรวม OCS `OCS doc 6489 · Drive 1Xfx7L1ANanLZ8J8FGnY8iiNPETJHPXNM · https://searchlaw.ocs.go.th/council-of-state/#/public/doc/M2UyTTM0bzJsTDhOR013cjlGSmJzdz09` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พระราชบัญญัติการขนส่งต่อเนื่องหลายรูปแบบ พ.ศ. 2548 (ฐานข้อมูลกฤษฎีกา เอกสาร 6489 ณ 30 เมษายน 2569 · ไม่พบฉบับแก้ไขในสำเนา) มาตรา 69 → `scripts/legal-kb/multimodal-transport-act.md` — มีในฉบับรวม OCS `OCS doc 6489 · Drive 1Xfx7L1ANanLZ8J8FGnY8iiNPETJHPXNM · https://searchlaw.ocs.go.th/council-of-state/#/public/doc/M2UyTTM0bzJsTDhOR013cjlGSmJzdz09` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พระราชบัญญัติการขนส่งต่อเนื่องหลายรูปแบบ พ.ศ. 2548 (ฐานข้อมูลกฤษฎีกา เอกสาร 6489 ณ 30 เมษายน 2569 · ไม่พบฉบับแก้ไขในสำเนา) มาตรา 70 → `scripts/legal-kb/multimodal-transport-act.md` — มีในฉบับรวม OCS `OCS doc 6489 · Drive 1Xfx7L1ANanLZ8J8FGnY8iiNPETJHPXNM · https://searchlaw.ocs.go.th/council-of-state/#/public/doc/M2UyTTM0bzJsTDhOR013cjlGSmJzdz09` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พระราชบัญญัติยา พ.ศ. 2510 (ฐานข้อมูลกฤษฎีกา เอกสาร 2675 ณ 30 เมษายน 2569 · พระราชบัญญัติยา (ฉบับที่ 6) พ.ศ. 2562 (doc 2817)) มาตรา 38 → `scripts/legal-kb/drug-act.md` — มีในฉบับรวม OCS `OCS doc 2675 · Drive 1skOP4a2F-hHFyKr01vgDlHMwu5XwOvU3 · https://searchlaw.ocs.go.th/council-of-state/#/public/doc/N0lPSUFmTWE0T3cvUU9Dc0I5blZtZz09` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พระราชบัญญัติประกอบรัฐธรรมนูญว่าด้วยการป้องกันและปราบปรามการทุจริต พ.ศ. 2561 (ฉบับรวมของสำนักงานคณะกรรมการกฤษฎีกาจากเว็บไซต์ ตรวจล่าสุด 29 มิถุนายน 2568 · แก้ไขถึงฉบับที่ 2 พ.ศ. 2568) มาตรา 167 → `scripts/legal-kb/nacc-organic-act.md` — มีในฉบับรวม OCS `data/laws-owner/nacc-organic-act-2561.pdf (เจ้าของบันทึกจากระบบค้นหากฎหมายของสำนักงานคณะกรรมการกฤษฎีกา 3 ตุลาคม 2569)` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา 1064 → `scripts/legal-kb/ccc-sections.md` — มีในฉบับรวม OCS `laws/civil-commercial-code-2568.pdf` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา 1078 → `scripts/legal-kb/ccc-sections.md` — มีในฉบับรวม OCS `laws/civil-commercial-code-2568.pdf` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พระราชบัญญัติอาหาร พ.ศ. 2522 (ฐานข้อมูลกฤษฎีกา เอกสาร 2104 ณ 30 เมษายน 2569 · ไม่พบฉบับแก้ไขในสำเนา) มาตรา 71 → `scripts/legal-kb/food-act.md` — มีในฉบับรวม OCS `OCS doc 2104 · Drive 1eZZCLWnPA2ccQIAy3QwhVppRwsWbQh8K · https://searchlaw.ocs.go.th/council-of-state/#/public/doc/REZKNHZHdndWOEZZNEVHRXkrQzE2UT09` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พ.ร.บ.เขตพัฒนาพิเศษภาคตะวันออก พ.ศ. 2561 มาตรา 54 → `scripts/legal-kb/eec-act.md` — มีในฉบับรวม OCS `laws/eec-act-2561.pdf` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พ.ร.บ.เขตพัฒนาพิเศษภาคตะวันออก พ.ศ. 2561 มาตรา 55 → `scripts/legal-kb/eec-act.md` — มีในฉบับรวม OCS `laws/eec-act-2561.pdf` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา 1051 → `scripts/legal-kb/ccc-sections.md` — มีในฉบับรวม OCS `laws/civil-commercial-code-2568.pdf` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พ.ร.บ.อนุญาโตตุลาการ พ.ศ. 2545 (ฉบับประกาศใช้ พ.ศ. 2545 ยังไม่รวมฉบับแก้ไขเพิ่มเติมภายหลัง) มาตรา 45 → `scripts/legal-kb/arbitration-act.md` — มีในฉบับรวม OCS `laws/arbitration-act-2545.pdf` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พระราชบัญญัติแรงงานสัมพันธ์ พ.ศ. 2518 (ฉบับรวมของสำนักงานคณะกรรมการกฤษฎีกาจากเว็บไซต์ ตรวจล่าสุด 31 สิงหาคม 2567 · แก้ไขถึงฉบับที่ 3 พ.ศ. 2544 และพระราชบัญญัติว่าด้วยการปรับเป็นพินัย พ.ศ. 2565) มาตรา 10 → `scripts/legal-kb/labour-relations-act.md` — มีในฉบับรวม OCS `data/laws-owner/labour-relations-act-2518-v2.pdf (เจ้าของบันทึกจากระบบค้นหากฎหมายของสำนักงานคณะกรรมการกฤษฎีกา 4 ตุลาคม 2569)` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
- พ.ร.บ.เครื่องหมายการค้า พ.ศ. 2534 มาตรา 80 → `scripts/legal-kb/trademark-act.md` — มีในฉบับรวม OCS `laws/trademark-act.pdf` (ตรวจด้วย las-billing scripts/legal/statute-corpus.py)
