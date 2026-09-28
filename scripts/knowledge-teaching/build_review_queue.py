#!/usr/bin/env python3
"""Deterministic review queue. Produces no legal verdicts and makes no LLM calls."""
import hashlib,importlib.util,json
from pathlib import Path
from build_catalog import ROOT,Page,clean,sha
spec=importlib.util.spec_from_file_location('firewall',ROOT/'scripts/public-citation-firewall.py')
firewall=importlib.util.module_from_spec(spec);spec.loader.exec_module(firewall)
POLICY='source-bound-review-v1'
def build():
 data=json.loads((ROOT/'docs/knowledge-teaching/catalog.json').read_text()); jobs=[]; cites={}
 registry_sha=sha(''.join(p.name+'\n'+p.read_text() for p in sorted((ROOT/'scripts/legal-kb').glob('*.md'))))
 for item in data['items']:
  if item['kind']!='article':continue
  for variant in item['variants']:
   raw=(ROOT/variant['path']).read_text();p=Page(raw)
   pairs=sorted(set(firewall.extract_citations(raw)),key=lambda x:(x[0] or '',x[1]))
   refs=[{'statute':law,'section':sec,'binding_status':'unresolved' if law in (None,'unrecognized') else 'candidate'} for law,sec in pairs]
   for ref in refs:
    key=f"{ref['statute'] or 'UNBOUND'}:{ref['section']}"
    cites.setdefault(key,[]).append(variant['path'])
   # A cache may use this input key only together with source evidence, model,
   # prompt, reviewer and decision hashes. It is NOT a reusable approval by itself.
   key=sha(json.dumps([variant['sha256'],registry_sha,POLICY],ensure_ascii=False))
   jobs.append(dict(article_id=item['id'],path=variant['path'],article_sha256=variant['sha256'],input_key=key,
    priority=item['review_priority'],status='pending_source_packet',citations=refs,
    text_utf8_bytes=len(clean(' '.join(p.text)).encode()),source_verified=False,semantic_reviewed=False))
 return dict(policy=POLICY,registry_sha256=registry_sha,source_tree=data['scope']['source_tree'],
   warning='Citation candidates inherit extractor limitations: unbound sections, comma lists and range interiors require full-text review. Registry membership is not legal correctness. No model was called.',
   required_cache_fields=['input_key','official_source_sha256','effective_date','as_of','prompt_sha256','model_version','reviewer','decision_sha256'],
   jobs=sorted(jobs,key=lambda j:(j['priority']!='high',j['path'])),citation_index=cites)
if __name__=='__main__':
 d=build();(ROOT/'docs/knowledge-teaching/review-queue.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 print({'jobs':len(d['jobs']),'citation_candidates':len(d['citation_index']),'high_priority':sum(j['priority']=='high' for j in d['jobs'])})
