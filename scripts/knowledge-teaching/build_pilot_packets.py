"""Local source packets for the initial ten variants; pending review is not a verdict."""
import hashlib,json
from pathlib import Path
from build_catalog import ROOT,Page,clean
PILOTS=[
 'articles/las-share-04.html','articles/las-share-05.html',
 'articles/las-cc-05.html','articles/las-cc-06.html',
 'articles/las-shield-04.html','articles/las-shield-05.html',
 'articles/las-shield-07.html','en/articles/las-shield-07.html',
 'articles/ai-legal-tech-thailand.html','en/articles/ai-legal-tech-thailand.html']

def build():
 queue=json.loads((ROOT/'docs/knowledge-teaching/review-queue.json').read_text());by_path={j['path']:j for j in queue['jobs']}
 packets=[]
 for path in PILOTS:
  raw=(ROOT/path).read_text();p=Page(raw)
  # Preserve every visible text node, including tables; segmentation is not claim extraction.
  nodes=[clean(t) for t in p.text if clean(t)]
  packets.append(dict(path=path,source_sha256=hashlib.sha256(raw.encode()).hexdigest(),status='pending_source_and_semantic_review',
   coverage_units=[dict(id=f'u{i:04}',text=t,status='unreviewed') for i,t in enumerate(nodes,1)],
   structured_data=p.ld,citation_candidates=by_path[path]['citations'],source_evidence=[],reviewer=None))
 return dict(scope='Ten pilot variants, not ten independent article topics; /en is a route and does not certify language or translation parity.',model_calls=0,packets=packets)
if __name__=='__main__':
 out=ROOT/'docs/knowledge-teaching/pilot-review-packets.json';d=build();out.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 print({'packets':len(d['packets']),'coverage_units':sum(len(p['coverage_units']) for p in d['packets'])})
