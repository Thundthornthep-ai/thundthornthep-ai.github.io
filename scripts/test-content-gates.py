#!/usr/bin/env python3
"""Regression tests for the content-rules, internal-link and sitemap gates and their shared page scope."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import las_public_pages as pages  # noqa: E402


def load(name: str):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


rules = load("validate-content-rules")
links = load("check-internal-links")
sitemap = load("check-sitemap-coverage")

GOOD = """<!DOCTYPE html><html lang="th"><head>
<meta name="author" content="ธันย์ธรณ์เทพ แย้มอุทัย, Ph.D.">
<meta name="keywords" content="กฎหมาย, ธันย์ธรณ์เทพ แย้มอุทัย">
<script type="application/ld+json">{"author":{"@type":"Person","name":"Thundthornthep Yamoutai, Ph.D.",
"alternateName":"ธันย์ธรณ์เทพ แย้มอุทัย"},"keywords":["Thundthornthep Yamoutai Ph.D."]}</script>
</head><body id="top">
<div class="meta">โดย ธันย์ธรณ์เทพ แย้มอุทัย, Ph.D.</div>
<p>ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา 150 · คำพิพากษาศาลฎีกาที่ 4466/2553 · หนังสือ กค 0706(กม.01)/123</p>
<p>พระราชกฤษฎีกาที่ออกตามประมวลรัษฎากร [ต้องยืนยันแหล่งที่มา: พระราชกฤษฎีกาฉบับล่าสุด]</p>
<p>พระราชบัญญัติคุ้มครองแรงงาน (ฉบับที่ 9) พ.ศ. 2568 · เพดานเพิ่มโดยฉบับที่ 7 พ.ศ. 2562</p>
<p>15 มกราคม 2569 · <a href="#top">top</a> · <a href="other.html#part">other</a></p>
<!-- ดร. ธันย์ธรณ์เทพ in an outline comment is not published -->
<div class="disclaimer">ข้อสงวนสิทธิ์: บทความนี้จัดทำเพื่อวัตถุประสงค์ทางวิชาการ</div>
</body></html>
"""


def make_site(root: Path, files: dict[str, str], reviewed: tuple[str, ...] = ()) -> Path:
    for rel, body in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    (root / "learning-hub").mkdir(exist_ok=True)
    (root / "learning-hub" / "legal-reviews.json").write_text(
        json.dumps({"variants": {rel: {"status": "reviewed"} for rel in reviewed}}), encoding="utf-8"
    )
    (root / "scripts" / "legal-kb").mkdir(parents=True, exist_ok=True)
    (root / "scripts" / "legal-kb" / "supreme-court-verified.json").write_text(
        json.dumps({"judgments": [{"number": "4466/2553", "status": "verified"},
                                  {"number": "1111/2550", "status": "not-found"}]}),
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return root


def rule_ids(html: str) -> list[str]:
    return sorted({rule for rule, _detail in rules.check_article(html, {"4466/2553"})})


class ContentRuleTests(unittest.TestCase):
    def test_compliant_page_passes_every_rule(self) -> None:
        self.assertEqual(rule_ids(GOOD), [])
        self.assertEqual(rules.check_site_wide(GOOD), [])

    def test_cr1_missing_disclaimer(self) -> None:
        page = GOOD.replace('<div class="disclaimer">ข้อสงวนสิทธิ์: บทความนี้จัดทำเพื่อวัตถุประสงค์ทางวิชาการ</div>', "")
        self.assertEqual(rule_ids(page), ["CR1"])
        english = page.replace("</body>", "<p>This article does not constitute legal advice.</p></body>")
        self.assertEqual(rule_ids(english), [])

    def test_cr2_doctor_prefix(self) -> None:
        for bad in ("ดร.ธันย์ธรณ์เทพ แย้มอุทัย", "ดร. ธันย์ธรณ์เทพ", "Dr. Thundthornthep Yamoutai"):
            found = rules.check_site_wide(f"<p>{bad}</p>")
            self.assertEqual([rule for rule, _ in found], ["CR2"], bad)

    def test_cr3_credit_form(self) -> None:
        for bad in (
            '<div class="author-name">by ธันย์ธรณ์เทพ แย้มอุทัย (Thundthornthep Yamoutai, Ph.D.)</div>',
            '<p>โดย ธันย์ธรณ์เทพ แย้มอุทัย | LAS</p>',
            '<script type="application/ld+json">{"author":{"name":"Thundthornthep Yamoutai"}}</script>',
            '<a href="/">Thundthornthep Yamoutai, Phd.</a>',
        ):
            self.assertEqual(rule_ids(GOOD.replace("</body>", bad + "</body>")), ["CR3"], bad)

    def test_cr4_banned_sources(self) -> None:
        for bad in ('<a href="https://www.peeseri.com/x">x</a>', '<a href="http://thailaw.com/law">x</a>',
                    '<img src="https://deka-online.com/a.png">', "<p>ที่มา https://www.thailaw.com/x</p>"):
            self.assertEqual(rule_ids(GOOD.replace("</body>", bad + "</body>")), ["CR4"], bad)
        self.assertEqual(rule_ids(GOOD.replace("</body>", '<a href="https://thailaws.com/">x</a></body>')), [])

    def test_cr5_replacement_character(self) -> None:
        found = rules.check_site_wide("<p>มาตรการที่เหมาะ��ม</p>")
        self.assertEqual([rule for rule, _ in found], ["CR5", "CR5"])

    def test_cr6_supreme_court_flags(self) -> None:
        for bad in ("[ต้องยืนยันฎีกา]", "[ต้องยืนยันเลขคำพิพากษา]", "[must verify Supreme Court case]",
                    "[Supreme Court citation to be verified]", "[unconfirmed — Supreme Court decision]"):
            self.assertIn("CR6", rule_ids(GOOD.replace("</body>", f"<p>{bad}</p></body>")), bad)
        for fine in ("[ต้องยืนยันแหล่งที่มา: พระราชกฤษฎีกาฉบับล่าสุด]", "[ต้องยืนยันมาตรา]",
                     "[ต้องยืนยันแหล่งที่มา: ผลของคำพิพากษาของศาลต่างประเทศ]"):
            self.assertEqual(rule_ids(GOOD.replace("</body>", f"<p>{fine}</p></body>")), [], fine)

    def test_cr7_supreme_court_numbers(self) -> None:
        for bad in ("ฎ. 1091/2519", "คำพิพากษาศาลฎีกาที่ 1275/2543", "ฎีกาที่ ๑๒๗๕/๒๕๔๓",
                    "Supreme Court Judgment No. 1223/2549", "Supreme Court Decision No. 465/2534",
                    "as the Supreme Court held in Judgment 6403/2561", "ศาลฎีกาวินิจฉัย ฎ.1111/2550",
                    "Supreme Court cases. Do not use Judgment No. 1521/2566 as authority"):
            self.assertEqual(rule_ids(GOOD.replace("</body>", f"<p>{bad}</p></body>")), ["CR7"], bad)
        for fine in ("พระราชกฤษฎีกาที่ 5/2560", "Constitutional Court Ruling No. 4/2562", "Notification No. 5/2567",
                     "ฎ. 4466/2553", "Supreme Court Judgment 4466/2553"):
            self.assertEqual(rule_ids(GOOD.replace("</body>", f"<p>{fine}</p></body>")), [], fine)

    def test_cr8_labour_protection_act_version(self) -> None:
        only7 = GOOD.replace("พระราชบัญญัติคุ้มครองแรงงาน (ฉบับที่ 9) พ.ศ. 2568 · ", "พระราชบัญญัติคุ้มครองแรงงาน ")
        self.assertEqual(rule_ids(only7), ["CR8"])
        latest = GOOD.replace("</body>", "<p>ฉบับล่าสุดคือ พ.ร.บ.คุ้มครองแรงงาน (ฉบับที่ 7) พ.ศ. 2562</p></body>")
        self.assertEqual(rule_ids(latest), ["CR8"])
        english = GOOD.replace("</body>", "<p>LPA Amendment No. 7, B.E. 2562, the latest amendment</p></body>")
        self.assertEqual(rule_ids(english), ["CR8"])

    def test_cr9_section_abbreviation(self) -> None:
        for bad in ("ป.พ.พ. ม.391", "ป.พ.พ. — ม.391, 1167–1168", "ตาม ม. 1270"):
            self.assertEqual(rule_ids(GOOD.replace("</body>", f"<p>{bad}</p></body>")), ["CR9"], bad)

    def test_cr10_month_abbreviation(self) -> None:
        self.assertEqual(rule_ids(GOOD.replace("</body>", "<p>15 ม.ค. 2569</p></body>")), ["CR10"])
        self.assertEqual(rule_ids(GOOD.replace("</body>", "<p>ระเบียบ ก.พ. ว่าด้วย</p></body>")), [])

    def test_comments_are_ignored(self) -> None:
        page = GOOD.replace("</body>", "<!-- ฎ. 1091/2519 [ต้องยืนยันฎีกา] ม.391 peeseri.com --></body>")
        self.assertEqual(rule_ids(page), [])

    def test_scope_skips_redirect_stubs_and_runs_site_wide_rules_everywhere(self) -> None:
        stub = '<html><head><meta http-equiv="refresh" content="0;url=x"></head><body>ฎ. 1/2500</body></html>'
        with tempfile.TemporaryDirectory() as tmp:
            root = make_site(Path(tmp), {
                "articles/good.html": GOOD,
                "articles/stub.html": stub,
                "blog/x/reviewed.html": GOOD.replace("ข้อสงวนสิทธิ์", "ข้อความ").replace("disclaimer", "note"),
                "blog/x/campaign.html": "<p>ฎ. 1/2500 no disclaimer</p>",
                "404.html": "<p>ดร.ธันย์ธรณ์เทพ</p>",
            }, reviewed=("blog/x/reviewed.html",))
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                status = rules.main(["--root", str(root)])
            report = out.getvalue()
            self.assertEqual(status, 1)
            self.assertIn("[CR1] blog/x/reviewed.html", report)
            self.assertIn("[CR2] 404.html", report)
            self.assertNotIn("stub.html", report)
            self.assertNotIn("campaign.html", report)
            self.assertNotIn("articles/good.html", report)

    def test_missing_register_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_site(Path(tmp), {"articles/good.html": GOOD})
            (root / "scripts" / "legal-kb" / "supreme-court-verified.json").unlink()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(rules.main(["--root", str(root)]), 3)


class InternalLinkTests(unittest.TestCase):
    def run_links(self, root: Path, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        links._parsed.clear()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            status = links.main(["--root", str(root), *args])
        return status, out.getvalue()

    def test_local_links_resolve_and_broken_ones_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_site(Path(tmp), {
                "index.html": '<a href="articles/a.html">a</a><a href="/blog/x/">blog</a>',
                "knowledge-hub.html": '<a href="https://thundthornthep-ai.github.io/articles/a.html#s1">a</a>',
                "articles/a.html": '<h2 id="s1">x</h2><a href="b">b</a><a href="../index.html">home</a>'
                                   '<a href="https://example.com/x.html">ext</a><a href="mailto:a@b.c">m</a>'
                                   '<a href="#/route">r</a><a href="?q=1">q</a><img src="../img/logo.png">',
                "articles/b.html": "<p>b</p>",
                "blog/x/index.html": "<p>x</p>",
                "img/logo.png": "png",
            })
            status, report = self.run_links(root)
            self.assertEqual(status, 0, report)

    def test_missing_targets_and_anchors_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_site(Path(tmp), {
                "articles/a.html": '<a href="ma-thailand-guide.html">x</a><a href="#references">refs</a>'
                                   '<a href="https://thundthornthep-ai.github.io/en/knowledge-hub.html">hub</a>'
                                   '<link rel="alternate" hreflang="en" href="/en/articles/a.html">',
                "en/articles/b.html": '<a href="../all-content.html">all</a><a href="/articles/a.html#nope">a</a>',
            })
            status, report = self.run_links(root)
            self.assertEqual(status, 1)
            for needle in ("ma-thailand-guide.html — target missing", "no id or name 'references'",
                           "en/knowledge-hub.html — target missing", "/en/articles/a.html — target missing",
                           "../all-content.html — target missing (en/all-content.html)", "no id or name 'nope'"):
                self.assertIn(needle, report)
            status, report = self.run_links(root, "--no-anchors")
            self.assertNotIn("no id or name", report)

    def test_scripts_and_comments_are_not_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_site(Path(tmp), {
                "articles/a.html": '<!-- <a href="gone.html">x</a> --><script>var s = \'<a href="gone2.html">\';</script>'
                                   '<a href="${url}">t</a>',
            })
            self.assertEqual(self.run_links(root)[0], 0)


class SitemapTests(unittest.TestCase):
    def test_public_articles_must_be_listed(self) -> None:
        stub = '<meta http-equiv="refresh" content="0;url=x">'
        with tempfile.TemporaryDirectory() as tmp:
            root = make_site(Path(tmp), {
                "articles/listed.html": "<p>a</p>",
                "articles/missing.html": "<p>b</p>",
                "articles/stub.html": stub,
                "articles/hidden.html": '<meta name="robots" content="noindex, follow">',
                "blog/x/reviewed.html": "<p>c</p>",
                "blog/x/campaign.html": "<p>d</p>",
                "media.html": stub,
                "sitemap.xml": '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                               "<url><loc>https://thundthornthep-ai.github.io/articles/listed.html</loc></url>"
                               "<url><loc>https://thundthornthep-ai.github.io/media.html</loc></url>"
                               "<url><loc>https://thundthornthep-ai.github.io/</loc></url></urlset>",
            }, reviewed=("blog/x/reviewed.html",))
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                status = sitemap.main(["--root", str(root)])
            report = out.getvalue()
            self.assertEqual(status, 1)
            self.assertIn("[MISSING] articles/missing.html", report)
            self.assertIn("[MISSING] blog/x/reviewed.html", report)
            self.assertNotIn("stub.html", report)
            self.assertNotIn("hidden.html", report)
            self.assertNotIn("campaign.html", report)
            self.assertIn("[WARN] media.html — listed but it is a redirect stub", report)
            self.assertIn("[WARN] index.html — listed but the file does not exist", report)


class ScopeTests(unittest.TestCase):
    def test_scope_is_articles_plus_reviewed_blog_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_site(Path(tmp), {
                "articles/a.html": "a", "en/articles/b.html": "b", "blog/x/r.html": "r", "blog/x/c.html": "c",
            }, reviewed=("articles/a.html", "blog/x/r.html", "en/blog/x/gone.html"))
            self.assertEqual(pages.citation_scope(root),
                             ["articles/a.html", "blog/x/r.html", "en/articles/b.html", "en/blog/x/gone.html"])
            self.assertTrue(pages.in_citation_scope("blog/x/r.html", root))
            self.assertFalse(pages.in_citation_scope("blog/x/c.html", root))

    def test_malformed_registry_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_site(Path(tmp), {"articles/a.html": "a"})
            (root / "learning-hub" / "legal-reviews.json").write_text("{", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                pages.citation_scope(root)


if __name__ == "__main__":
    unittest.main()
