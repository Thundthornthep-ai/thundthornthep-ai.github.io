import { preferredPaths } from './curriculum-policy.js';
const $ = id => document.getElementById(id);
const el = (tag, text, cls) => { const n=document.createElement(tag); if(text)n.textContent=text; if(cls)n.className=cls; return n; };
let data, paths, activeTag='all';
function link(variant) { const a=el('a',`${variant.language.toUpperCase()} · ${variant.path.startsWith("en/")?"ฉบับ /en":"ฉบับหลัก"}`);a.href=variant.url;a.target='_blank';a.rel='noopener';return a; }
function renderCatalog() {
 const needle=$('search').value.trim().toLocaleLowerCase();
 const list=data.items.filter(i=>(activeTag==='all'||i.tags.includes(activeTag))&&($('kind').value==='all'||i.kind===$('kind').value)&&($('language').value==='all'||i.variants.some(v=>v.language===$('language').value))&&(!needle||[i.title,i.id,...i.variants.map(v=>v.title),...i.tags.map(t=>data.categories[t])].join(' ').toLocaleLowerCase().includes(needle)));
 $('count').textContent=`พบ ${list.length} เรื่อง จาก ${data.items.length} เรื่อง`; $('catalog').replaceChildren();
 for(const i of list){const card=el('article',null,'card');card.append(el('small',i.series?`LAS ${i.series.toUpperCase()} · ตอน ${i.episode}`:i.kind==='resource'?'สื่อประกอบ':'บทความ'));card.append(el('h3',i.title));const tags=el('div');i.tags.forEach(t=>tags.append(el('span',data.categories[t],'tag')));card.append(tags,el('span','รอทบทวนข้อกฎหมายทั้งฉบับ','tag status'));const dates=[...new Set(i.variants.map(v=>v.modified).filter(Boolean))];card.append(el('p',`ปรับปรุงตามต้นฉบับ: ${dates.join(' / ')||'ไม่พบข้อมูลวันที่'}`,'muted'));const links=el('div',null,'links row');i.variants.filter(v=>$('language').value==='all'||v.language===$('language').value).forEach(v=>links.append(link(v)));card.append(links);$('catalog').append(card);}
 if(!list.length)$('catalog').append(el('p','ไม่พบเรื่องที่ตรงกับตัวกรอง ลองเปลี่ยนคำค้นหรือหมวดหมู่','empty'));
}
function showPath(path){const target=$('lesson');target.hidden=false;target.replaceChildren(el('h3',path.title),el('p',`ควรทบทวนก่อน: ${path.prerequisites.map(id=>paths.find(p=>p.id===id).title).join(' → ')||'เริ่มได้จากบทแรก'}`));const ol=el('ol');path.lessons.forEach(id=>{const item=data.items.find(i=>i.id===id);const li=el('li');const a=link(item.variants[0]);a.textContent=item.title;li.append(a);ol.append(li);});target.append(ol,el('h4','งานฝึกท้ายเส้นทาง'),el('p',path.exercise),el('p','เกณฑ์ประเมิน: ระบุประเด็นครบ อ้างหลักฐานตรงเรื่อง แยกข้อเท็จจริงกับข้อสรุป และระบุสิ่งที่ยังไม่ทราบ','muted'));}
function pathIcon(id) {
 const shapes = {
  foundation: 'M4 4h6a3 3 0 0 1 3 3v14a4 4 0 0 0-4-2H4zM13 7a3 3 0 0 1 3-3h4v15h-4a3 3 0 0 0-3 2',
  corporate: 'M4 21V5h10v16M14 11h6v10M7 8h4M7 12h4M7 16h4M2 21h20',
  drafting: 'M6 3h9l4 4v14H6zM14 3v5h5M9 12h7M9 16h5',
  risk: 'M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6',
  growth: 'M4 17l6-6 4 3 6-9M14 5h6v6'
 };
 const chip = el('span',null,'cute-icon'); chip.setAttribute('aria-hidden','true');
 const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
 for (const [key,value] of Object.entries({viewBox:'0 0 24 24',fill:'none',stroke:'currentColor','stroke-width':'1.7','stroke-linecap':'round','stroke-linejoin':'round'})) svg.setAttribute(key,value);
 const path = document.createElementNS('http://www.w3.org/2000/svg','path');path.setAttribute('d',shapes[id]);svg.append(path);chip.append(svg);return chip;
}
function renderPaths(){ $('paths').replaceChildren();for(const id of preferredPaths($('audience').value)){const p=paths.find(x=>x.id===id);const card=el('article',null,'path');card.append(pathIcon(p.id),el('small',`${p.lessons.length} บทเรียน · ลำดับเสนอสำหรับผู้สอน`),el('h3',p.title),el('p',p.outcome));const b=el('button','ดูลำดับบทเรียน');b.addEventListener('click',()=>showPath(p));card.append(b);$('paths').append(card);}}
async function start(){
 const responses=await Promise.all(['catalog.json','learning-paths.json','override-audit.json'].map(p=>fetch(p).then(r=>{if(!r.ok)throw Error(`อ่าน ${p} ไม่สำเร็จ`);return r.json();})));
 [data,paths]=responses;const overrides=responses[2];
 for(const [label,value] of [['บทความ',data.scope.articles],['คู่มือและสื่อ',data.scope.resources],['ฉบับเอกสาร',data.scope.catalogue_variants],['เส้นทางเรียน',paths.length]]){const n=el('div',null,'stat');n.append(el('strong',String(value)),el('span',label));$('stats').append(n);}
 for(const [id,label] of [['all','ทุกหมวด'],...Object.entries(data.categories).filter(([id])=>data.items.some(i=>i.tags.includes(id)))]){const b=el('button',label);b.setAttribute('aria-pressed',String(id==='all'));b.addEventListener('click',()=>{activeTag=id;for(const t of $('tags').children)t.setAttribute('aria-pressed','false');b.setAttribute('aria-pressed','true');renderCatalog();});$('tags').append(b);}
 $('overrideSummary').textContent=`สำเนาที่ตรวจพบ ${overrides.mapped_routes} เส้นทาง · ชื่อหัวเรื่องต่างกัน ${overrides.heading_mismatches} เส้นทาง (ยังไม่ยืนยันว่าเนื้อหาขัดกัน)`;
 overrides.items.forEach(i=>$('overrides').append(el('li',`${i.route} — สำเนา LAS: ${i.local_title||'ไม่พบต้นฉบับ'} | GitHub: ${i.github_title||'ไม่พบ'} | ต้องตรวจระบบจริง`)));
 $('revision').textContent=data.scope.source_tree.slice(0,7);['search','kind','language'].forEach(id=>$(id).addEventListener('input',renderCatalog));$('audience').addEventListener('change',renderPaths);renderPaths();renderCatalog();
}
start().catch(e=>{$('count').textContent=`เปิดทะเบียนไม่ได้: ${e.message}`;});
