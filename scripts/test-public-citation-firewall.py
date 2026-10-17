#!/usr/bin/env python3
"""Regression tests for the public citation firewall.

Proves Thai-numeral normalization, HTML-comment ignoring, slash-list splits,
statute-scoped registry keys, and fail-closed unmatched sections.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
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
            firewall.extract_citations("Plant Variety Protection Act B.E. 2542, Section 3"),
            [(firewall.UNRECOGNIZED, "3")],
        )
        self.assertEqual(
            firewall.extract_citations("Section 3 of the Plant Variety Protection Act"),
            [(firewall.UNRECOGNIZED, "3")],
        )
        self.assertEqual(
            firewall.extract_citations("Anti-Smuggling Act B.E. 2567, Section 4"),
            [(firewall.UNRECOGNIZED, "4")],
        )

    def test_sentence_initial_the_plant_variety_act_is_unrecognized(self) -> None:
        self.assertEqual(
            firewall.extract_citations("The Plant Variety Protection Act, Section 3"),
            [(firewall.UNRECOGNIZED, "3")],
        )
        self.assertEqual(
            firewall.extract_citations("The Act, Section 3"),
            [(None, "3")],
        )

    def test_thai_abbreviated_act_names_bind(self) -> None:
        self.assertEqual(firewall.extract_citations("ตาม พ.ร.บ.โรงแรม พ.ศ. 2547 มาตรา 15"), [("hotel", "15")])
        self.assertEqual(firewall.extract_citations("พ.ร.บ.ลิขสิทธิ์ พ.ศ. 2537 มาตรา 19"), [("copyright", "19")])
        self.assertEqual(firewall.extract_citations("พ.ร.บ.สิทธิบัตร พ.ศ. 2522 มาตรา 65 สัตต"), [("patent", "65 สัตต")])
        self.assertEqual(firewall.extract_citations("Patent Act B.E. 2522, Section 35"), [("patent", "35")])
        self.assertEqual(firewall.extract_citations("ตาม พ.ร.บ.การบัญชี พ.ศ. 2543 มาตรา 11"), [("accounting", "11")])
        self.assertEqual(
            firewall.extract_citations("พระราชบัญญัติว่าด้วยการขัดกันแห่งกฎหมาย พ.ศ. 2481 มาตรา 8"),
            [("conflictlaws", "8")],
        )
        self.assertEqual(firewall.extract_citations("พระราชบัญญัติประกันสังคม พ.ศ. 2533 มาตรา 67"), [("socialsecurity", "67")])

    def test_owner_supplied_act_titles_bind(self) -> None:
        self.assertEqual(firewall.extract_citations("พระราชบัญญัติทนายความ พ.ศ. 2528 มาตรา 33"), [("lawyers", "33")])
        self.assertEqual(firewall.extract_citations("พระราชบัญญัติเครื่องสำอาง พ.ศ. 2558 มาตรา 41"), [("cosmetics", "41")])
        self.assertEqual(
            firewall.extract_citations("พระราชบัญญัติขายตรงและตลาดแบบตรง พ.ศ. 2545 มาตรา 33"), [("directsales", "33")]
        )
        self.assertEqual(firewall.extract_citations("พระราชบัญญัติแรงงานสัมพันธ์ พ.ศ. 2518 มาตรา 13"), [("labourrelations", "13")])
        self.assertEqual(firewall.extract_citations("ประมวลกฎหมายวิธีพิจารณาความอาญา มาตรา 126"), [("criminalprocedure", "126")])
        self.assertEqual(firewall.extract_citations("ป.วิ.พ. มาตรา 173"), [("civilprocedure", "173")])

    def test_owner_supplied_aliases_do_not_steal_neighbours(self) -> None:
        self.assertEqual(firewall.extract_citations("ประมวลกฎหมายอาญา มาตรา 352"), [("criminal", "352")])
        self.assertEqual(firewall.extract_citations("พระราชบัญญัติคุ้มครองแรงงาน พ.ศ. 2541 มาตรา 118"), [("lpa", "118")])

    def test_item9_act_titles_bind(self) -> None:
        self.assertEqual(firewall.extract_citations("พระราชบัญญัติศุลกากร พ.ศ. 2560 มาตรา 52"), [("customs", "52")])
        self.assertEqual(
            firewall.extract_citations("พระราชบัญญัติการรักษาความมั่นคงปลอดภัยไซเบอร์ พ.ศ. 2562 มาตรา 3"), [("cyber", "3")]
        )
        self.assertEqual(
            firewall.extract_citations("พระราชกำหนดว่าด้วยการประชุมผ่านสื่ออิเล็กทรอนิกส์ พ.ศ. 2563 มาตรา 9"),
            [("emeeting", "9")],
        )
        self.assertEqual(firewall.extract_citations("พระราชบัญญัติสถานพยาบาล พ.ศ. 2541 มาตรา 16"), [("healthfacility", "16")])
        self.assertEqual(
            firewall.extract_citations(
                "พระราชบัญญัติกำหนดความผิดเกี่ยวกับห้างหุ้นส่วนจดทะเบียน ห้างหุ้นส่วนจำกัด บริษัทจำกัด สมาคม และมูลนิธิ"
                " พ.ศ. 2499 มาตรา 41"
            ),
            [("partnershipoffences", "41")],
        )

    def test_item9_subject_phrase_without_act_title_does_not_bind(self) -> None:
        cites = firewall.extract_citations(
            "ส่วนการรับขนของทางทะเลต้องใช้กฎหมายว่าด้วยการรับขนของทางทะเลตามมาตรา 609 ของประมวลกฎหมายแพ่งและพาณิชย์"
        )
        self.assertNotIn(("seacarriage", "609"), cites)
        self.assertNotIn(("drug", "5"), firewall.extract_citations("พระราชบัญญัติยาเสพติดให้โทษ มาตรา 5"))

    def test_entity_list_without_partnership_offences_title_does_not_bind(self) -> None:
        cites = firewall.extract_citations("ห้างหุ้นส่วนจำกัด บริษัทจำกัด สมาคม และมูลนิธิ มาตรา 41")
        self.assertNotIn(("partnershipoffences", "41"), cites)
        full = (
            "พระราชบัญญัติกำหนดความผิดเกี่ยวกับห้างหุ้นส่วนจดทะเบียน ห้างหุ้นส่วนจำกัด บริษัทจำกัด สมาคม "
            "และมูลนิธิ พ.ศ. 2499 มาตรา 41"
        )
        self.assertEqual(firewall.extract_citations(full), [("partnershipoffences", "41")])

    def test_longer_english_title_ending_in_known_act_is_unrecognized(self) -> None:
        self.assertEqual(
            firewall.extract_citations("Controlled Drug Act B.E. 2550 Section 21"),
            [(firewall.UNRECOGNIZED, "21")],
        )
        self.assertEqual(
            firewall.extract_citations("Section 21 of the Controlled Drug Act"),
            [(firewall.UNRECOGNIZED, "21")],
        )
        self.assertEqual(firewall.extract_citations("Drug Act B.E. 2510, Section 21"), [("drug", "21")])
        self.assertEqual(
            firewall.extract_citations("Thai Labour Protection Act, Section 118"), [("lpa", "118")]
        )
        self.assertEqual(
            firewall.extract_citations("Civil and Commercial Code Section 420"), [("ccc", "420")]
        )
        self.assertEqual(
            firewall.extract_citations("Unfair Contract Terms Act B.E. 2540, Section 4"), [("ucta", "4")]
        )

    def test_thai_inserted_section_suffix_is_part_of_the_section(self) -> None:
        self.assertEqual(
            firewall.extract_citations("พระราชบัญญัติควบคุมอาคาร พ.ศ. 2522 มาตรา 32 ทวิ และมาตรา 65 ทวิ"),
            [("building", "32 ทวิ"), ("building", "65 ทวิ")],
        )
        self.assertEqual(
            firewall.extract_citations("พระราชบัญญัติอาคารชุด พ.ศ. 2522 มาตรา 19 เตรส"), [("condo", "19 เตรส")]
        )
        self.assertEqual(firewall.extract_citations("พระราชบัญญัติควบคุมอาคาร พ.ศ. 2522 มาตรา 5 ฉบับนี้"), [("building", "5")])
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp)
            (kb / "building.md").write_text(
                "statute: building\nhttps://searchlaw.ocs.go.th/\n- มาตรา 32\n- มาตรา 32 ทวิ\n", encoding="utf-8"
            )
            registry = firewall.load_registry(kb)
            self.assertEqual(registry["building"], {"32", "32 ทวิ"})
            cites = firewall.extract_citations("พระราชบัญญัติควบคุมอาคาร พ.ศ. 2522 มาตรา 32 ตรี")
            self.assertEqual(firewall.missing_citations(cites, registry), ["building:32 ตรี"])

    def test_base_number_statutes_resolve_suffixes_on_the_base_number(self) -> None:
        registry = {"revenue": {"65", "35 ตรี"}, "building": {"32"}}
        self.assertIsNone(firewall.resolve_key("revenue", "65 ทวิ", registry))  # the Revenue Code is exact now
        with mock.patch.object(firewall, "BASE_NUMBER_STATUTES", {"revenue"}):
            self.assertEqual(firewall.resolve_key("revenue", "65 ทวิ", registry), "revenue:65 ทวิ")
            self.assertEqual(firewall.resolve_key("revenue", "35", registry), "revenue:35")
            self.assertIsNone(firewall.resolve_key("building", "32 ทวิ", registry))
            self.assertIsNone(firewall.resolve_key("revenue", "66 ทวิ", registry))

    def test_revenue_code_inserted_sections_stay_whole(self) -> None:
        self.assertEqual(firewall.extract_citations("ประมวลรัษฎากร มาตรา 91/10"), [("revenue", "91/10")])
        self.assertEqual(firewall.extract_citations("ประมวลรัษฎากร มาตรา 85/14"), [("revenue", "85/14")])
        self.assertEqual(firewall.extract_citations("FBA Sections 36/37"), [("fba", "36"), ("fba", "37")])

    def test_bankruptcy_rehabilitation_sections_stay_whole(self) -> None:
        self.assertEqual(
            firewall.extract_citations("พระราชบัญญัติล้มละลาย พุทธศักราช 2483 มาตรา 90/41"), [("bankruptcy", "90/41")]
        )
        self.assertEqual(firewall.expand_section_token("90/41", "bankruptcy"), ["90/41"])
        self.assertEqual(firewall.expand_section_token("36/37", "fba"), ["36", "37"])

    def test_phrase_before_matches_a_full_scan(self) -> None:
        text = ("ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา 1 " * 60) + ("ก" * 700) + " มาตรา 2 ข้อความ " + ("ข" * 30)
        last_end = 0
        for match in firewall.SECTION_RE.finditer(text):
            last_end = match.end()
        self.assertEqual(firewall.phrase_before(text), text[last_end:][-firewall.PREFIX_LIMIT:])
        self.assertEqual(firewall.phrase_before("ก" * 900), ("ก" * 900)[-firewall.PREFIX_LIMIT:])

    def test_social_security_word_alone_is_not_the_act(self) -> None:
        cites = firewall.extract_citations("พ.ร.บ.คุ้มครองแรงงาน เงินประกันสังคม มาตรา 118")
        self.assertNotIn(("socialsecurity", "118"), cites)

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
            "Unlike the Civil Code, the Plant Variety Protection Act, Section 3 applies"
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

    def test_sentence_initial_plant_variety_act_does_not_pass_on_other_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            (Path(tmp) / "ccc.md").write_text(
                "statute: ccc\nOfficial source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 3\n",
                encoding="utf-8",
            )
            registry = firewall.load_registry(kb)
            cites = firewall.extract_citations("The Plant Variety Protection Act, Section 3")
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


def scan(text: str):
    return firewall.scan_text(text)


def gate(text: str, kb: Path) -> tuple[int, str]:
    out = io.StringIO()
    status = firewall.check_text(text, firewall.load_registry(kb), out=out, err=out)
    return status, out.getvalue()


class NonCanonicalSectionFormTests(unittest.TestCase):
    """G2 (audit 17 ตุลาคม 2569): forms the gate used to miss now parse, or fail as unparsed."""

    def test_thai_abbreviation_ma_dot_is_a_bound_citation(self) -> None:
        self.assertEqual(firewall.extract_citations("ป.พ.พ. ม.9999"), [("ccc", "9999")])
        self.assertEqual(firewall.extract_citations("ป.พ.พ. ม. 391"), [("ccc", "391")])
        self.assertEqual(firewall.extract_citations("พ.ร.บ.อนุญาโตตุลาการ ม.40-41"), [("arbitration", "40")])

    def test_ma_dot_inside_a_thai_word_is_not_a_citation(self) -> None:
        self.assertEqual(firewall.cited_sections("หนังสือกรมสรรพากร ที่ กค 0706(กม.01)/123"), [])
        self.assertEqual(scan("กม.01").unparsed, [])

    def test_matra_without_space_is_a_citation(self) -> None:
        self.assertEqual(firewall.extract_citations("ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา9999"), [("ccc", "9999")])
        self.assertEqual(firewall.cited_sections("มาตรา๓๙๑"), ["391"])

    def test_english_sec_and_s_abbreviations_are_citations(self) -> None:
        self.assertEqual(firewall.extract_citations("Civil and Commercial Code Sec. 9999"), [("ccc", "9999")])
        self.assertEqual(firewall.extract_citations("Civil and Commercial Code s. 9999"), [("ccc", "9999")])
        self.assertEqual(firewall.extract_citations("Food Act s.40"), [("food", "40")])
        self.assertEqual(firewall.cited_sections("(Sec. 1051)"), ["1051"])
        self.assertEqual(
            firewall.extract_citations("PDPA Secs. 28–29"), [("pdpa", "28"), ("pdpa", "29")]
        )
        self.assertEqual(
            firewall.extract_citations("PDPA ss. 28-29"), [("pdpa", "28"), ("pdpa", "29")]
        )

    def test_capital_s_and_us_are_not_citations(self) -> None:
        self.assertEqual(firewall.cited_sections("the U.S. 5 largest firms"), [])
        self.assertEqual(firewall.cited_sections("Plan S. 5 tiers"), [])
        self.assertEqual(scan("the U.S. 5 largest firms").unparsed, [])

    def test_unknown_section_form_is_unparsed_not_citation_free(self) -> None:
        result = scan("Civil and Commercial Code Sec 9999")
        self.assertEqual(result.citations, [])
        self.assertEqual(len(result.unparsed), 1)

    def test_unparsed_text_fails_with_exit_4(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            status, report = gate("<p>Civil and Commercial Code Sec 9999</p>", kb)
            self.assertEqual(status, firewall.EXIT_UNPARSED)
            self.assertIn("UNPARSED", report)
            status, _report = gate("<p>ปพพ. มาตรา 213 and Sec 9999</p>", kb)
            self.assertEqual(status, firewall.EXIT_UNPARSED)

    def test_text_without_section_like_tokens_is_exit_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            self.assertEqual(gate("<p>No statute here.</p>", kb)[0], firewall.EXIT_NO_CITATION)

    def test_registry_miss_wins_over_unparsed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            self.assertEqual(gate("<p>ป.พ.พ. ม.9999 and Sec 5</p>", kb)[0], firewall.EXIT_BLOCK)

    def test_abbreviated_forms_block_unregistered_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            for text in ("ป.พ.พ. ม.9999", "Civil and Commercial Code s. 9999", "Sec. 9999", "มาตรา9999"):
                self.assertEqual(gate(f"<p>{text}</p>", kb)[0], firewall.EXIT_BLOCK, text)
            self.assertEqual(gate("<p>ป.พ.พ. ม.213</p>", kb)[0], firewall.EXIT_PASS)


class SectionListTests(unittest.TestCase):
    def test_bound_comma_list_is_expanded_and_checked(self) -> None:
        cites = firewall.extract_citations("the Civil and Commercial Code, Sections 1012, 1025 and 1064.")
        self.assertEqual(cites, [("ccc", "1012"), ("ccc", "1025"), ("ccc", "1064")])
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            status, report = gate("<p>Civil and Commercial Code, Sections 213 and 9999</p>", kb)
            self.assertEqual(status, firewall.EXIT_BLOCK)
            self.assertIn("ccc:9999", report)

    def test_unbound_list_is_reported_for_review_not_cited(self) -> None:
        result = scan("political office holders (Sections 10 to 13)")
        self.assertEqual(result.citations, [])
        self.assertEqual(result.review_lists, ["Sections 10 to 13"])
        self.assertEqual(result.unparsed, [])
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            status, report = gate("<p>Sections 102, 105</p>", kb)
            self.assertEqual(status, firewall.EXIT_NO_CITATION)
            self.assertIn("REVIEW unbound section list", report)

    def test_list_items_with_subsections_paragraphs_and_suffixes(self) -> None:
        self.assertEqual(
            firewall.extract_citations("Revenue Code — Sections 40(1), 40(2), 40(6)"),
            [("revenue", "40")] * 3,
        )
        self.assertEqual(
            firewall.extract_citations("TCCC Sections 193/14(3), 295, 682 para. 2, 692"),
            [("ccc", "193/14"), ("ccc", "295"), ("ccc", "682"), ("ccc", "692")],
        )
        self.assertEqual(
            firewall.extract_citations("Revenue Code Sections 65 bis (4) and 71 bis"),
            [("revenue", "65"), ("revenue", "71")],
        )
        self.assertEqual(
            firewall.extract_citations("Civil and Commercial Code Sections 425 + 291"),
            [("ccc", "425"), ("ccc", "291")],
        )

    def test_list_to_range_and_et_seq(self) -> None:
        self.assertEqual(
            firewall.extract_citations("Public Limited Companies Act B.E. 2535 (Sections 180 to 182)"),
            [("plc", "180"), ("plc", "181"), ("plc", "182")],
        )
        self.assertEqual(
            firewall.extract_citations("Land Code B.E. 2497 — Sections 86 et seq."), [("landcode", "86")]
        )
        self.assertEqual(
            firewall.extract_citations("Civil and Commercial Code Sections 1012 to 1273/4"),
            [("ccc", "1012"), ("ccc", "1273/4")],
        )

    def test_list_owns_its_plural_slash_head(self) -> None:
        self.assertEqual(
            firewall.extract_citations("Foreign Business Act Sections 36/37, 38"),
            [("fba", "36"), ("fba", "37"), ("fba", "38")],
        )
        self.assertEqual(firewall.cited_sections("FBA Sections 36 / 37"), ["36", "37"])

    def test_list_naming_an_unknown_act_is_unrecognized(self) -> None:
        cites = firewall.extract_citations("Plant Variety Protection Act Sections 33, 34")
        self.assertEqual(cites, [("unrecognized", "33"), ("unrecognized", "34")])


class TrailingHaengBindingTests(unittest.TestCase):
    """F1 (audit 17 ตุลาคม 2569): 'มาตรา N แห่ง พ.ร.บ.X' binds X when X's aliases carry the Act prefix."""

    def test_prefixed_aliases_bind_after_haeng(self) -> None:
        cases = {
            "มาตรา 5 แห่งพระราชบัญญัติการบัญชี พ.ศ. 2543": "accounting",
            "มาตรา 26 แห่ง พ.ร.บ.โรงแรม พ.ศ. 2547": "hotel",
            "มาตรา 26 แห่ง พ.ร.บ. โรงแรม พ.ศ. 2547": "hotel",
            "มาตรา 44 แห่งพระราชบัญญัติลิขสิทธิ์ พ.ศ. 2537": "copyright",
            "มาตรา 38 แห่งพระราชบัญญัติยา พ.ศ. 2510": "drug",
            "มาตรา 27 แห่งพระราชบัญญัติการขนส่งต่อเนื่องหลายรูปแบบ พ.ศ. 2548": "multimodal",
            "มาตรา 10 แห่งพระราชบัญญัติศุลกากร พ.ศ. 2560": "customs",
            "มาตรา 33 แห่งพระราชบัญญัติทนายความ พ.ศ. 2528": "lawyers",
            "มาตรา 15/22 แห่งพระราชบัญญัติการเดินอากาศ พ.ศ. 2497": "airnav",
            "มาตรา 5 ของพระราชบัญญัติการไกล่เกลี่ยข้อพิพาท พ.ศ. 2562": "mediation",
            "มาตรา 5 ตามพระราชกำหนดการประกอบธุรกิจสินทรัพย์ดิจิทัล พ.ศ. 2561": "digitalasset",
        }
        for text, key in cases.items():
            statutes = {statute for statute, _section in firewall.extract_citations(text)}
            self.assertEqual(statutes, {key}, text)

    def test_longest_alias_wins_after_haeng(self) -> None:
        self.assertEqual(
            firewall.extract_citations("มาตรา 5 แห่งพระราชบัญญัติสถาบันอนุญาโตตุลาการ พ.ศ. 2550"),
            [("arbinstitute", "5")],
        )
        self.assertEqual(
            firewall.extract_citations("มาตรา 40 แห่งพระราชบัญญัติอนุญาโตตุลาการ พ.ศ. 2545"),
            [("arbitration", "40")],
        )

    def test_haeng_bound_section_does_not_pass_on_another_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp)
            (kb / "ccc.md").write_text(
                "statute: ccc\nOfficial source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 26\n",
                encoding="utf-8",
            )
            (kb / "hotel.md").write_text(
                "statute: hotel\nOfficial source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 15\n",
                encoding="utf-8",
            )
            status, report = gate("<p>มาตรา 26 แห่งพระราชบัญญัติโรงแรม พ.ศ. 2547</p>", kb)
            self.assertEqual(status, firewall.EXIT_BLOCK)
            self.assertIn("hotel:26", report)

    def test_bare_following_word_or_next_list_item_does_not_bind(self) -> None:
        self.assertEqual(firewall.extract_citations("มาตรา 150 อาคารชุดที่จดทะเบียน"), [(None, "150")])
        cites = firewall.extract_citations(
            "พ.ร.บ.โรงงาน พ.ศ. 2535 มาตรา 13 มาตรา 18 และมาตรา 19 พ.ร.บ.การประกอบกิจการพลังงาน พ.ศ. 2550 มาตรา 47"
        )
        self.assertNotIn(("energy", "19"), cites)
        self.assertIn(("energy", "47"), cites)


class BatchModeTests(unittest.TestCase):
    """G7: one registry load for many files, with a [PASS]/[BLOCK] verdict per file."""

    def run_main(self, argv: list[str]) -> tuple[int, str]:
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["firewall", *argv]), contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(out):
            status = firewall.main()
        return status, out.getvalue()

    def test_batch_loads_registry_once_and_reports_each_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "kb").mkdir()
            kb = write_kb(root / "kb")
            pages = {
                "pass.html": "<p>ป.พ.พ. มาตรา 213</p>",
                "none.html": "<p>No statute.</p>",
                "block.html": "<p>ป.พ.พ. ม.9999</p>",
                "unparsed.html": "<p>Civil and Commercial Code Sec 9999</p>",
            }
            for name, body in pages.items():
                (root / name).write_text(body, encoding="utf-8")
            files = [str(root / name) for name in pages] + [str(root / "missing.html")]
            real_load = firewall.load_registry
            with mock.patch.object(firewall, "load_registry", side_effect=real_load) as loader:
                status, report = self.run_main(["--kb", str(kb), "--input", *files])
            self.assertEqual(loader.call_count, 1)
            self.assertEqual(status, firewall.EXIT_BLOCK)
            self.assertIn(f"[PASS] {root / 'pass.html'} — citations verified", report)
            self.assertIn(f"[PASS] {root / 'none.html'} — no statutory citation detected", report)
            self.assertIn(f"[BLOCK] {root / 'block.html'} — firewall exit 1", report)
            self.assertIn(f"[BLOCK] {root / 'unparsed.html'} — firewall exit 4", report)
            self.assertIn(f"[BLOCK] {root / 'missing.html'} — firewall exit 3", report)
            self.assertIn("files=5 blocked=3", report)

    def test_single_input_keeps_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "kb").mkdir()
            kb = write_kb(root / "kb")
            for body, expected in (
                ("<p>ป.พ.พ. มาตรา 213</p>", 0),
                ("<p>ป.พ.พ. ม.9999</p>", 1),
                ("<p>No statute.</p>", 2),
                ("<p>Sec 12</p>", 4),
            ):
                (root / "page.html").write_text(body, encoding="utf-8")
                status, _report = self.run_main(["--kb", str(kb), "--input", str(root / "page.html")])
                self.assertEqual(status, expected, body)


class VerifyScriptTests(unittest.TestCase):
    """verify-legal-citations.sh: exit 4 blocks, reviewed blog pages are in --all, other blog pages are not."""

    def setUp(self) -> None:
        if shutil.which("bash") is None or shutil.which("git") is None:
            self.skipTest("bash and git are required")
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        scripts = self.root / "scripts"
        scripts.mkdir()
        here = Path(__file__).parent
        for name in ("verify-legal-citations.sh", "public-citation-firewall.py", "las_public_pages.py"):
            shutil.copy(here / name, scripts / name)
        (scripts / "legal-kb").mkdir()
        write_kb(scripts / "legal-kb")
        for rel, body in {
            "articles/ok.html": "<p>ป.พ.พ. มาตรา 213</p>",
            "articles/plain.html": "<p>No statute.</p>",
            "articles/unparsed.html": "<p>Civil and Commercial Code Sec 9999</p>",
            "blog/x/reviewed.html": "<p>ป.พ.พ. ม.9999</p>",
            "blog/x/campaign.html": "<p>มาตรา 99999</p>",
        }.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        (self.root / "learning-hub").mkdir()
        (self.root / "learning-hub" / "legal-reviews.json").write_text(
            json.dumps({"variants": {"articles/ok.html": {}, "blog/x/reviewed.html": {}}}), encoding="utf-8"
        )
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def verify(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = {k: v for k, v in os.environ.items() if k not in {"LAS_CITATION_FIREWALL", "LAS_LEGAL_KB"}}
        return subprocess.run(
            ["bash", "scripts/verify-legal-citations.sh", *args],
            cwd=self.root, capture_output=True, text=True, env=env,
        )

    def test_unparsed_page_is_blocked(self) -> None:
        result = self.verify("articles/unparsed.html")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("[BLOCK] articles/unparsed.html — firewall exit 4", result.stdout)

    def test_no_citation_page_passes(self) -> None:
        result = self.verify("articles/plain.html", "articles/ok.html")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("RESULT: all files passed citation gate", result.stdout)

    def test_all_covers_reviewed_blog_pages_only(self) -> None:
        result = self.verify("--all")
        self.assertIn("[BLOCK] blog/x/reviewed.html", result.stdout)
        self.assertNotIn("campaign.html", result.stdout)
        self.assertIn("RESULT: 2 file(s) blocked", result.stdout)

    def test_unregistered_blog_page_is_rejected_as_argument(self) -> None:
        result = self.verify("blog/x/campaign.html")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not an article or reviewed blog HTML path", result.stderr)


class CodexFailOpenTests(unittest.TestCase):
    """PR #79 review: two fail-open paths found by Codex (17 ตุลาคม 2569)."""

    def kb_with_copyright_44(self, root: Path) -> Path:
        write_kb(root)
        (root / "copyright.md").write_text(
            "statute: copyright\nOfficial source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 44\n",
            encoding="utf-8",
        )
        return root

    def test_extended_act_title_does_not_bind_a_registered_prefix_alias(self) -> None:
        for text in (
            "มาตรา 44 แห่งพระราชบัญญัติลิขสิทธิ์ดิจิทัล",
            "มาตรา 44 แห่ง พ.ร.บ.ลิขสิทธิ์ดิจิทัล พ.ศ. 2570",
            "มาตรา 5 แห่งพระราชบัญญัติคุ้มครองแรงงานทางทะเล พ.ศ. 2558",
        ):
            cites = firewall.extract_citations(text)
            self.assertNotIn(("copyright", "44"), cites, text)
            self.assertNotIn(("lpa", "5"), cites, text)
            self.assertEqual({statute for statute, _section in cites}, {firewall.UNRECOGNIZED}, text)
        self.assert_complete_titles_still_bind()

    def test_extended_act_title_blocks_even_when_the_number_is_registered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = self.kb_with_copyright_44(Path(tmp))
            status, report = gate("<p>มาตรา 44 แห่งพระราชบัญญัติลิขสิทธิ์ดิจิทัล</p>", kb)
            self.assertEqual(status, firewall.EXIT_BLOCK, report)
            self.assertEqual(gate("<p>มาตรา 44 แห่งพระราชบัญญัติลิขสิทธิ์ พ.ศ. 2537</p>", kb)[0], firewall.EXIT_PASS)

    def assert_complete_titles_still_bind(self) -> None:
        cases = {
            "มาตรา 44 แห่งพระราชบัญญัติลิขสิทธิ์ พ.ศ. 2537": "copyright",
            "มาตรา 44 แห่งพระราชบัญญัติลิขสิทธิ์": "copyright",
            "มาตรา 44 แห่งพระราชบัญญัติลิขสิทธิ์, มาตรา 45": "copyright",
            "(มาตรา 44 แห่งพระราชบัญญัติลิขสิทธิ์)": "copyright",
            "มาตรา 44 แห่งพระราชบัญญัติลิขสิทธิ์ประกอบกฎกระทรวง": "copyright",
            "มาตรา 26 แห่ง พ.ร.บ.โรงแรม2547": "hotel",
            "มาตรา 4 แห่งพระราชบัญญัติว่าด้วยข้อสัญญาที่ไม่เป็นธรรมเป็นหลัก": "ucta",
            "มาตรา 5 แห่ง พ.ร.บ.การแข่งขันทางการค้า พ.ศ. 2560": "competition",
            "มาตรา 36 ของพระราชบัญญัติประกอบรัฐธรรมนูญว่าด้วยการป้องกันและปราบปรามการทุจริต พ.ศ. 2561": "nacc",
            "มาตรา 42 แห่งพระราชบัญญัติกำหนดความผิดเกี่ยวกับห้างหุ้นส่วนจดทะเบียน ห้างหุ้นส่วนจำกัด "
            "บริษัทจำกัด สมาคม และมูลนิธิ พ.ศ. 2499": "partnershipoffences",
            "มาตรา 5 แห่งพระราชบัญญัติสถาบันอนุญาโตตุลาการ พ.ศ. 2550": "arbinstitute",
        }
        for text, key in cases.items():
            self.assertEqual(firewall.extract_citations(text)[0][0], key, text)
        # "พระราชบัญญัติเดียวกัน / นี้ / ประกอบรัฐธรรมนูญนี้" refer back: unbound, not unrecognised.
        for text in ("มาตรา 9 แห่งพระราชบัญญัติเดียวกัน", "มาตรา 9 แห่งพระราชบัญญัติประกอบรัฐธรรมนูญนี้"):
            self.assertEqual(firewall.extract_citations(text), [(None, "9")], text)
        # A Code name is complete; Thai prose may follow it directly.
        self.assertEqual(
            firewall.extract_citations("มาตรา 150 แห่งประมวลกฎหมายแพ่งและพาณิชย์ไม่ได้กำหนดไว้"), [("ccc", "150")]
        )

    def test_statute_carries_across_coordinated_plural_lists(self) -> None:
        cites = firewall.extract_citations("Civil and Commercial Code Sections 213, 41/1 and Sections 9998, 9999")
        self.assertEqual(cites, [("ccc", "213"), ("ccc", "41/1"), ("ccc", "9998"), ("ccc", "9999")])
        self.assertEqual(scan("Civil and Commercial Code Sections 213, 41/1 and Sections 9998, 9999").review_lists, [])
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            status, report = gate("<p>Civil and Commercial Code Sections 213, 41/1 and Sections 9998, 9999</p>", kb)
            self.assertEqual(status, firewall.EXIT_BLOCK, report)
            self.assertIn("ccc:9998", report)
            self.assertIn("ccc:9999", report)

    def test_singular_head_lists_check_every_number(self) -> None:
        for text in ("ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา 150, 9999", "ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา 150 และ 9999",
                     "Civil and Commercial Code Section 150, 9999", "Civil and Commercial Code Section 150 or 9999"):
            self.assertEqual(firewall.extract_citations(text), [("ccc", "150"), ("ccc", "9999")], text)
            with tempfile.TemporaryDirectory() as tmp:
                status, report = gate(f"<p>{text}</p>", write_kb(Path(tmp)))
                self.assertEqual(status, firewall.EXIT_BLOCK, report)
                self.assertIn("ccc:9999", report)
        # a statute named after the list binds every item; Thai insert suffixes and Thai digits are kept
        self.assertEqual(firewall.extract_citations("Section 27 or 28 of the Personal Data Protection Act"),
                         [("pdpa", "27"), ("pdpa", "28")])
        self.assertEqual(firewall.extract_citations("มาตรา ๗๑ ทวิ และ ๗๑ ตรี แห่งประมวลรัษฎากร"),
                         [("revenue", "71 ทวิ"), ("revenue", "71 ตรี")])
        # a number followed by a unit, hyphen or word is not a section
        for text in ("Section 183, 10-category review", "Section 183, 10 categories", "มาตรา 5 และ 2 ปี"):
            self.assertEqual(len(firewall.extract_citations(text)), 1, text)

    def test_statute_carries_across_a_bare_comma_between_singular_tokens(self) -> None:
        for text in ("Civil and Commercial Code Section 150, Section 9", "ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา 150, มาตรา 9"):
            self.assertEqual(firewall.extract_citations(text), [("ccc", "150"), ("ccc", "9")], text)
        # a full stop is not coordination: the next citation binds to its own statute
        self.assertEqual(firewall.extract_citations("Civil and Commercial Code Section 150. Section 9 of the PDPA"),
                         [("ccc", "150"), ("pdpa", "9")])

    def test_ccc_abbreviation_binds_and_latin_aliases_respect_word_boundaries(self) -> None:
        self.assertEqual(firewall.extract_citations("CCC Sections 797 and 9999"), [("ccc", "797"), ("ccc", "9999")])
        self.assertEqual(scan("CCC Sections 797 and 9999").review_lists, [])
        with tempfile.TemporaryDirectory() as tmp:
            status, report = gate("<p>(CCC Sections 797 and 9999)</p>", write_kb(Path(tmp)))
            self.assertEqual(status, firewall.EXIT_BLOCK, report)
            self.assertIn("ccc:9999", report)
        # an alias inside a longer Latin word is not that statute ("ACCC" is not the CCC)
        self.assertEqual(firewall.extract_citations("ACCC Section 4"), [(None, "4")])

    def test_statute_carries_between_singular_tokens_and_lists(self) -> None:
        self.assertIn(
            ("ccc", "9999"),
            firewall.extract_citations("Civil and Commercial Code Section 213 and Sections 9998, 9999"),
        )
        self.assertIn(
            ("ccc", "9999"),
            firewall.extract_citations("Civil and Commercial Code Sections 213, 41/1 and Section 9999"),
        )
        # No coordination, no carry: a later unrelated list stays a review item.
        result = scan("Civil and Commercial Code Sections 213, 41/1. The guide's Sections 3, 4 explain this.")
        self.assertEqual(result.review_lists, ["Sections 3, 4"])


if __name__ == "__main__":
    unittest.main()
