"""Static theme inventory: no legal verdict, DOM mutation or model call."""
import hashlib,json,re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from build_catalog import ROOT

class Styles(HTMLParser):
 def __init__(self,raw):
  super().__init__();self.inside=False;self.css=[];self.inline=[];self.classes=set();self.links=[];self.feed(raw)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='style':self.inside=True
  if 'style' in a:self.inline.append(a['style'])
  self.classes.update(a.get('class','').split())
  if tag=='link' and 'stylesheet' in a.get('rel',''):self.links.append(a.get('href',''))
 def handle_endtag(self,tag):
  if tag=='style':self.inside=False
 def handle_data(self,data):
  if self.inside:self.css.append(data)

def build():
 catalogue=json.loads((ROOT/'docs/knowledge-teaching/catalog.json').read_text());rows=[]
 for item in catalogue['items']:
  for v in item['variants']:
   raw=(ROOT/v['path']).read_text();p=Styles(raw);css='\n'.join(p.css)
   palette=Counter(x.lower() for x in re.findall(r'#[0-9a-fA-F]{3,8}\b',css+'\n'+'\n'.join(p.inline)))
   rows.append(dict(path=v['path'],kind=item['kind'],source_sha256=hashlib.sha256(raw.encode()).hexdigest(),embedded_css_sha256=hashlib.sha256(css.encode()).hexdigest(),template_hint='wiki-wrapper' if 'wiki-wrapper' in p.classes else 'other',inline_style_count=len(p.inline),hex_colors=dict(palette.most_common()),stylesheets=p.links,semantic_risk_classes=sorted(x for x in p.classes if re.search('risk|warning|success|danger',x,re.I)),status='pending_rendered_review'))
 return dict(scope='159 catalogued HTML variants; supplemental PDFs are not recolored',limitations='Static hex inventory only: named/rgb/variable/external CSS and runtime styles require browser review. Template hints and CSS fingerprints are not semantic equivalence.',count=len(rows),template_hints=dict(Counter(r['template_hint'] for r in rows)),distinct_embedded_css=len(set(r['embedded_css_sha256'] for r in rows)),items=rows)
if __name__=='__main__':
 d=build();(ROOT/'docs/knowledge-teaching/article-theme-audit.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in d.items() if k!='items'})
