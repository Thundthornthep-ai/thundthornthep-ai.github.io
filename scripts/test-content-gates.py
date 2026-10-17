#!/usr/bin/env python3
"""Regression tests for the content-rules, template-structure, internal-link and sitemap gates and their shared page
scope."""
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
template = load("check-template-structure")
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
                     "Administrative Court Case No. 12/2565", "Court of Appeal Decision No. 300/2560",
                     "Supreme Administrative Court Judgment No. 7/2564",
                     "ฎ. 4466/2553", "Supreme Court Judgment 4466/2553"):
            self.assertEqual(rule_ids(GOOD.replace("</body>", f"<p>{fine}</p></body>")), [], fine)

    def test_cr8_labour_protection_act_version(self) -> None:
        only7 = GOOD.replace("พระราชบัญญัติคุ้มครองแรงงาน (ฉบับที่ 9) พ.ศ. 2568 · ", "พระราชบัญญัติคุ้มครองแรงงาน ")
        self.assertEqual(rule_ids(only7), ["CR8"])
        latest = GOOD.replace("</body>", "<p>ฉบับล่าสุดคือ พ.ร.บ.คุ้มครองแรงงาน (ฉบับที่ 7) พ.ศ. 2562</p></body>")
        self.assertEqual(rule_ids(latest), ["CR8"])
        english = GOOD.replace("</body>", "<p>LPA Amendment No. 7, B.E. 2562, the latest amendment</p></body>")
        self.assertEqual(rule_ids(english), ["CR8"])
        # an unrelated 2568 date elsewhere on the page is not a reference to amendment No. 9
        only7_dated = only7.replace("</body>", "<p>ปรับปรุงเมื่อวันที่ 17 ตุลาคม 2568</p></body>")
        self.assertEqual(rule_ids(only7_dated), ["CR8"])

    def test_cr7_court_named_after_the_number(self) -> None:
        # no court named before the number, so only the words after it identify the Supreme Court
        no_court = GOOD.replace(" · คำพิพากษาศาลฎีกาที่ 4466/2553", "")
        self.assertEqual(rule_ids(no_court), [])
        for noun in ("Judgment", "Decision", "Case", "Ruling"):
            later = no_court.replace("</body>", f"<p>{noun} No. 9999/2566 of the Supreme Court held otherwise.</p></body>")
            self.assertEqual(rule_ids(later), ["CR7"], noun)

    def test_cr7_number_belongs_to_the_court_that_governs_it(self) -> None:
        # the last court named before the number governs, so an earlier Supreme Court mention does not capture it
        other = "<p>The Supreme Court discussed an earlier matter. The Constitutional Court issued Decision No. 4/2562.</p>"
        self.assertEqual(rule_ids(GOOD.replace("</body>", other + "</body>")), [])
        # a court named right after the number wins over one named before it
        after = "<p>The Constitutional Court agreed with Judgment No. 9999/2566 of the Supreme Court.</p>"
        self.assertEqual(rule_ids(GOOD.replace("</body>", after + "</body>")), ["CR7"])

    def test_cr2_prefix_in_its_own_element(self) -> None:
        split = GOOD.replace("</body>", "<p><span>Dr.</span><span>Thundthornthep Yamoutai, Ph.D.</span></p></body>")
        self.assertIn(("CR2"), {rule for rule, _detail in rules.check_site_wide(split)})

    def test_cr7_thai_number_first_citations(self) -> None:
        no_court = GOOD.replace(" · คำพิพากษาศาลฎีกาที่ 4466/2553", "")
        bad = no_court.replace("</body>", "<p>คำพิพากษาที่ 9999/2566 ของศาลฎีกาวางหลักไว้</p></body>")
        self.assertEqual(rule_ids(bad), ["CR7"])
        fine = no_court.replace("</body>", "<p>คำวินิจฉัยที่ 4/2562 ของศาลรัฐธรรมนูญ</p></body>")
        self.assertEqual(rule_ids(fine), [])

    def test_cr2_prefix_with_an_entity_between_elements(self) -> None:
        split = GOOD.replace("</body>", "<p><span>Dr.&nbsp;</span><span>Thundthornthep Yamoutai, Ph.D.</span></p></body>")
        self.assertIn("CR2", {rule for rule, _detail in rules.check_site_wide(split)})

    def test_cr8_no9_of_another_statute_does_not_count(self) -> None:
        page = GOOD.replace(
            "<p>พระราชบัญญัติคุ้มครองแรงงาน (ฉบับที่ 9) พ.ศ. 2568 · เพดานเพิ่มโดยฉบับที่ 7 พ.ศ. 2562</p>",
            "<p>Labour Protection Act Amendment No. 7. The Social Security Act Amendment No. 9.</p>",
        )
        self.assertEqual(rule_ids(page), ["CR8"])
        named_after = page.replace("The Social Security Act Amendment No. 9.", "Amendment No. 9 of the Labour Protection Act.")
        self.assertEqual(rule_ids(named_after), [])

    def test_cr8_amendment_numbers_bound_to_the_act(self) -> None:
        only7 = GOOD.replace("พระราชบัญญัติคุ้มครองแรงงาน (ฉบับที่ 9) พ.ศ. 2568 · ", "พระราชบัญญัติคุ้มครองแรงงาน ")
        # No. 7 named without its year
        no_year = only7.replace("ฉบับที่ 7 พ.ศ. 2562", "ฉบับที่ 7")
        self.assertEqual(rule_ids(no_year), ["CR8"])
        # an unrelated statute's No. 9 far from the Act's name does not satisfy the rule
        filler = "ข้อความอื่น " * 40
        other9 = only7.replace("</body>", f"<p>{filler}ประมวลรัษฎากร ฉบับที่ 9</p></body>")
        self.assertEqual(rule_ids(other9), ["CR8"])

    def test_cr9_section_abbreviation(self) -> None:
        for bad in ("ป.พ.พ. ม.391", "ป.พ.พ. — ม.391, 1167–1168", "ตาม ม. 1270"):
            self.assertEqual(rule_ids(GOOD.replace("</body>", f"<p>{bad}</p></body>")), ["CR9"], bad)

    def test_cr10_month_abbreviation(self) -> None:
        self.assertEqual(rule_ids(GOOD.replace("</body>", "<p>15 ม.ค. 2569</p></body>")), ["CR10"])
        self.assertEqual(rule_ids(GOOD.replace("</body>", "<p>ระเบียบ ก.พ. ว่าด้วย</p></body>")), [])

    FAQ_LD = ('<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":['
              '{"@type":"Question","name":"สัญญาเช่าต้องจดทะเบียนเมื่อใด?","acceptedAnswer":{"@type":"Answer","text":"x"}},'
              '{"@type":"Question","name":"What is a lease?","acceptedAnswer":{"@type":"Answer","text":"y"}}]}</script>')

    def faq_page(self, body: str = "", ld: str | None = None) -> str:
        return GOOD.replace("</head>", (self.FAQ_LD if ld is None else ld) + "</head>").replace("</body>", body + "</body>")

    def test_cr11_faq_jsonld_without_a_visible_faq(self) -> None:
        # TPL-05: FAQPage JSON-LD that the reader never sees, an HTML comment naming the FAQ does not count
        self.assertEqual(rule_ids(self.faq_page("<!-- JSON-LD FAQPage Schema -->")), ["CR11"])
        # the same block inside an @graph array
        graph = ('<script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"Article"},'
                 '{"@type":"FAQPage","mainEntity":{"@type":"Question","name":"Hidden question?"}}]}</script>')
        self.assertEqual(rule_ids(self.faq_page(ld=graph)), ["CR11"])
        # a question shown word for word, or a visible FAQ section, is a visible FAQ
        shown = self.faq_page("<h3>What is a lease?</h3><p>y</p>")
        self.assertEqual(rule_ids(shown), [])
        section = self.faq_page('<h2>คำถามที่พบบ่อย</h2><div class="faq-item"><div class="faq-q">Q1: เช่าเมื่อใด?</div></div>')
        self.assertEqual(rule_ids(section), [])
        # inline markup inside a shown question keeps it word for word (Codex review of PR #80)
        inline = self.faq_page("<h3>What is a <em>lease</em>?</h3><p>y</p>")
        self.assertEqual(rule_ids(inline), [])
        self.assertEqual([detail for _, detail in rules.check_warnings(inline)], ["สัญญาเช่าต้องจดทะเบียนเมื่อใด?"])
        # the JSON-LD text itself is not visible text
        self.assertEqual(rules.check_faq(self.faq_page())[0][0][0], "CR11")
        # inert <template> contents are not visible either (Codex review of PR #80, round 14)
        self.assertEqual(rule_ids(self.faq_page("<template><h3>What is a lease?</h3></template>")), ["CR11"])
        self.assertEqual(rule_ids(self.faq_page('<template><div class="faq-item">Q</div></template>')), ["CR11"])
        # an <iframe> fallback body is raw text a browser does not show (Codex review of PR #80, round 38)
        self.assertEqual(rule_ids(self.faq_page('<iframe src="x.html"><h2>คำถามที่พบบ่อย</h2><h3>What is a lease?</h3></iframe>')), ["CR11"])
        # an empty FAQPage fails, and data-class is not a FAQ class (Codex review of PR #80, round 15)
        empty = '<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}</script>'
        self.assertEqual(rule_ids(self.faq_page(ld=empty)), ["CR11"])
        self.assertEqual(rule_ids(self.faq_page('<div data-class="faq">not an FAQ</div>')), ["CR11"])
        # each FAQPage object needs a question, and "no-faq" is not a FAQ class (Codex review of PR #80, round 17)
        two = self.FAQ_LD + empty
        self.assertEqual(rule_ids(self.faq_page("<h3>What is a lease?</h3>", ld=two)), ["CR11"])
        self.assertEqual(rule_ids(self.faq_page('<div class="no-faq">x</div>')), ["CR11"])
        self.assertEqual(rule_ids(self.faq_page('<div class="box faq-item">x</div>')), [])
        self.assertEqual(rule_ids(self.faq_page("<div class=faq-item>x</div>")), [])
        # a class written inside another attribute's value is no class; the word "hidden" in a title hides nothing
        # (Codex review of PR #80, round 39)
        self.assertEqual(rule_ids(self.faq_page('<div title="x class=faq-item">x</div>')), ["CR11"])
        # a character reference in an attribute value is decoded as the browser does; a "<body>" in a head comment does
        # not start the body (Codex review of PR #80, round 40)
        self.assertEqual(rule_ids(self.faq_page('<div style="display&#58;none"><h3>What is a lease?</h3></div>')), ["CR11"])
        titled = self.faq_page().replace("</head>", "<!-- <body> --><title>What is a lease?</title></head>", 1)
        self.assertEqual(rule_ids(titled), ["CR11"])
        self.assertEqual(rule_ids(self.faq_page('<div title="section hidden by default"><h3>What is a lease?</h3></div>')), [])
        # a FAQ class outside the body is no FAQ section (Codex review of PR #80, round 35)
        outside = self.faq_page().replace('<html lang="th">', '<html lang="th" class="faq-page">', 1)
        self.assertIn('class="faq-page"', outside)
        self.assertEqual(rule_ids(outside), ["CR11"])
        # a FAQ heading with inline markup is a FAQ heading (Codex review of PR #80, round 18)
        for heading in ("<h2>Frequently <em>Asked</em> Questions</h2>", "<h2><em>คำถาม</em>ที่พบบ่อย</h2>"):
            self.assertEqual(rule_ids(self.faq_page(heading)), [], heading)
        # a nested template does not end the outer one (Codex review of PR #80, round 16)
        self.assertEqual(rule_ids(self.faq_page("<template><template></template><h3>What is a lease?</h3></template>")),
                         ["CR11"])
        # nor is text in a hidden element (Codex review of PR #80, round 20)
        self.assertEqual(rule_ids(self.faq_page("<div hidden><div>x</div><h3>What is a lease?</h3></div>")), ["CR11"])
        self.assertEqual(rule_ids(self.faq_page('<div aria-hidden="true"><h3>What is a lease?</h3></div>')), ["CR11"])
        # a ">" inside a quoted attribute does not end the tag (round 25)
        self.assertEqual(rule_ids(self.faq_page('<div data-note="1 > 0" hidden><h3>What is a lease?</h3></div>')), ["CR11"])
        # a style may quote a value with the other quote type (Codex review of PR #80, round 26)
        self.assertEqual(rule_ids(self.faq_page(
            """<div style="font-family:'Arial'; display:none"><h3>What is a lease?</h3></div>""")), ["CR11"])
        self.assertEqual(rule_ids(self.faq_page('<div data-hidden="no"><h3>What is a lease?</h3></div>')), [])
        # inline display:none hides too, and FAQPage may be written as its full IRI (Codex review of PR #80, round 21)
        self.assertEqual(rule_ids(self.faq_page('<div style="color:red; display: none"><h3>What is a lease?</h3></div>')),
                         ["CR11"])
        for style in ("style=display:none", "style=visibility:hidden"):
            self.assertEqual(rule_ids(self.faq_page(f"<div {style}><h3>What is a lease?</h3></div>")), ["CR11"], style)
        # an unquoted style ends at whitespace: a later attribute value does not hide the element (round 24)
        self.assertEqual(rule_ids(self.faq_page("<div style=color:red data-note=display:none><h3>What is a lease?</h3></div>")),
                         [])
        iri = '<script type="application/ld+json">{"@type":"https://schema.org/FAQPage","mainEntity":[{"@type":"Question","name":"Hidden?"}]}</script>'
        self.assertEqual(rule_ids(self.faq_page(ld=iri)), ["CR11"])
        # a ">" in a quoted attribute of the JSON-LD tag does not hide the block (round 27)
        quoted = '<script data-note="1 > 0" type="application/ld+json">{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":"Hidden?"}]}</script>'
        self.assertEqual(rule_ids(self.faq_page(ld=quoted)), ["CR11"])
        # a script end tag may hold whitespace (round 32)
        spaced = self.FAQ_LD.replace("</script>", "</script >")
        self.assertEqual(rule_ids(self.faq_page(ld=spaced)), ["CR11"])
        # a <title> repeating a question is not a visible FAQ (round 31)
        titled = self.faq_page().replace("<head>", "<head><title>What is a lease?</title>", 1)
        self.assertNotEqual(titled, self.faq_page())
        self.assertEqual(rule_ids(titled), ["CR11"])

    def test_w11_faq_wording_drift_is_reported_not_failed(self) -> None:
        page = self.faq_page("<h3>What is a lease?</h3>")
        self.assertEqual(rule_ids(page), [])
        self.assertEqual([(rule, detail) for rule, detail in rules.check_warnings(page)],
                         [("W11", "สัญญาเช่าต้องจดทะเบียนเมื่อใด?")])
        self.assertEqual(rules.check_warnings(GOOD), [])

    def test_cr12_free_form_section_hedge(self) -> None:
        # VF-3: the hedge on las-cc-06 that the corpus answers
        bad = ("[ส่วนกฎที่ว่าการเลิกสัญญาไม่กระทบสิทธิเรียกค่าเสียหายนั้น ใกล้เคียงกับข้อความท้ายมาตรา 391 มากกว่า — "
               "ต้องยืนยันมาตราที่ถูกต้องหากต้องการยืนยันกฎนี้]")
        self.assertEqual(rule_ids(GOOD.replace("</body>", f"<p>{bad}</p></body>")), ["CR12"])
        self.assertEqual(rule_ids(GOOD.replace("</body>", "<p>ซึ่งต้องยืนยันมาตราอีกครั้ง</p></body>")), ["CR12"])
        for fine in ("[ต้องยืนยันมาตรา]", "[ต้องยืนยันมาตรา: ผลของนิติกรรม]", "[ ต้องยืนยันมาตรา]",
                     "[ต้องยืนยันมาตรา — ตรวจสอบตัวเลขกับตัวบท]"):
            self.assertEqual(rule_ids(GOOD.replace("</body>", f"<p>{fine}</p></body>")), [], fine)
        # a bracketed free-form hedge is not the standard flag (Codex review of PR #80, round 32)
        for bad in ("[ต้องยืนยันมาตราที่ถูกต้อง]", "[ต้องยืนยันมาตราอีกครั้ง]"):
            self.assertEqual(rule_ids(GOOD.replace("</body>", f"<p>{bad}</p></body>")), ["CR12"], bad)

    def test_w12_free_form_english_hedge_is_reported(self) -> None:
        for bad in ("License (governing CCC provisions to be confirmed)", "S-Curve industries (number to be verified)",
                    "the section number is still to be verified"):
            page = GOOD.replace("</body>", f"<p>{bad}</p></body>")
            self.assertEqual(rule_ids(page), [], bad)
            self.assertEqual([rule for rule, _ in rules.check_warnings(page)], ["W12"], bad)
        fine = GOOD.replace("</body>", "<p>Act B.E. 2561 [unconfirmed — paragraph to be verified against the official "
                                       "text] and [must verify section number]</p></body>")
        self.assertEqual(rules.check_warnings(fine), [])

    def test_cr13_invented_company_names(self) -> None:
        # TPL-06: names that read like real companies
        for bad in ("บริษัท ก่อสร้างมั่นคง จำกัด", "บริษัท ก่อสร้างมั่นคง จำกัดฯ", "บริษัท โซลาร์ เพาเวอร์ จำกัด", "ในบริษัท โรงพยาบาลมิตรภาพการแพทย์ จำกัด ซึ่ง",
                    "บริษัท Startup จำกัด มีทุน", "<strong>บริษัท ก่อสร้าง จำกัด</strong>",
                    # names of more than three words (Codex review of PR #80)
                    "บริษัท ไทย โซลาร์ กรีน เพาเวอร์ จำกัด", "บริษัท สยาม ดิจิทัล เทค โซลูชั่นส์ แอนด์ เซอร์วิส จำกัด",
                    # a trading name that starts with ผู้ is not a party role (Codex review of PR #80, round 35)
                    "บริษัท ผู้ชนะ จำกัด", "บริษัท ผู้มั่งคั่ง จำกัด",
                    # a role is a placeholder only as the whole name (Codex review of PR #80, round 36)
                    "บริษัท รุ่งเรือง ผู้รับเหมา จำกัด", "บริษัท สยาม มหาชน จำกัด"):
            self.assertEqual(rule_ids(GOOD.replace("</body>", f"<p>{bad}</p></body>")), ["CR13"], bad)
        for fine in ("บริษัท A จำกัด (ผู้รับเหมาก่อสร้าง)", "บริษัท B จำกัด", "ห้างหุ้นส่วนจำกัด D แปรสภาพเป็นบริษัท D จำกัด",
                     "บริษัท ก จำกัด", "บริษัท เอบีซี จำกัด", "บริษัท โลจิสติกส์ เอ จำกัด", "บริษัท _________________ จำกัด",
                     "บริษัท ผู้ว่าจ้าง จำกัด", "บริษัท ผู้ให้บริการ จำกัด", "บริษัท ผู้รับเหมาก่อสร้าง จำกัด", "บริษัท มหาชน จำกัด", "บริษัทจำกัดและบริษัทมหาชนจำกัด",
                     "บริษัท จำกัด กับห้างหุ้นส่วน", "บริษัท Legal Advance Solution จำกัด",
                     "เอกชน / บริษัท มหาชน จำกัด", "ข้อเท็จจริงสมมติ: บริษัท A จำกัด"):
            self.assertEqual(rule_ids(GOOD.replace("</body>", f"<p>{fine}</p></body>")), [], fine)

    def test_cr14_script_tooltip_titles(self) -> None:
        # TPL-07: js/legal-links.js tooltip titles; regex patterns and comments are not titles
        script = ("// ปพพ. ม.291 comment\nvar defined = [\n"
                  "  { pattern: /มาตรา\\s*291|ม\\.?\\s*291/, url: '/a.html', title: 'LAS Share 09 — หนี้ร่วม vs หนี้ลำพัง (ม.291)' },\n"
                  "  { pattern: /^x$/, url: '/b.html', title: \"LAS Share 04 — อายุความ (ม.193)\" },\n"
                  "  { pattern: /^y$/, url: '/c.html', title: 'LAS Share 09 — หนี้ร่วมและหนี้ส่วนตัว (มาตรา 291)' }\n];")
        found = rules.check_script(script)
        self.assertEqual([rule for rule, _ in found], ["CR14", "CR14"])
        self.assertEqual(rules.check_script("title: 'LAS Share 01 — จ้างทำของกับจ้างแรงงาน (มาตรา 575)'"), [])
        self.assertEqual(len(rules.check_script("title: 'หนี้ลำพัง'")), 1)
        # assignments, setAttribute and concatenations are titles too (Codex review of PR #80, round 10)
        self.assertEqual(len(rules.check_script("a.title = 'ค่าชดเชย (ม.118)';")), 1)
        self.assertEqual(len(rules.check_script("el.setAttribute('title', \"A vs B\");")), 1)
        # whitespace before the call is still a call (Codex review of PR #80, round 19)
        self.assertEqual(len(rules.check_script("link.setAttribute ('title', 'ม.118');")), 1)
        self.assertEqual(len(rules.check_script("link.setAttribute\n  ('title', 'ม.118');")), 1)
        # a parenthesized value is still the title (Codex review of PR #80, round 20)
        self.assertEqual(len(rules.check_script("link.title = ('ม.118');")), 1)
        self.assertEqual(len(rules.check_script("link.setAttribute('TITLE', 'ม.118');")), 1)
        # a concatenation across lines is one title (Codex review of PR #80, round 22)
        self.assertEqual(len(rules.check_script("link.title = 'ม.' +\n  '118';")), 1)
        self.assertEqual(len(rules.check_script("link.title = 'A '\n  + 'vs B';")), 1)
        # a non-literal operand reads as a digit (Codex review of PR #80, round 24)
        self.assertEqual(len(rules.check_script("link.title = 'ม.' + section;")), 1)
        self.assertEqual(len(rules.check_script("link.setAttribute('title', 'ม.' + n);")), 1)
        self.assertEqual(len(rules.check_script("link.title = 'ส่วน ม.' + n + ' ของ';")), 1)
        self.assertEqual(len(rules.check_script("link.SetAttribute('title', 'ม.118');")), 1)  # any string, round 25
        self.assertEqual(len(rules.check_script("link.setAttribute('title', ('A vs B'));")), 1)
        self.assertEqual(len(rules.check_script("a.title = 'คำพิพากษา ' + n + ' ม.5';")), 1)
        self.assertEqual(rules.check_script("a.title = 'คำพิพากษาศาลฎีกาที่ ' + dm[1] + '/' + dm[2] + ' — Kelomn';"), [])
        # since round 25 every string of a site script is read, whatever form uses it (Codex review of PR #80)
        self.assertEqual(len(rules.check_script("if (a.title === 'ม.1') {}")), 1)
        # bracket assignments are titles; comments are not, and a URL is not a comment (Codex review of PR #80, round 11)
        self.assertEqual(len(rules.check_script("link['title'] = 'ค่าชดเชย (ม.118)';")), 1)
        self.assertEqual(len(rules.check_script('link["title"]="A vs B";')), 1)
        self.assertEqual(rules.check_script("// title: 'foo vs bar'\n/* a.title = 'x vs y' */"), [])
        self.assertEqual(len(rules.check_script("{ url: 'https://x.y/z', title: 'ม.5' }")), 1)
        # an interpolated template literal is checked on its static text (Codex review of PR #80, round 12)
        self.assertEqual(len(rules.check_script("link.title = `ค่าชดเชย ${section} (ม.118)`;")), 1)
        self.assertEqual(rules.check_script("link.title = `คำพิพากษาศาลฎีกาที่ ${n}/${y}`;"), [])
        # an expression that completes the abbreviation is caught (Codex review of PR #80, round 15)
        self.assertEqual(len(rules.check_script("link.title = `ม.${section}`;")), 1)
        self.assertEqual(len(rules.check_script("link.title = `ม.${format({section: 118})}`;")), 1)
        # escapes are read as the browser renders them (Codex review of PR #80, round 16)
        for escaped in ("a.title = 'ม.\\x31';", "a.title = 'ม.\\u0031';", "a.title = `ม.\\u{31}`;", "a.title = 'A \\x76s B';"):
            self.assertEqual(len(rules.check_script(escaped)), 1, escaped)
        self.assertEqual(rules.check_script("a.title = 'it\\'s fine';"), [])
        # a quoted key is a title property too (Codex review of PR #80, round 13)
        self.assertEqual(len(rules.check_script('{"title": "ค่าชดเชย (ม.118)"}')), 1)
        self.assertEqual(len(rules.check_script("{'title': 'A vs B'}")), 1)
        # a variable or a destructuring default named title is not a tooltip (Codex review of PR #80, round 14)
        self.assertEqual(len(rules.check_script("const title = 'A vs B'; function f({title = 'A vs B'}) {}")), 2)
        # a conditional branch is a string too (round 25); regex literals and comments are not
        self.assertEqual(len(rules.check_script("link.title = thai ? 'ม.118' : 'Section 118';")), 1)
        # a line continuation inside a literal (round 26)
        self.assertEqual(len(rules.check_script("link.title = 'A vs\\\n B';")), 1)
        # a nested template literal is read too (round 27)
        self.assertEqual(len(rules.check_script("link.title = `${prefix} ${`ม.118`}`;")), 1)
        # "vs" followed by punctuation, but not inside a word (Codex review of PR #80, round 32)
        for bad in ("t = 'Joint (vs.) Several';", "t = 'A vs/B';", "t = 'A vs.';"):
            self.assertEqual(len(rules.check_script(bad)), 1, bad)
        self.assertEqual(rules.check_script("t = 'canvas versus vsync';"), [])
        self.assertEqual(rules.check_script("link.title = `${prefix} ${`มาตรา 118`}`;"), [])
        # a parenthesized operand, and a regex literal is not a string (Codex review of PR #80, round 28)
        self.assertEqual(len(rules.check_script("link.title = 'ม.' + (100 + 18);")), 1)
        self.assertEqual(rules.check_script('const r = /"A vs B"/; const s = a / b / c;'), [])
        self.assertEqual(rules.check_script("x = { pattern: /'ม.1'/i, url: '/a' };"), [])
        self.assertEqual(len(rules.check_script("y = a / 2; t = 'ม.' + n;")), 1)
        self.assertEqual(rules.check_script("var p = /มาตรา\\s*291|ม\\.?\\s*291/; // ม.291"), [])
        self.assertEqual(len(rules.check_script("a . title = 'A vs B';")), 1)
        with tempfile.TemporaryDirectory() as tmp:
            root = make_site(Path(tmp), {"articles/good.html": GOOD, "js/legal-links.js": script})
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                status = rules.main(["--root", str(root)])
            self.assertEqual(status, 1)
            self.assertIn("[CR14] js/legal-links.js", out.getvalue())
            self.assertNotIn("articles/good.html", out.getvalue())

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

    def test_named_untracked_article_gets_the_article_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_site(Path(tmp), {"articles/good.html": GOOD})
            # written after make_site's "git add", so it is not in the tracked-file scope
            (root / "articles" / "new.html").write_text(GOOD.replace("ข้อสงวนสิทธิ์", "ข้อความ").replace("disclaimer", "note"),
                                                       encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                status = rules.main(["--root", str(root), "articles/new.html"])
            self.assertEqual(status, 1)
            self.assertIn("[CR1] articles/new.html", out.getvalue())

    def test_missing_register_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_site(Path(tmp), {"articles/good.html": GOOD})
            (root / "scripts" / "legal-kb" / "supreme-court-verified.json").unlink()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(rules.main(["--root", str(root)]), 3)


COMPLETE = """<html><head><style>.practice-note{} .faq-item{} .quick-answer{}</style></head><body>
<div class="quick-answer"><strong>คำตอบโดยย่อ</strong> ...</div>
<table><tr><td>x</td></tr></table>
<div class="practice-note tip"><span class="pn-label">LAS Practice Note</span></div>
<h2 class="section-heading">ข้อต่อสู้ของผู้ขายกับผู้ซื้อ Devil's Advocate</h2>
<h2>คำถามที่พบบ่อย</h2><div class="faq-item"><div class="faq-q">Q1</div></div>
<div class="ref-section"><h2>แหล่งอ้างอิงทางกฎหมาย</h2></div>
<div class="disclaimer">ข้อสงวนสิทธิ์</div>
</body></html>"""


class TemplateStructureTests(unittest.TestCase):
    def test_complete_page_has_every_marker(self) -> None:
        self.assertEqual(template.missing_markers(COMPLETE), [])

    def test_each_missing_marker_is_reported(self) -> None:
        cuts = {
            "quick-answer": ('<div class="quick-answer"><strong>คำตอบโดยย่อ</strong> ...</div>', ""),
            "table": ("<table><tr><td>x</td></tr></table>", ""),
            "practice-note": ('<div class="practice-note tip"><span class="pn-label">LAS Practice Note</span></div>', ""),
            "counterargument": ("<h2 class=\"section-heading\">ข้อต่อสู้ของผู้ขายกับผู้ซื้อ Devil's Advocate</h2>", ""),
            "faq": ('<h2>คำถามที่พบบ่อย</h2><div class="faq-item"><div class="faq-q">Q1</div></div>', ""),
            "ref-section": ('<div class="ref-section"><h2>แหล่งอ้างอิงทางกฎหมาย</h2></div>', ""),
            "disclaimer": ('<div class="disclaimer">ข้อสงวนสิทธิ์</div>', ""),
        }
        for marker, (old, new) in cuts.items():
            self.assertIn(old, COMPLETE, marker)
            self.assertEqual(template.missing_markers(COMPLETE.replace(old, new)), [marker], marker)

    def test_locked_order(self) -> None:
        # Codex review of PR #80: every marker present but in the wrong order must fail
        self.assertEqual(template.order_problems(COMPLETE), [])
        quick = '<div class="quick-answer"><strong>คำตอบโดยย่อ</strong> ...</div>'
        refs = '<div class="ref-section"><h2>แหล่งอ้างอิงทางกฎหมาย</h2></div>'
        swapped = COMPLETE.replace(quick, "@@Q@@").replace(refs, quick).replace("@@Q@@", refs)
        self.assertEqual(template.missing_markers(swapped), [])
        self.assertIn("out of order: ref-section before quick-answer", template.order_problems(swapped))
        with tempfile.TemporaryDirectory() as tmp:
            root = make_site(Path(tmp), {"articles/swapped.html": swapped, "articles/full.html": COMPLETE})
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                status = template.main(["--root", str(root), "--strict", "articles/swapped.html", "articles/full.html"])
            self.assertEqual(status, 1)
            self.assertIn("[FAIL] articles/swapped.html: out of order", out.getvalue())
            self.assertNotIn("full.html", out.getvalue().split("[TEMPLATE]")[0])
        # a label split across inline tags is found and ordered like any other marker (Codex review of PR #80)
        split = COMPLETE.replace(quick, "").replace('<div class="disclaimer">ข้อสงวนสิทธิ์</div>',
                                                    '<div class="disclaimer">ข้อสงวนสิทธิ์</div><div>Quick <em>Answer</em></div>')
        self.assertEqual(template.missing_markers(split), [])
        self.assertIn("out of order: disclaimer before quick-answer", template.order_problems(split))
        # two labels in one text node keep their own offsets (Codex review of PR #80)
        pn = '<div class="practice-note tip"><span class="pn-label">LAS Practice Note</span></div>'
        one_node = COMPLETE.replace(quick, "").replace(pn, "<p>LAS Practice Note &amp; Quick Answer</p>")
        self.assertEqual(template.missing_markers(one_node), [])
        self.assertIn("out of order: practice-note before quick-answer", template.order_problems(one_node))
        # several section classes on one element are not several sections (Codex review of PR #80)
        wrapper = ('<html><body><h1>T</h1><div class="quick-answer practice-note counterargument faq ref-section disclaimer">'
                   "x</div><table><tr><td>x</td></tr></table></body></html>")
        self.assertEqual(template.missing_markers(wrapper), [])
        self.assertTrue(any(p.startswith("one element for two sections") for p in template.order_problems(wrapper)))
        # the same holds when the closing sections pick a later hit of their own (Codex review of PR #80, round 6)
        closing = COMPLETE.replace('<div class="ref-section"><h2>แหล่งอ้างอิงทางกฎหมาย</h2></div>\n<div class="disclaimer">ข้อสงวนสิทธิ์</div>',
                                   '<div class="ref-section disclaimer"><h2>References</h2><p>Disclaimer: not legal advice</p></div>')
        self.assertNotEqual(closing, COMPLETE)
        self.assertEqual(template.missing_markers(closing), [])
        self.assertIn("one element for two sections: ref-section and disclaimer", template.order_problems(closing))
        # a label in running text belongs to its element too (Codex review of PR #80, round 7)
        labels = COMPLETE.replace(quick, '<div class="quick-answer">Quick Answer and Practice Note</div>').replace(pn, "")
        self.assertEqual(template.missing_markers(labels), [])
        self.assertIn("one element for two sections: quick-answer and practice-note", template.order_problems(labels))
        self.assertEqual(template.order_problems(COMPLETE.replace(pn, "<p>LAS Practice Note</p>")), [])
        # two labels in one plain heading are not a shared section ("Practice Note: … Disclaimer" names a clause)
        clause = COMPLETE.replace(pn, pn + '<h2 class="section-heading">LAS Practice Note: Human-in-the-Loop Disclaimer</h2>')
        self.assertEqual(template.order_problems(clause), [])
        # two labels alone in one plain element are one section (Codex review of PR #80, round 8), but not in a link
        plain = COMPLETE.replace(quick, "<div>Quick Answer Practice Note</div>").replace(pn, "")
        self.assertIn("one element for two sections: quick-answer and practice-note", template.order_problems(plain))
        toc = COMPLETE.replace(pn, pn + '<ul><li><a href="#s7">LAS Practice Note: Human-in-the-Loop Disclaimer</a></li></ul>')
        self.assertEqual(template.order_problems(toc), [])
        # a label in a link names a section and is not one (Codex review of PR #80, round 9)
        nav = COMPLETE.replace(pn, '<nav><a href="#qa">Quick Answer</a> <a href="#pn"><em>Practice</em> Note</a></nav>')
        self.assertEqual(template.missing_markers(nav), ["practice-note"])
        # without the link, a sub-heading that names a table of claims and defences does not move the counterargument
        ledger = COMPLETE.replace(quick, quick + '<h3 class="sub-heading">Claim Ledger (ตารางวิเคราะห์มูลกรณีและข้อต่อสู้ทางกฎหมาย)</h3>')
        self.assertEqual(template.order_problems(ledger), [])
        # a label nested anywhere inside another section is not a section of its own (Codex review of PR #80, round 10)
        nested = COMPLETE.replace(quick, '<div class="quick-answer"><b>Quick Answer</b> <span>Practice Note</span></div>').replace(pn, "")
        self.assertIn("one element for two sections: quick-answer and practice-note", template.order_problems(nested))
        # but a section element nested in another keeps its own label (div.disclaimer inside div.ref-section)
        inner = COMPLETE.replace('<div class="ref-section"><h2>แหล่งอ้างอิงทางกฎหมาย</h2></div>\n<div class="disclaimer">ข้อสงวนสิทธิ์</div>',
                                 '<div class="ref-section"><h2>แหล่งอ้างอิงทางกฎหมาย</h2><div class="disclaimer"><strong>ข้อสงวนสิทธิ์:</strong> x</div></div>')
        self.assertNotEqual(inner, COMPLETE)
        self.assertEqual(template.order_problems(inner), [])
        # inline formatting cannot make two sections of one block (Codex review of PR #80, round 11)
        inline = COMPLETE.replace(quick, "<p><span>Quick Answer</span> <span>Practice Note</span></p>").replace(pn, "")
        self.assertIn("one element for two sections: quick-answer and practice-note", template.order_problems(inline))
        # data-class is not a class, and inert <template> contents are not rendered (Codex review of PR #80, round 13)
        self.assertIn("practice-note", template.missing_markers(COMPLETE.replace(pn, '<div data-class="practice-note">x</div>')))
        self.assertEqual(template.missing_markers(COMPLETE.replace(pn, '<template><div class="practice-note">x</div></template>')),
                         ["practice-note"])
        nested_tpl = COMPLETE.replace(pn, '<template><template></template><div class="practice-note">x</div></template>')
        self.assertEqual(template.missing_markers(nested_tpl), ["practice-note"])
        self.assertEqual(template.missing_markers(COMPLETE.replace(pn, '<div hidden><div class="practice-note">x</div></div>')),
                         ["practice-note"])
        self.assertEqual(template.missing_markers(COMPLETE.replace(
            pn, '<div style="display:none"><div class="practice-note">x</div></div>')), ["practice-note"])
        # <noscript> content is not shown to visitors with scripting on (Codex review of PR #80, round 29)
        self.assertEqual(template.missing_markers(COMPLETE.replace(pn, '<noscript><div class="practice-note">x</div></noscript>')),
                         ["practice-note"])
        # a refresh tag in a comment does not make the page a redirect stub that strict mode skips (round 20)
        stub = COMPLETE.replace("<body>", '<body><!-- <meta http-equiv="refresh" content="0;url=/x"> -->').replace(pn, "")
        with tempfile.TemporaryDirectory() as tmp:
            root = make_site(Path(tmp), {"articles/stub.html": stub})
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(template.main(["--root", str(root), "--strict", "articles/stub.html"]), 1)
        # a real refresh tag with a quoted ">" in another attribute is a redirect (Codex review of PR #80, round 33)
        self.assertTrue(pages.is_redirect_stub('<meta data-note="1 > 0" http-equiv="refresh" content="0; url=/new">'))
        self.assertFalse(pages.is_redirect_stub('<meta data-note="http-equiv=refresh" name="x">'))
        # a refresh with no destination only reloads the page: the article is still checked (round 41)
        for reload in ('<meta http-equiv="refresh" content="30">', '<meta http-equiv="refresh">',
                       '<meta http-equiv="refresh" content="0; url=">'):
            self.assertFalse(pages.is_redirect_stub(reload), reload)
        self.assertTrue(pages.is_redirect_stub('<meta http-equiv="refresh" content="5, /b.html">'))
        # markup inside a <textarea> is text, not elements (round 33)
        self.assertEqual(template.missing_markers(COMPLETE.replace(pn, '<textarea><div class="practice-note">x</div></textarea>'),
                                                  labels=False), ["practice-note"])
        # nor does one inside a script string (round 30)
        scripted = COMPLETE.replace("<body>", """<body><script>const s = '<meta http-equiv="refresh" content="0">';</script>""").replace(pn, "")
        with tempfile.TemporaryDirectory() as tmp:
            root = make_site(Path(tmp), {"articles/scripted.html": scripted})
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(template.main(["--root", str(root), "--strict", "articles/scripted.html"]), 1)
        # inline markup joins Thai text as the browser renders it (Codex review of PR #80, round 17)
        thai = COMPLETE.replace(quick, "<h2><strong>คำตอบ</strong>โดยย่อ</h2>")
        self.assertEqual(template.missing_markers(thai), [])
        self.assertEqual(template.order_problems(thai), [])
        heading = COMPLETE.replace('<h2>คำถามที่พบบ่อย</h2><div class="faq-item"><div class="faq-q">Q1</div></div>',
                                   "<h2><em>คำถาม</em>ที่พบบ่อย</h2>")
        self.assertEqual(template.missing_markers(heading), [])
        # on a --strict page a label in prose is not a section: classes and headings only (Codex review of PR #80,
        # round 18); the legacy report still accepts it
        prose = COMPLETE.replace(pn, "<p>For details, read the Practice Note below.</p>")
        self.assertEqual(template.missing_markers(prose), [])
        self.assertEqual(template.missing_markers(prose, labels=False), ["practice-note"])
        self.assertEqual(template.missing_markers(COMPLETE, labels=False), [])
        with tempfile.TemporaryDirectory() as tmp:
            root = make_site(Path(tmp), {"articles/prose.html": prose})
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(template.main(["--root", str(root), "--strict", "articles/prose.html"]), 1)
                self.assertEqual(template.main(["--root", str(root), "articles/prose.html"]), 0)
        # unquoted classes count; Quick Answer and Disclaimer headings count when they open with the label
        # (Codex review of PR #80, round 23)
        unquoted = COMPLETE.replace('<div class="quick-answer">', "<div class=quick-answer>").replace(
            '<div class="disclaimer">', "<div class=disclaimer>")
        self.assertEqual(template.missing_markers(unquoted, labels=False), [])
        headings = COMPLETE.replace(quick, "<h2>Quick Answer</h2><p>x</p>").replace(
            '<div class="disclaimer">ข้อสงวนสิทธิ์</div>', "<h2>ข้อสงวนสิทธิ์</h2><p>x</p>")
        self.assertEqual(template.missing_markers(headings, labels=False), [])
        self.assertEqual(template.order_problems(headings, labels=False), [])
        # a ">" inside a heading's attribute does not end its start tag (round 26)
        fake = COMPLETE.replace(quick, '<h2 data-note=">Quick Answer">Nothing</h2>')
        self.assertIn("quick-answer", template.missing_markers(fake, labels=False))
        clause_head = COMPLETE.replace(pn, '<h2 class="section-heading">LAS Practice Note: Human-in-the-Loop Disclaimer</h2>')
        self.assertEqual(template.order_problems(clause_head, labels=False), [])
        # an end tag may carry whitespace before its ">" (round 36)
        spaced = "<html><body><h2>Quick Answer</h2 ><p>x</p></body></html>"
        self.assertNotIn("quick-answer", template.missing_markers(spaced, labels=False))
        # a class inside another attribute's value marks nothing (round 39)
        noted = ('<html><body>' + "".join(f'<div data-note="x class={c}">x</div>' for c in
                 ("quick-answer", "practice-note", "faq", "ref-section", "disclaimer")) + "</body></html>")
        self.assertEqual(template.missing_markers(noted, labels=False), template.missing_markers(
            "<html><body><p>text</p></body></html>", labels=False))
        titled = COMPLETE.replace('<div class="quick-answer">', '<div class="quick-answer" title="shown, not hidden">')
        self.assertEqual(template.missing_markers(titled, labels=False), [])
        # an <iframe> fallback body marks nothing (round 38)
        framed = ('<html><body><iframe src="x.html">' + "".join(f'<div class="{c}">x</div>' for c in
                  ("quick-answer", "practice-note", "faq", "ref-section", "disclaimer")) + "<table></table></iframe></body></html>")
        self.assertEqual(len(template.missing_markers(framed, labels=False)), len(template.missing_markers(
            "<html><body><p>text</p></body></html>", labels=False)))
        # only the <body> counts: classes and a table in <head> mark nothing (round 34)
        head_only = ('<html><head>' + "".join(f'<meta class="{c}">' for c in
                     ("quick-answer", "practice-note", "faq", "ref-section", "disclaimer"))
                     + '<table></table><!-- <body> --></head><body><p>text</p></body></html>')
        self.assertEqual(len(template.missing_markers(head_only, labels=False)), len(template.missing_markers(
            "<html><body><p>text</p></body></html>", labels=False)))
        self.assertTrue(template.missing_markers(head_only, labels=False))
        # a class name counts only at the start of a class token
        self.assertIn("faq", template.missing_markers(COMPLETE.replace(
            '<h2>คำถามที่พบบ่อย</h2><div class="faq-item"><div class="faq-q">Q1</div></div>', '<div class="no-faq">x</div>')))
        # a body heading that mentions อ้างอิง before the FAQ does not move the closing references section
        early = COMPLETE.replace(quick, quick + "<h3>ตารางสรุปมาตราที่อ้างอิง</h3>")
        self.assertEqual(template.order_problems(early), [])

    def test_css_comments_and_prose_do_not_count(self) -> None:
        # the inline CSS of every page names .practice-note and .faq-item; prose "อีกฝ่ายหนึ่ง" is not a section
        page = COMPLETE.replace('<div class="practice-note tip"><span class="pn-label">LAS Practice Note</span></div>',
                                "<!-- Practice Note --><p>คู่สัญญาอีกฝ่ายหนึ่ง</p>")
        page = page.replace("<h2 class=\"section-heading\">ข้อต่อสู้ของผู้ขายกับผู้ซื้อ Devil's Advocate</h2>", "")
        self.assertEqual(template.missing_markers(page), ["practice-note", "counterargument"])

    def test_report_only_unless_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = make_site(Path(tmp), {
                "articles/full.html": COMPLETE,
                "articles/legacy.html": "<p>old page</p>",
                "articles/stub.html": '<meta http-equiv="refresh" content="0;url=x">',
            })
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                status = template.main(["--root", str(root)])
            self.assertEqual(status, 0)
            self.assertIn("[REPORT] articles/legacy.html: missing quick-answer", out.getvalue())
            self.assertNotIn("full.html", out.getvalue())
            self.assertNotIn("stub.html", out.getvalue())
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                status = template.main(["--root", str(root), "--strict", "articles/legacy.html", "articles/full.html"])
            self.assertEqual(status, 1)
            self.assertIn("[FAIL] articles/legacy.html", out.getvalue())
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(template.main(["--root", str(root), "--strict", "articles/full.html"]), 0)
                self.assertEqual(template.main(["--root", str(root), "--strict", "articles/missing.html"]), 1)


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
