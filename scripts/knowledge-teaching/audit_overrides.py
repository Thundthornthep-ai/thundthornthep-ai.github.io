#!/usr/bin/env python3
"""Read-only reconciliation of an explicitly supplied LAS checkout; emits metadata only."""
import argparse,json,re
from pathlib import Path
from build_catalog import Page,clean,sha,read_variant,ROOT

def audit(checkout):
 mapping=checkout/'server/lib/hub-local-articles.ts'
 text=mapping.read_text(); imports=dict((key,name) for key,name in re.findall(r'import\s+(\w+)\s+from\s+"../hub-articles/([^"/]+)\.js"',text))
 rows=[]
 for route,key in re.findall(r'"(/articles/[^"\s]+\.html)":\s*(\w+)',text):
  name=imports[key]; file=checkout/'server/hub-articles'/f'{name}.html'
  if not file.exists(): rows.append(dict(route=route,status='source-missing')); continue
  raw=file.read_text(); p=Page(raw); title=clean(' '.join(p.h1) or ' '.join(p.title))
  public=ROOT/route.lstrip('/')
  r=dict(route=route,local_title=title,local_sha256=sha(raw),status='runtime-unverified')
  if public.exists():
   _,v=read_variant(ROOT,route.lstrip('/')); r.update(github_title=v['title'],github_sha256=v['sha256'],same_bytes=sha(raw)==v['sha256'],same_heading=title==v['title'])
  else: r['status']='github-source-missing'
  rows.append(r)
 return dict(scope='Read-only local checkout snapshot; dirty checkout is not production authority. No content copied or deployed.',mapped_routes=len(rows),heading_mismatches=sum(r.get('same_heading') is False for r in rows),items=rows)
if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('checkout',type=Path); ap.add_argument('--output',required=True,type=Path); a=ap.parse_args()
 data=audit(a.checkout); a.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n'); print({k:v for k,v in data.items() if k!='items'})
