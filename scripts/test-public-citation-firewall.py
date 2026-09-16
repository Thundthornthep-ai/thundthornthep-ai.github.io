#!/usr/bin/env python3
"""Regression tests for the public citation firewall.

Proves Thai-numeral normalization, HTML-comment ignoring, slash-list splits,
statute-scoped registry keys, and fail-closed unmatched sections.
"""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "public_citation_firewall",
    Path(__file__).with_name("public-citation-firewall.py"),
)
firewall = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(firewall)


def write_kb(root: Path) -> Path:
    (root / "lpa.md").write_text(
        "statute: lpa\nOfficial source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 118\n",
        encoding="utf-8",
    )
    (root / "ccc.md").write_text(
        "statute: ccc\nOfficial source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 213\n- มาตรา 41/1\n",
        encoding="utf-8",
    )
    return root


class PrepareTextTests(unittest.TestCase):
    def test_thai_digits_normalize_to_arabic(self) -> None:
        self.assertEqual(firewall.prepare_text("มาตรา ๒๑๓ และ ๖๘๑/๑"), "มาตรา 213 และ 681/1")

    def test_html_comments_are_removed(self) -> None:
        text = "<!-- SECTION 1: Outline -->\n<p>ปพพ. มาตรา 222</p>"
        self.assertNotIn("SECTION 1", firewall.prepare_text(text))
        self.assertIn("มาตรา 222", firewall.prepare_text(text))

    def test_ampersand_entity_does_not_break_ccc_alias(self) -> None:
        self.assertIn("and", firewall.prepare_text("Civil &amp; Commercial Code"))

    def test_html_tags_and_mdash_become_separators(self) -> None:
        text = (
            "<strong>พระราชบัญญัติคุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562</strong> "
            "&mdash; มาตรา 37"
        )
        prepared = firewall.prepare_text(text)
        self.assertNotIn("<strong>", prepared)
        self.assertNotIn("</strong>", prepared)
        self.assertNotIn("&mdash;", prepared)
        self.assertIn("พระราชบัญญัติคุ้มครองข้อมูลส่วนบุคคล", prepared)
        self.assertIn("มาตรา 37", prepared)


class CitationExtractionTests(unittest.TestCase):
    def test_lawquote_thai_numeral_is_a_citation(self) -> None:
        html = '<div class="lawquote"><pre>มาตรา ๒๑๓  ถ้าลูกหนี้ละเลย</pre></div>'
        self.assertEqual(set(firewall.cited_sections(html)), {"213"})

    def test_outline_comment_is_not_a_citation(self) -> None:
        html = "<!-- SECTION 7: Tax Gross-Up -->\n<p>ไม่มีมาตรา</p>"
        self.assertEqual(firewall.cited_sections(html), [])

    def test_intervening_section_does_not_inherit_prior_statute(self) -> None:
        cites = firewall.extract_citations("ปพพ. มาตรา 577 + มาตรา 118")
        self.assertIn(("ccc", "577"), cites)
        self.assertIn((None, "118"), cites)

    def test_trailing_statute_binds_after_section_number(self) -> None:
        cites = firewall.extract_citations("ปพพ. มาตรา 577 + มาตรา 118 พ.ร.บ.คุ้มครองแรงงาน")
        self.assertIn(("ccc", "577"), cites)
        self.assertIn(("lpa", "118"), cites)

    def test_long_english_act_title_still_binds(self) -> None:
        cites = firewall.extract_citations(
            "Personal Data Protection Act B.E. 2562 (2019), Section 91"
        )
        self.assertEqual(cites, [("pdpa", "91")])

    def test_trailing_of_the_act_binds(self) -> None:
        cites = firewall.extract_citations("Section 118 of the Personal Data Protection Act")
        self.assertEqual(cites, [("pdpa", "118")])

    def test_thai_haeng_introducer_still_binds_lpa(self) -> None:
        cites = firewall.extract_citations("มาตรา 30 แห่งพระราชบัญญัติคุ้มครองแรงงาน")
        self.assertEqual(cites, [("lpa", "30")])

    def test_later_act_in_same_sentence_does_not_rebind(self) -> None:
        cites = firewall.extract_citations(
            "Foreign Business Act B.E. 2542 (1999), Section 36 and Section 37, "
            "simulated transactions under the Civil and Commercial Code Section 155"
        )
        self.assertIn(("fba", "36"), cites)
        self.assertIn(("fba", "37"), cites)
        self.assertIn(("ccc", "155"), cites)

    def test_coordinated_and_keeps_statute_scope(self) -> None:
        cites = firewall.extract_citations(
            "Foreign Business Act B.E. 2542 (1999), Section 36 and Section 37"
        )
        self.assertEqual(cites, [("fba", "36"), ("fba", "37")])

    def test_amendment_clause_still_binds_lpa(self) -> None:
        cites = firewall.extract_citations(
            "พระราชบัญญัติคุ้มครองแรงงาน พ.ศ. 2541 แก้ไขเพิ่มเติมโดย ฉบับที่ 9 พ.ศ. 2568 มาตรา 118"
        )
        self.assertEqual(cites, [("lpa", "118")])

    def test_contrast_clause_does_not_steal_hire_of_work_section(self) -> None:
        cites = firewall.extract_citations(
            "ลูกจ้างได้รับสิทธิตาม พ.ร.บ.คุ้มครองแรงงาน ส่วนจ้างทำของ (Hire of Work) ตามมาตรา 587"
        )
        self.assertEqual(cites, [(None, "587")])

    def test_negated_ucta_use_does_not_rebind_ccc_150(self) -> None:
        cites = firewall.extract_citations(
            "พระราชบัญญัติว่าด้วยข้อสัญญาที่ไม่เป็นธรรม พ.ศ. 2540 มาตรา 4 "
            "ไม่ใช่การนำมาตรา 150 มาใช้เป็นบทข้อสัญญาที่ไม่เป็นธรรม"
        )
        self.assertIn(("ucta", "4"), cites)
        self.assertIn((None, "150"), cites)

    def test_arabic_lecture_cite_still_counts(self) -> None:
        self.assertIn("222", firewall.cited_sections("ปพพ. มาตรา 222"))

    def test_slash_list_splits_into_two_sections(self) -> None:
        html = "FBA Sections 36 / 37 (พ.ร.บ.ประกอบธุรกิจของคนต่างด้าว พ.ศ. 2542 มาตรา 36/37)"
        self.assertEqual(set(firewall.cited_sections(html)), {"36", "37"})
        self.assertEqual(firewall.cited_sections("มาตรา 159/164"), ["159", "164"])

    def test_spaced_and_plural_slash_lists_are_citations(self) -> None:
        self.assertEqual(set(firewall.cited_sections("FBA มาตรา 36 / 37")), {"36", "37"})
        self.assertEqual(set(firewall.cited_sections("FBA Sections 36 / 37")), {"36", "37"})
        self.assertEqual(firewall.cited_sections("Sections 102, 105"), [])

    def test_inserted_section_stays_compound(self) -> None:
        self.assertEqual(firewall.cited_sections("มาตรา 41/1"), ["41/1"])
        self.assertEqual(firewall.cited_sections("มาตรา 193/30"), ["193/30"])

    def test_securities_89_inserts_do_not_split_into_bare_numbers(self) -> None:
        """SEA 89/* stays compound only when bound (or 89/8, whose insert side is < 10)."""
        self.assertEqual(firewall.cited_sections("มาตรา ๘๙/๘"), ["89/8"])
        self.assertEqual(firewall.cited_sections("มาตรา ๘๙/๑๘"), ["89", "18"])
        self.assertEqual(
            firewall.extract_citations(
                "พระราชบัญญัติหลักทรัพย์และตลาดหลักทรัพย์ พ.ศ. ๒๕๓๕ มาตรา ๘๙/๒๓"
            ),
            [("securities", "89/23")],
        )
        self.assertEqual(
            firewall.extract_citations(
                "พระราชบัญญัติหลักทรัพย์และตลาดหลักทรัพย์ พ.ศ. ๒๕๓๕ มาตรา ๘๙/๑๘"
            ),
            [("securities", "89/18")],
        )
        self.assertNotIn("18", firewall.cited_sections(
            "พระราชบัญญัติหลักทรัพย์และตลาดหลักทรัพย์ พ.ศ. ๒๕๓๕ มาตรา ๘๙/๑๘"
        ))
        self.assertNotIn("23", firewall.cited_sections(
            "พระราชบัญญัติหลักทรัพย์และตลาดหลักทรัพย์ พ.ศ. ๒๕๓๕ มาตรา ๘๙/๒๓"
        ))
        self.assertNotIn("89", firewall.cited_sections(
            "พระราชบัญญัติหลักทรัพย์และตลาดหลักทรัพย์ พ.ศ. ๒๕๓๕ มาตรา ๘๙/๒๓"
        ))

    def test_upsize_07_sea_box_phrases(self) -> None:
        """Phrases from articles/las-upsize-07.html official boxes."""
        cites = firewall.extract_citations(
            "พระราชบัญญัติหลักทรัพย์และตลาดหลักทรัพย์ พ.ศ. ๒๕๓๕ มาตรา ๒๖๘"
        )
        self.assertEqual(cites, [("securities", "268")])
        box_33 = (
            "พระราชบัญญัติหลักทรัพย์และตลาดหลักทรัพย์ พ.ศ. ๒๕๓๕ มาตรา ๓๓ "
            "มาตรา ๓๓ ห้ามมิให้บริษัทเสนอขายหลักทรัพย์ที่ออกใหม่ "
            "(๑) เป็นการเสนอขายหลักทรัพย์ที่เข้าลักษณะตามมาตรา ๖๓"
        )
        cites = firewall.extract_citations(box_33)
        self.assertIn(("securities", "33"), cites)
        self.assertIn((None, "63"), cites)
        self.assertNotIn("18", firewall.cited_sections("กระบวนการ IPO ใช้เวลา 18–36 เดือน"))

    def test_upsize_08_sea_box_phrases(self) -> None:
        """Phrases from articles/las-upsize-08.html official boxes."""
        self.assertEqual(
            firewall.extract_citations(
                "พระราชบัญญัติหลักทรัพย์และตลาดหลักทรัพย์ พ.ศ. ๒๕๓๕ มาตรา ๕๖"
            ),
            [("securities", "56")],
        )
        body = (
            "พระราชบัญญัติหลักทรัพย์และตลาดหลักทรัพย์ พ.ศ. ๒๕๓๕ มาตรา ๘๙/๒๓ "
            "ให้นำความในมาตรา ๘๙/๘ วรรคสอง มาตรา ๘๙/๑๐ มาตรา ๘๙/๑๑ (๒) "
            "และ (๓) และมาตรา ๘๙/๑๘ มาใช้บังคับ โดยอนุโลม"
        )
        self.assertIn("89/23", firewall.cited_sections(body))
        self.assertIn("89/8", firewall.cited_sections(body))
        self.assertNotIn("89/10", firewall.cited_sections(body))
        self.assertNotIn("89/18", firewall.cited_sections(body))


class RegistryAndGateTests(unittest.TestCase):
    def test_thai_article_matches_arabic_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            registry = firewall.load_registry(kb)
            missing = firewall.missing_citations(firewall.extract_citations("ปพพ. มาตรา ๒๑๓"), registry)
            self.assertEqual(missing, [])

    def test_named_act_absent_from_alias_map_is_unrecognized(self) -> None:
        cites = firewall.extract_citations("Widget Licensing Act B.E. 2560, Section 3")
        self.assertEqual(cites, [(firewall.UNRECOGNIZED, "3")])

    def test_one_word_and_hyphenated_act_titles_are_unrecognized(self) -> None:
        self.assertEqual(
            firewall.extract_citations("Patent Act B.E. 2522, Section 3"),
            [(firewall.UNRECOGNIZED, "3")],
        )
        self.assertEqual(
            firewall.extract_citations("Section 3 of the Patent Act"),
            [(firewall.UNRECOGNIZED, "3")],
        )
        self.assertEqual(
            firewall.extract_citations("Anti-Smuggling Act B.E. 2567, Section 4"),
            [(firewall.UNRECOGNIZED, "4")],
        )

    def test_sentence_initial_the_patent_act_is_unrecognized(self) -> None:
        self.assertEqual(
            firewall.extract_citations("The Patent Act, Section 3"),
            [(firewall.UNRECOGNIZED, "3")],
        )
        self.assertEqual(
            firewall.extract_citations("The Act, Section 3"),
            [(None, "3")],
        )

    def test_named_unknown_act_does_not_pass_on_another_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            registry = firewall.load_registry(kb)
            cites = firewall.extract_citations("Trade Secrets Act B.E. 2545 (2002), Section 3")
            self.assertEqual(cites, [("tradesecrets", "3")])
            missing = firewall.missing_citations(cites, registry)
            self.assertEqual(missing, ["tradesecrets:3"])

    def test_sibling_footer_pills_do_not_rebind_next_statute(self) -> None:
        html = (
            "<span>มาตรา 118</span>"
            "<span>พ.ร.บ.ความลับทางการค้า พ.ศ. 2545</span>"
        )
        self.assertEqual(firewall.extract_citations(html), [(None, "118")])

    def test_adjacent_statute_and_section_spans_keep_binding(self) -> None:
        html = "<span>ประมวลรัษฎากร</span><span>มาตรา 118</span>"
        self.assertEqual(firewall.extract_citations(html), [("revenue", "118")])

    def test_footer_chain_cuts_unrelated_statute_after_section_pills(self) -> None:
        html = (
            "<span>พ.ร.บ.หลักทรัพย์และตลาดหลักทรัพย์ พ.ศ. 2535</span>"
            "<span>มาตรา 65</span>"
            "<span>มาตรา 83</span>"
            "<span>พ.ร.บ.บริษัทมหาชนจำกัด พ.ศ. 2535</span>"
        )
        cites = firewall.extract_citations(html)
        self.assertIn(("securities", "65"), cites)
        self.assertIn((None, "83"), cites)
        self.assertNotIn(("plc", "83"), cites)

    def test_adjacent_revenue_118_does_not_pass_on_lpa_118(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            registry = firewall.load_registry(kb)
            html = "<span>ประมวลรัษฎากร</span><span>มาตรา 118</span>"
            cites = firewall.extract_citations(html)
            self.assertEqual(cites, [("revenue", "118")])
            self.assertEqual(firewall.missing_citations(cites, registry), ["revenue:118"])

    def test_plural_section_dash_range_is_detected(self) -> None:
        criminal = [("criminal", str(n)) for n in range(147, 167)]
        self.assertEqual(firewall.extract_citations("Criminal Code Sections 147–166"), criminal)
        self.assertEqual(firewall.extract_citations("Criminal Code Sections 147—166"), criminal)
        self.assertEqual(
            firewall.extract_citations("PDPA Sections 28-29"),
            [("pdpa", "28"), ("pdpa", "29")],
        )
        self.assertEqual(firewall.cited_sections("กระบวนการ IPO ใช้เวลา 18–36 เดือน"), [])
        self.assertEqual(firewall.cited_sections("มาตรา 32–65"), ["32"])
        self.assertEqual(firewall.cited_sections("Sections 102, 105"), [])

    def test_criminal_code_range_does_not_pass_on_ccc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp)
            (kb / "ccc.md").write_text(
                "statute: ccc\nOfficial source: https://www.ocs.go.th/searchlaw-law\n"
                "- มาตรา 147\n- มาตรา 166\n",
                encoding="utf-8",
            )
            registry = firewall.load_registry(kb)
            cites = firewall.extract_citations("Criminal Code Sections 147–166")
            self.assertEqual(cites, [("criminal", str(n)) for n in range(147, 167)])
            self.assertEqual(
                firewall.missing_citations(cites, registry),
                [f"criminal:{n}" for n in range(147, 167)],
            )

    def test_unknown_act_stays_unrecognized_near_known_alias(self) -> None:
        cites = firewall.extract_citations(
            "Unlike the Civil Code, the Patent Act, Section 3 applies"
        )
        self.assertEqual(cites, [(firewall.UNRECOGNIZED, "3")])
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            (Path(tmp) / "ccc.md").write_text(
                "statute: ccc\nOfficial source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 3\n",
                encoding="utf-8",
            )
            registry = firewall.load_registry(kb)
            self.assertEqual(firewall.missing_citations(cites, registry), ["unrecognized:3"])

    def test_securities_scope_does_not_carry_across_unrelated_cites(self) -> None:
        cites = firewall.extract_citations(
            "Securities and Exchange Act Section 89/8. Other provisions: Sections 89 / 18"
        )
        self.assertEqual(cites, [("securities", "89/8"), (None, "89"), (None, "18")])

    def test_multi_item_slash_list_splits_every_component(self) -> None:
        cites = firewall.extract_citations("PDPA Sections 28 / 29 / 37")
        self.assertEqual(cites, [("pdpa", "28"), ("pdpa", "29"), ("pdpa", "37")])
        self.assertNotIn(("pdpa", "28/29/37"), cites)

    def test_thai_criminal_code_is_not_bare(self) -> None:
        self.assertEqual(
            firewall.extract_citations("ประมวลกฎหมายอาญา มาตรา 144"),
            [("criminal", "144")],
        )
        self.assertEqual(
            firewall.extract_citations("ประมวลกฎหมายอาญา มาตรา 149"),
            [("criminal", "149")],
        )
        self.assertEqual(
            firewall.extract_citations("ประมวลกฎหมายอาญา มาตรา 95"),
            [("criminal", "95")],
        )

    def test_thai_criminal_code_does_not_pass_on_ccc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp)
            (kb / "ccc.md").write_text(
                "statute: ccc\nOfficial source: https://www.ocs.go.th/searchlaw-law\n"
                "- มาตรา 95\n- มาตรา 144\n- มาตรา 149\n",
                encoding="utf-8",
            )
            registry = firewall.load_registry(kb)
            for phrase, section in (
                ("ประมวลกฎหมายอาญา มาตรา 144", "144"),
                ("ประมวลกฎหมายอาญา มาตรา 149", "149"),
                ("ประมวลกฎหมายอาญา มาตรา 95", "95"),
            ):
                cites = firewall.extract_citations(phrase)
                self.assertEqual(cites, [("criminal", section)], phrase)
                self.assertEqual(
                    firewall.missing_citations(cites, registry),
                    [f"criminal:{section}"],
                    phrase,
                )

    def test_nacc_organic_act_prefix_binds(self) -> None:
        self.assertEqual(
            firewall.extract_citations(
                "พระราชบัญญัติประกอบรัฐธรรมนูญว่าด้วยการป้องกันและปราบปรามการทุจริต "
                "พ.ศ. 2561 มาตรา 36"
            ),
            [("nacc", "36")],
        )
        self.assertEqual(
            firewall.extract_citations(
                "พระราชบัญญัติประกอบรัฐธรรมนูญว่าด้วยการป้องกันและปราบปรามการทุจริต "
                "พ.ศ. 2561 มาตรา 103"
            ),
            [("nacc", "103")],
        )
        self.assertEqual(
            firewall.extract_citations(
                "พระราชบัญญัติประกอบรัฐธรรมนูญว่าด้วยการป้องกันและปราบปรามการทุจริต "
                "พ.ศ. 2561 มาตรา 128"
            ),
            [("nacc", "128")],
        )

    def test_nacc_organic_act_trailing_of_form_is_not_unrecognized(self) -> None:
        cites = firewall.extract_citations(
            "มาตรา 36 ของพระราชบัญญัติประกอบรัฐธรรมนูญว่าด้วยการป้องกันและปราบปรามการทุจริต "
            "พ.ศ. 2561"
        )
        self.assertEqual(len(cites), 1)
        self.assertEqual(cites[0][1], "36")
        self.assertNotEqual(cites[0][0], firewall.UNRECOGNIZED)

    def test_constitution_section_is_named_not_bare(self) -> None:
        self.assertEqual(
            firewall.extract_citations(
                "Constitution of the Kingdom of Thailand B.E. 2560 (2017), Section 234(3)"
            ),
            [("constitution", "234")],
        )
        self.assertEqual(
            firewall.extract_citations("Constitution B.E. 2560 — Section 234(3)"),
            [("constitution", "234")],
        )
        self.assertEqual(
            firewall.extract_citations(
                "รัฐธรรมนูญแห่งราชอาณาจักรไทย พุทธศักราช 2560 มาตรา 234"
            ),
            [("constitution", "234")],
        )
        self.assertEqual(
            firewall.extract_citations("Section 234 of the Constitution"),
            [("constitution", "234")],
        )

    def test_constitution_234_does_not_pass_on_ccc_234(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            (Path(tmp) / "ccc.md").write_text(
                "statute: ccc\nOfficial source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 234\n",
                encoding="utf-8",
            )
            registry = firewall.load_registry(kb)
            cites = firewall.extract_citations(
                "Constitution of the Kingdom of Thailand B.E. 2560 (2017), Section 234"
            )
            self.assertEqual(cites, [("constitution", "234")])
            self.assertEqual(firewall.missing_citations(cites, registry), ["constitution:234"])

    def test_unknown_thai_code_is_unrecognized(self) -> None:
        cites = firewall.extract_citations("ประมวลกฎหมายยาเสพติด มาตรา 5")
        self.assertEqual(cites, [(firewall.UNRECOGNIZED, "5")])

    def test_constitutional_court_is_not_a_constitution_cite(self) -> None:
        cites = firewall.extract_citations(
            "Constitutional Court justices holding specified positions, Section 102"
        )
        self.assertNotIn(("constitution", "102"), cites)

    def test_html_wrapped_pdpa_title_binds_section_37(self) -> None:
        phrase = (
            "<strong>พระราชบัญญัติคุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562</strong> "
            "&mdash; มาตรา 37(1), 37(4), 39"
        )
        cites = firewall.extract_citations(phrase)
        self.assertIn(("pdpa", "37"), cites)
        self.assertNotIn((None, "37"), cites)

    def test_html_wrapped_pdpa_37_does_not_pass_on_arbitration_37(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp)
            (kb / "arbitration.md").write_text(
                "statute: arbitration\nOfficial source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 37\n",
                encoding="utf-8",
            )
            registry = firewall.load_registry(kb)
            phrase = (
                "<strong>พระราชบัญญัติคุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562</strong> "
                "&mdash; มาตรา 37"
            )
            cites = firewall.extract_citations(phrase)
            self.assertEqual(cites, [("pdpa", "37")])
            self.assertEqual(firewall.missing_citations(cites, registry), ["pdpa:37"])

    def test_sentence_initial_patent_act_does_not_pass_on_other_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            (Path(tmp) / "ccc.md").write_text(
                "statute: ccc\nOfficial source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 3\n",
                encoding="utf-8",
            )
            registry = firewall.load_registry(kb)
            cites = firewall.extract_citations("The Patent Act, Section 3")
            self.assertEqual(cites, [(firewall.UNRECOGNIZED, "3")])
            self.assertEqual(firewall.missing_citations(cites, registry), ["unrecognized:3"])

    def test_pdpa_slash_list_89_90_is_not_a_securities_insert(self) -> None:
        cites = firewall.extract_citations("PDPA Sections 89 / 90")
        self.assertEqual(cites, [("pdpa", "89"), ("pdpa", "90")])
        cites_18 = firewall.extract_citations("PDPA Sections 89 / 18")
        self.assertEqual(cites_18, [("pdpa", "89"), ("pdpa", "18")])
        self.assertNotIn(("pdpa", "89/18"), cites_18)
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp)
            (kb / "pdpa.md").write_text(
                "statute: pdpa\nOfficial source: https://www.ocs.go.th/searchlaw-law\n"
                "- มาตรา 89\n- มาตรา 90\n",
                encoding="utf-8",
            )
            registry = firewall.load_registry(kb)
            self.assertEqual(firewall.missing_citations(cites, registry), [])
            self.assertNotIn("89/90", registry["pdpa"])

    def test_pdpa_section_118_does_not_pass_on_lpa_118(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            registry = firewall.load_registry(kb)
            self.assertEqual(registry["lpa"], {"118"})
            self.assertNotIn("118", registry.get("pdpa", set()))
            for phrase in (
                "Personal Data Protection Act, Section 118",
                "Personal Data Protection Act B.E. 2562 (2019), Section 118",
                "Section 118 of the Personal Data Protection Act",
            ):
                cites = firewall.extract_citations(phrase)
                self.assertEqual(cites, [("pdpa", "118")], phrase)
                missing = firewall.missing_citations(cites, registry)
                self.assertEqual(missing, ["pdpa:118"], phrase)

    def test_registry_splits_slash_lists_and_does_not_keep_combined_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp)
            (kb / "fba.md").write_text(
                "statute: fba\nOfficial source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 36/37\n",
                encoding="utf-8",
            )
            (kb / "ccc.md").write_text(
                "statute: ccc\nOfficial source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 159/164\n",
                encoding="utf-8",
            )
            registry = firewall.load_registry(kb)
            self.assertEqual(registry["fba"], {"36", "37"})
            self.assertEqual(registry["ccc"], {"159", "164"})
            self.assertNotIn("36/37", registry["fba"])
            self.assertNotIn("159/164", registry["ccc"])

    def test_lpa_section_118_passes_on_lpa_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            registry = firewall.load_registry(kb)
            cites = firewall.extract_citations("พระราชบัญญัติคุ้มครองแรงงาน พ.ศ. 2541 มาตรา 118")
            missing = firewall.missing_citations(cites, registry)
            self.assertEqual(missing, [])

    def test_bare_section_passes_if_registered_under_any_statute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            registry = firewall.load_registry(kb)
            missing = firewall.missing_citations(firewall.extract_citations("มาตรา 118"), registry)
            self.assertEqual(missing, [])

    def test_unknown_section_remains_a_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            registry = firewall.load_registry(kb)
            missing = firewall.missing_citations(firewall.extract_citations("มาตรา 99999"), registry)
            self.assertEqual(missing, ["99999"])

    def test_named_securities_268_does_not_pass_on_ccc_268(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp)
            (kb / "ccc.md").write_text(
                "statute: ccc\nOfficial source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 268\n",
                encoding="utf-8",
            )
            (kb / "securities.md").write_text(
                "statute: securities\nOfficial source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 32\n",
                encoding="utf-8",
            )
            registry = firewall.load_registry(kb)
            cites = firewall.extract_citations(
                "พระราชบัญญัติหลักทรัพย์และตลาดหลักทรัพย์ พ.ศ. ๒๕๓๕ มาตรา ๒๖๘"
            )
            self.assertEqual(cites, [("securities", "268")])
            self.assertEqual(firewall.missing_citations(cites, registry), ["securities:268"])

    def test_securities_insert_phrase_does_not_need_bare_23(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp)
            (kb / "securities.md").write_text(
                "statute: securities\nOfficial source: https://www.ocs.go.th/searchlaw-law\n"
                "- มาตรา 89/8\n- มาตรา 89/18\n- มาตรา 89/23\n- มาตรา 63\n",
                encoding="utf-8",
            )
            registry = firewall.load_registry(kb)
            self.assertNotIn("18", registry["securities"])
            self.assertNotIn("23", registry["securities"])
            self.assertNotIn("89", registry["securities"])
            phrases = (
                "พระราชบัญญัติหลักทรัพย์และตลาดหลักทรัพย์ พ.ศ. ๒๕๓๕ มาตรา ๘๙/๒๓",
                "มาตรา ๘๙/๘",
                "พระราชบัญญัติหลักทรัพย์และตลาดหลักทรัพย์ พ.ศ. ๒๕๓๕ มาตรา ๘๙/๑๘",
                "ตามมาตรา ๖๓",
            )
            for phrase in phrases:
                cites = firewall.extract_citations(phrase)
                self.assertEqual(firewall.missing_citations(cites, registry), [], phrase)

    def test_registry_without_url_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp)
            (kb / "reg.md").write_text("statute: ccc\n- มาตรา 213\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                firewall.load_registry(kb)

    def test_each_registry_file_needs_its_own_official_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp)
            (kb / "lpa.md").write_text(
                "statute: lpa\nOfficial source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 118\n",
                encoding="utf-8",
            )
            (kb / "pdpa.md").write_text("statute: pdpa\n- มาตรา 999\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "pdpa.md"):
                firewall.load_registry(kb)

    def test_registry_without_statute_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp)
            (kb / "reg.md").write_text(
                "Official source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 213\n",
                encoding="utf-8",
            )
            with self.assertRaises(RuntimeError):
                firewall.load_registry(kb)


if __name__ == "__main__":
    unittest.main()
