import json,unittest
from pathlib import Path
from build_catalog import ROOT,Page,build,read_variant
class CatalogueTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.data=build(ROOT);cls.items={i['id']:i for i in cls.data['items']}
 def test_every_tracked_file_accounted_for_once(self):
  paths=[v['path'] for i in self.items.values() for v in i['variants']]+[e['path'] for e in self.data['excluded']]
  self.assertEqual(len(paths),len(set(paths)));self.assertEqual(len(paths),self.data['scope']['tracked_html'])
 def test_saved_snapshot_matches_article_bytes_and_inventory(self):
  stored=json.loads((ROOT/'docs/knowledge-teaching/catalog.json').read_text())
  current={v['path']:v['sha256'] for i in self.items.values() for v in i['variants']}
  saved={v['path']:v['sha256'] for i in stored['items'] for v in i['variants']}
  self.assertEqual(saved,current)
  baseline_excluded={e['path'] for e in stored['excluded']}
  current_excluded={e['path'] for e in self.data['excluded'] if not e['path'].startswith('docs/knowledge-teaching/')}
  self.assertEqual(baseline_excluded,current_excluded)
 def test_supplemental_materials_preserve_file_identity_and_local_links(self):
  import hashlib
  items=json.loads((ROOT/'docs/knowledge-teaching/materials.json').read_text())
  self.assertEqual(len({i['id'] for i in items}),len(items))
  for i in items:
   self.assertNotIn(i['id'],self.items)
   self.assertEqual(i['kind'],'resource')
   self.assertTrue(set(i['tags']).issubset(self.data['categories']))
   for v in i['variants']:
    self.assertEqual(v['url'],v['path'])
    self.assertTrue(v['path'].startswith('materials/'))
    self.assertNotIn('..',Path(v['path']).parts)
    content=(ROOT/'docs/knowledge-teaching'/v['path']).read_bytes()
    self.assertTrue(content.startswith(b'%PDF-'))
    self.assertEqual(hashlib.sha256(content).hexdigest(),v['sha256'])
    self.assertEqual(len(content),v['bytes'])
 def test_redirect_is_not_a_lesson(self):
  self.assertNotIn('articles/anti-nominee-thailand',self.items)
  self.assertIn('articles/anti-nominee-thailand-legal-guide',self.items)
 def test_bilingual_variants_preserved_not_certified(self):
  x=self.items['articles/las-shield-07'];self.assertEqual(len(x['variants']),2)
  self.assertIn('not-semantic-parity-verified',x['variant_relation'])
 def test_no_legal_approval_inferred(self):
  self.assertTrue(all(i['legal_status']=='unreviewed' for i in self.items.values()))
 def test_discovery_does_not_drop_unlinked_shield(self):
  self.assertIn('articles/las-shield-03',self.items)
  self.assertFalse(self.items['articles/las-shield-03']['hub_linked'])
 def test_paths_exist_unique_and_acyclic(self):
  paths=json.loads((ROOT/'docs/knowledge-teaching/learning-paths.json').read_text());byid={p['id']:p for p in paths}
  def visit(id,ancestors):
   self.assertNotIn(id,ancestors)
   for pre in byid[id]['prerequisites']:visit(pre,ancestors+[id])
  for p in paths:
   visit(p['id'],[]);self.assertEqual(len(p['lessons']),len(set(p['lessons'])))
   for id in p['lessons']:self.assertIn(id,self.items)
 def test_dates_are_source_metadata(self):
  _,v=read_variant(ROOT,'articles/las-share-04.html');self.assertEqual(v['modified'],'2026-09-28')
 def test_parser_excludes_scripts_from_article_text(self):
  p=Page('<h1>A &amp; B</h1><script>SECRET</script><p>body</p>');self.assertNotIn('SECRET',p.text);self.assertIn('body',p.text)
 def test_all_variant_targets_exist(self):
  for i in self.items.values():
   for v in i['variants']:self.assertTrue((ROOT/v['path']).is_file())
 def test_no_placeholder_in_titles(self):
  self.assertTrue(all(i['title'] and '{{' not in i['title'] for i in self.items.values()))
if __name__=='__main__':unittest.main()
