import hashlib,json,subprocess,unittest
from pathlib import Path
from build_catalog import ROOT,Page,clean

class ThemePilotTests(unittest.TestCase):
 def test_theme_only_text_and_structured_data_unchanged(self):
  records=json.loads((ROOT/'docs/knowledge-teaching/theme-pilot.json').read_text())
  for r in records:
   before=subprocess.check_output(['git','show',f"ebc851b:{r['path']}"],cwd=ROOT,text=True)
   after=(ROOT/r['path']).read_text()
   self.assertEqual(hashlib.sha256(before.encode()).hexdigest(),r['before_sha256'])
   self.assertEqual(clean(' '.join(Page(before).text)),clean(' '.join(Page(after).text)))
   self.assertEqual(Page(before).ld,Page(after).ld)
   self.assertEqual(after.count('/css/knowledge-article-theme.css'),1)
   self.assertEqual(after.count('class="las-knowledge-article"'),1)
 def test_scope_is_only_three_articles_and_css_is_opt_in(self):
  records=json.loads((ROOT/'docs/knowledge-teaching/theme-pilot.json').read_text())
  self.assertEqual(len(records),3)
  css=(ROOT/'css/knowledge-article-theme.css').read_text()
  self.assertNotIn('!important',css)
  self.assertNotIn('.risk-high {',css)

if __name__=='__main__':unittest.main()
