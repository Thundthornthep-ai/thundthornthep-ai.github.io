# ส.ก. Navigator — Bug Review Handoff

**Date:** 2026-05-01
**Branch:** `claude/review-sknavigator-bugs-MNMBb`
**Status:** ⚠️ Branch corrupted — needs cleanup before merge

---

## 1. Branch state ตอนนี้

| ไฟล์ | สถานะ remote | ขนาด | ต้องทำ |
|------|--------------|------|--------|
| `manifest.json` | ✅ ดี | 2,346 B | merge ได้ |
| `service-worker.js` | ✅ ดี | 3,064 B | merge ได้ |
| `index.html` | ❌ truncated | 3.9 KB (ของจริง 110 KB) | reset → re-apply |
| `campaign-tracker.html` | ❌ truncated | 2.3 KB (ของจริง 111 KB) | reset → re-apply |
| `district-intel.html` | ❌ truncated | 1.8 KB (ของจริง 119 KB) | reset → re-apply |
| `phase-a.html` | ❌ truncated | 1.4 KB (ของจริง 101 KB) | reset → re-apply |
| `phase-b.html` | ❌ truncated | 1.9 KB (ของจริง 81 KB) | reset → re-apply |
| `phase-c.html` | ⚠️ ยังไม่มี fix | 48.6 KB (main) | apply M7 |
| `phase-d-e.html` | ⚠️ ยังไม่มี fix | 125 KB (main) | apply M7 |

**สาเหตุ truncation**: MCP `create_or_update_file` truncate content > ~10 KB เมื่อยิงจาก sub-agent (Haiku/Sonnet) — เป็น tool parameter size limit ที่ผ่าน proxy

---

## 2. คำสั่งแนะนำที่บ้าน (Claude Code)

### ขั้นที่ 1: ลบ branch เก่าที่ corrupt + เริ่มใหม่

```bash
cd <repo>
git fetch origin
git push origin --delete claude/review-sknavigator-bugs-MNMBb
git checkout main
git pull
git checkout -b claude/review-sknavigator-bugs-MNMBb
```

### ขั้นที่ 2: ให้ Claude Code อ่านส่วน "3. Bug list + fix" ด้านล่าง แล้วสั่งให้ apply ทุกบัคบนเครื่องคุณตรงๆ

ที่บ้าน Claude Code มี Edit ตรงกับไฟล์ (ไม่ผ่าน MCP) — ไม่ติด truncation

---

## 3. Bug list + fix (ครบทั้ง 15 บัค)

### 🔴 HIGH

#### H1. campaign-tracker.html:743 — Sign quantity ไม่กันค่าลบ
```js
// FROM:
function addSign(){var q=+document.getElementById('sq').value;if(!q){alert('กรุณากรอกจำนวน');return}
// TO:
function addSign(){var q=+document.getElementById('sq').value;if(!q||q<0||!Number.isInteger(q)){alert('กรุณากรอกจำนวนเป็นจำนวนเต็มบวก');return}
```

#### H2. campaign-tracker.html:744 — addTx รับ 0 ไม่ได้ + NaN ผ่าน
```js
// FROM:
function addTx(){var amt=+document.getElementById('xa').value;if(!amt||amt<0){alert('กรุณากรอกจำนวนเงินเป็นค่าบวก');return}
// TO:
function addTx(){var amt=+document.getElementById('xa').value;if(isNaN(amt)||amt<=0){alert('กรุณากรอกจำนวนเงินเป็นค่าบวก');return}
```

#### H3. district-intel.html:386-388 — Traffy fetch ไม่มี timeout
#### H4. district-intel.html — race condition เมื่อสลับเขต
รวม 2 ข้อนี้แทนที่บล็อก fetch:
```js
// FROM (~line 386):
if(window._traffyAbort)window._traffyAbort.abort();
window._traffyAbort=new AbortController();
fetch('https://publicapi.traffy.in.th/teamchadchart-stat-api/geojson/v1?limit=1000',{signal:window._traffyAbort.signal})
.then(function(r){if(!r.ok)throw new Error('API '+r.status);return r.json();})
.then(function(data){
  if(!data.features||!data.features.length){el.textContent='ไม่พบข้อมูลจาก Traffy API';return;}
  var items=data.features.filter(function(f){return f.properties&&f.properties.district===currentDistrict;});

// TO:
if(window._traffyAbort)window._traffyAbort.abort();
if(window._traffyTimeout)clearTimeout(window._traffyTimeout);
window._traffyAbort=new AbortController();
var fetchDistrict=currentDistrict;
window._traffyTimeout=setTimeout(function(){try{window._traffyAbort.abort()}catch(e){}},10000);
fetch('https://publicapi.traffy.in.th/teamchadchart-stat-api/geojson/v1?limit=1000',{signal:window._traffyAbort.signal})
.then(function(r){if(!r.ok)throw new Error('API '+r.status);return r.json();})
.then(function(data){
  if(currentDistrict!==fetchDistrict)return;
  if(!data.features||!data.features.length){el.textContent='ไม่พบข้อมูลจาก Traffy API';return;}
  var items=data.features.filter(function(f){return f&&f.properties&&f.properties.district===fetchDistrict;});
```

แล้วที่ `.catch(...)` ต่อท้ายด้วย `.then` clear timeout:
```js
.catch(function(err){if(err.name==='AbortError')return;el.textContent='ไม่สามารถเชื่อมต่อ Traffy API';el.style.color='var(--red)';})
.then(function(){if(window._traffyTimeout){clearTimeout(window._traffyTimeout);window._traffyTimeout=null;}});
```

#### H5. index.html:1801, 2304 — `setInterval` ไม่ clear
แทนที่ 2 จุด:
```js
// At end of countdown IIFE (~line 1801):
// FROM:
tick();
setInterval(tick, 1000);
// TO:
tick();
if(window._cdTimer)clearInterval(window._cdTimer);
window._cdTimer=setInterval(tick, 1000);
window.addEventListener('beforeunload',function(){if(window._cdTimer){clearInterval(window._cdTimer);window._cdTimer=null;}});

// ECT auto-refresh (~line 2304):
// FROM:
var _ectTimer = setInterval(function(){
  if(document.hidden) return;
  window.loadEctNews(true);
}, ECT_AUTO_REFRESH_MS);
// TO:
if(window._ectTimer)clearInterval(window._ectTimer);
window._ectTimer = setInterval(function(){
  if(document.hidden) return;
  window.loadEctNews(true);
}, ECT_AUTO_REFRESH_MS);
window.addEventListener('beforeunload',function(){if(window._ectTimer){clearInterval(window._ectTimer);window._ectTimer=null;}});
```

### 🟡 MEDIUM

#### M1. campaign-tracker.html:778 — sort tiebreaker
```js
// FROM:
ftx.sort(function(a,b){return b.date>a.date?1:-1});
// TO:
ftx.sort(function(a,b){if(a.date===b.date)return b.id>a.id?1:-1;return b.date>a.date?1:-1});
```

#### M2. campaign-tracker.html:893 — try/catch ใน setItem
```js
// FROM:
URL.revokeObjectURL(url);localStorage.setItem('sk_lastExport',Date.now().toString());hideBackupBanner()
// TO:
URL.revokeObjectURL(url);try{localStorage.setItem('sk_lastExport',Date.now().toString())}catch(e){}hideBackupBanner()
```

#### M3. district-intel.html:703 — POI ID format consistency
```js
// FROM (in addPoi):
id: Date.now()+Math.random(),
// TO:
id: Date.now().toString(36)+Math.random().toString(36).slice(2,8),
```

และที่ removePoi (line 724):
```js
// FROM:
pois[catKey] = (pois[catKey]||[]).filter(function(p){return p.id!==id});
// TO:
pois[catKey] = (pois[catKey]||[]).filter(function(p){return String(p.id)!==String(id)});
```

#### M4. district-intel.html:392 — guard properties
รวมอยู่ใน H4 ด้านบนแล้ว (ที่ filter เปลี่ยนเป็น `f&&f.properties&&...`)

#### M5. district-intel.html:801 — GPS preview marker cleanup ตอนปิดฟอร์ม
```js
// FROM:
function toggleEl(id){var el=document.getElementById(id);el.style.display=el.style.display==='none'?'block':'none'}
// TO:
function toggleEl(id){var el=document.getElementById(id);el.style.display=el.style.display==='none'?'block':'none';if(id==='checkinForm'&&el.style.display==='none'&&window._gpsPreviewMarker){try{window._gpsPreviewMarker.remove()}catch(e){}window._gpsPreviewMarker=null}}
```

#### M6. phase-b.html:515-517 — เพิ่มลิงก์ #dont-section ใน sidebar
```html
<!-- FROM: -->
<a href="#do-section" class="sidebar-link" data-section="do-section">
  <span class="num">2.6</span> หาเสียง (DO/DON'T)
</a>
<!-- TO: -->
<a href="#do-section" class="sidebar-link" data-section="do-section">
  <span class="num">2.6a</span> สิ่งที่ทำได้ (DO)
</a>
<a href="#dont-section" class="sidebar-link" data-section="dont-section">
  <span class="num">2.6b</span> สิ่งที่ห้ามทำ (DON'T)
</a>
```

#### M7. phase-a/b/c/d-e.html — เพิ่ม @media print
ใส่ก่อน `</style>` ในทุกไฟล์ Phase A-E:
```css
@media print {
  .top-bar, .sidebar, .bottom-nav, .site-footer, .sidebar-back, .scroll-progress { display: none !important; }
  .content, .main-content, main { margin-left: 0 !important; padding: 0 !important; max-width: 100% !important; }
  body { background: #fff !important; color: #000 !important; }
  a { color: #000 !important; text-decoration: underline; }
  .topic-section, section { page-break-inside: avoid; }
}
```

### 🟢 LOW

#### L1. service-worker.js:61 — regex strict สำหรับ Traffy
```js
// FROM:
if (url.includes('api.') || url.includes('traffy') || url.includes('fondue')) {
// TO:
if (/^https:\/\/(publicapi\.traffy\.in\.th|.*\.fondue\.in\.th)\//.test(url)) {
```
+ bump `CACHE_NAME = 'sk-navigator-v12'`

#### L2. manifest.json — ย่อ name
```json
"name": "ส.ก. Navigator คู่มือเลือกตั้ง กทม.",
```

#### L3. campaign-tracker.html — parseFloat ป้องกัน NaN
3 จุด (lines ~756, ~779, ~825):
```js
// PATTERN: change `s+t.amt` → `s+(parseFloat(t.amt)||0)`
.reduce(function(s,t){return s+(parseFloat(t.amt)||0)},0)
```

---

## 4. False positive (ที่ subagent รายงานแต่ไม่ใช่บัค)

ห้ามแก้ตามนี้ — เป็น false positive ทั้งหมด:

1. **HUB "broken knowledge cards"** (qa-ect.html / bkk-universe.html / field-techniques.html / bkk-oss.html) — ไฟล์มีอยู่จริงในรีโพ
2. **Manifest icon `/las-logo-color.png`** — มีอยู่จริงที่ root
3. **Phase A `flag-walk.jpg` etc.** — มีอยู่จริงใน `img/`
4. **Decimal wage truncation** — `+"250.50"` = 250.5 ปกติ
5. **Bitwise OR sort** — โค้ดใช้ `||` (logical) ไม่ใช่ `|` (bitwise)
6. **Income CSV `-`** — `CN['in']='รายรับ'` ตั้งครบ
7. **t.law crash** — มี ternary guard อยู่แล้ว

---

## 5. Local files (เผื่อต้องการ pull ตรงๆ)

ทุกไฟล์ที่แก้แล้วถูก save ไว้ที่ `/home/user/sk-navigator-review/` บน machine นี้:
- `index.html`, `campaign-tracker.html`, `district-intel.html`
- `phase-a.html`, `phase-b.html`, `phase-c.html`, `phase-d-e.html`
- `manifest.json`, `service-worker.js`

ถ้าต้องการให้ผม `cat` ไฟล์ใดออกมาให้ใน chat (เพื่อ copy ไปที่อื่น) บอกได้ครับ
