#!/usr/bin/env python3
"""Build a reviewable teaching catalogue from tracked HTML; never infer legal approval."""
import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[2]
BASE = 'https://thundthornthep-ai.github.io/'
RULES = [
 ('corporate','บริษัทและธรรมาภิบาล',r'บริษัท|อำนาจกรรมการ|กรรมการบริษัท|หุ้น|company|corporate|sharehold|joint.venture|มติ|บริคณห์'),
 ('contract','สัญญาและหนี้',r'สัญญา|หนี้|ค้ำประกัน|อายุความ|มอบอำนาจ|ความลับ|ข้อห้ามแข่งขัน|ประกันภัย|อนุญาโต|dispute|insurance|non.compete|\bnda\b|contract|agreement|liability|indemn|warrant|force.majeure|termination|definitions|precedent'),
 ('investment','การลงทุนและการขยายธุรกิจ',r'ลงทุน|ต่างชาติ|ต่างด้าว|ควบรวม|ซื้อกิจการ|due.diligence|exit.strategy|\bipo\b|ระดมทุน|หลักทรัพย์|investment|nominee|boi|eec|merger|acquisition|foreign|franchise|กิจการ|deadlock'),
 ('labour','แรงงานและการจ้างงาน',r'แรงงาน|ลูกจ้าง|employment|labour|labor'),
 ('privacy','ข้อมูลส่วนบุคคล',r'pdpa|ข้อมูลส่วนบุคคล|privacy'),
 ('property','อสังหาริมทรัพย์',r'อสังหา|เช่า|คอนโด|ที่ดิน|condo|lease|property|hotel|real.estate'),
 ('tax','ภาษีและการเงิน',r'ภาษี|tax|transfer.pricing|finance'),
 ('ip','ทรัพย์สินทางปัญญา',r'ทรัพย์สินทางปัญญา|ลิขสิทธิ์|intellectual|ip-law|trademark'),
 ('consumer','ผู้บริโภคและการตลาด',r'ผู้บริโภค|การตลาด|consumer|marketing'),
 ('public','กฎหมายมหาชนและท้องถิ่น',r'ทุจริต|ประมูล|ทรัพย์สิน.*เจ้าหน้าที่|asset.declaration|corruption|bid.rigging|bkk-council'),
 ('professional','วิชาชีพและเทคโนโลยีกฎหมาย',r'lawyer|วิชาชีพ|ai-|analytics|practitioner|legal.tech'),
]
LABELS = dict((k,v) for k,v,_ in RULES)
LABELS['general'] = 'ความรู้ทั่วไปและรอจัดหมวด'

class Page(HTMLParser):
 def __init__(self, html):
  super().__init__(convert_charrefs=True)
  self.meta={}; self.links=[]; self.h1=[]; self.title=[]; self.ld=[]; self.text=[]
  self.lang='und'; self.capture=None; self.buf=[]; self.h=False; self.t=False; self.skip=0
  self.feed(html)
 def handle_starttag(self, tag, attrs):
  a=dict(attrs)
  if tag=='html': self.lang=a.get('lang','und').split('-')[0]
  if tag=='meta': self.meta[(a.get('name') or a.get('property') or a.get('http-equiv') or '').lower()]=a.get('content','')
  if tag in ('a','link') and a.get('href'): self.links.append(a)
  if tag=='h1': self.h=True
  if tag=='title': self.t=True
  if tag in ('script','style'):
   self.skip+=1
   if a.get('type')=='application/ld+json': self.capture=True; self.buf=[]
 def handle_endtag(self, tag):
  if tag=='h1': self.h=False
  if tag=='title': self.t=False
  if tag in ('script','style'):
   self.skip=max(0,self.skip-1)
   if tag=='script' and self.capture:
    try: self.ld.append(json.loads(''.join(self.buf)))
    except ValueError: pass
    self.capture=None
 def handle_data(self, data):
  if self.capture: self.buf.append(data)
  if self.h: self.h1.append(data)
  if self.t: self.title.append(data)
  if not self.skip: self.text.append(data)

def flat(value):
 if isinstance(value,dict):
  yield value
  for v in value.values(): yield from flat(v)
 elif isinstance(value,list):
  for v in value: yield from flat(v)

def clean(s): return re.sub(r'\s+',' ',s).strip()
def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def tracked(root): return subprocess.check_output(['git','-C',str(root),'ls-files','*.html'],text=True).splitlines()
def category(path,title):
 tags=[k for k,_,r in RULES if re.search(r,path+' '+title,re.I)]
 if '/las-cc-' in path and 'contract' not in tags: tags.insert(0,'contract')
 return tags or ['general']

def read_variant(root,path):
 raw=(root/path).read_text(encoding='utf-8'); p=Page(raw)
 article=next((o for o in flat(p.ld) if o.get('@type') in ('Article','BlogPosting','NewsArticle','TechArticle')), {})
 title=clean(' '.join(p.h1) or article.get('headline','') or ' '.join(p.title))
 return p,dict(path=path,title=title,language=p.lang,sha256=sha(raw),text_sha256=sha(clean(' '.join(p.text))),
   published=article.get('datePublished') or p.meta.get('article:published_time'),
   modified=article.get('dateModified') or p.meta.get('article:modified_time'),
   url=BASE+path, legal_status='unreviewed',article_schema=bool(article))

def build(root):
 files=tracked(root); groups={}; excluded=[]; routes=[]
 for path in files:
  p,v=read_variant(root,path)
  if p.meta.get('refresh'):
   excluded.append(dict(path=path,reason='redirect',target=p.meta['refresh'])); continue
  is_article=bool(re.match(r'(?:en/|th/)?articles/(?!.*-index\.html$)',path))
  is_blog=bool(re.match(r'(?:en/|th/)?blog/',path))
  if not (is_article or is_blog):
   excluded.append(dict(path=path,reason='navigation-template-service-or-profile')); continue
  # Blog tools/collections remain discoverable as resources, not counted as articles.
  kind='article' if is_article or v['article_schema'] else 'resource'
  identity=re.sub(r'^(en|th)/','',path).removesuffix('.html')
  entry=groups.setdefault(identity,dict(id=identity,kind=kind,title=v['title'],variants=[],tags=[],series=None,legal_status='unreviewed',taxonomy_status='proposed'))
  entry['variants'].append(v)
  entry['tags']=sorted(set(entry['tags']+category(path,v['title'])))
  m=re.search(r'las-(share|shield|cc|upsize|invest)-(\d+)\.html$',path)
  if m: entry['series']=m[1]; entry['episode']=int(m[2])
  routes.append(path)
 hub=Page((root/'knowledge-hub.html').read_text()); hub_paths=set()
 for a in hub.links:
  u=urlsplit(a['href'])
  if not u.netloc or u.netloc=='thundthornthep-ai.github.io': hub_paths.add(unquote(u.path).lstrip('/'))
 entries=sorted(groups.values(),key=lambda x:x['id'])
 for e in entries:
  if len(e['tags'])>1 and 'general' in e['tags']: e['tags'].remove('general')
  primary=next((v for v in e['variants'] if not v['path'].startswith(('en/','th/'))),e['variants'][0])
  e['title']=primary['title']; e['hub_linked']=any(v['path'] in hub_paths for v in e['variants'])
  e['variant_relation']='same-route-family-not-semantic-parity-verified' if len(e['variants'])>1 else 'single'
  risk=bool(re.search(r'อายุความ|ค้ำประกัน|แรงงาน|ต่างด้าว|pdpa|nominee|liability|termination|consumer|labour|employment', e['title']+' '+e['id'], re.I))
  e['review_priority']='high' if risk else 'normal'
  e['review_reason']='deadline-liability-or-change-sensitive-topic' if risk else 'baseline-review-required'
 scope=dict(tracked_html=len(files),catalogue_variants=len(routes),learning_items=len(entries),
  articles=sum(e['kind']=='article' for e in entries),resources=sum(e['kind']=='resource' for e in entries),
  excluded=len(excluded),unlinked_items=sum(not e['hub_linked'] for e in entries),
  legal_reviewed=0,source_tree=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip())
 assert len(routes)+len(excluded)==len(files)
 return dict(schema_version=1,scope=scope,categories=LABELS,items=entries,excluded=excluded,
  coverage_boundary='All tracked HTML in this GitHub snapshot accounted for. Other repositories, authenticated runtime overrides and external links require reconciliation. No full legal or translation review claimed.')

if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path,default=ROOT/'docs/knowledge-teaching/catalog.json'); a=ap.parse_args()
 data=build(ROOT); a.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(data['scope'],ensure_ascii=False))
