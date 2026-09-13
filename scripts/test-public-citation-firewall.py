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


class CitationExtractionTests(unittest.TestCase):
    def test_lawquote_thai_numeral_is_a_citation(self) -> None:
        html = '<div class="lawquote"><pre>มาตรา ๒๑๓  ถ้าลูกหนี้ละเลย</pre></div>'
        self.assertEqual(set(firewall.cited_sections(html)), {"213"})

    def test_outline_comment_is_not_a_citation(self) -> None:
        html = "<!-- SECTION 7: Tax Gross-Up -->\n<p>ไม่มีมาตรา</p>"
        self.assertEqual(firewall.cited_sections(html), [])

    def test_intervening_section_does_not_inherit_prior_statute(self) -> None:
        cites = firewall.extract_citations("ปพพ. มาตรา 577 + มาตรา 118 พ.ร.บ.คุ้มครองแรงงาน")
        self.assertIn((None, "118"), cites)

    def test_arabic_lecture_cite_still_counts(self) -> None:
        self.assertIn("222", firewall.cited_sections("ปพพ. มาตรา 222"))

    def test_slash_list_splits_into_two_sections(self) -> None:
        html = "FBA Sections 36 / 37 (พ.ร.บ.ประกอบธุรกิจของคนต่างด้าว พ.ศ. 2542 มาตรา 36/37)"
        self.assertEqual(set(firewall.cited_sections(html)), {"36", "37"})
        self.assertEqual(firewall.cited_sections("มาตรา 159/164"), ["159", "164"])

    def test_inserted_section_stays_compound(self) -> None:
        self.assertEqual(firewall.cited_sections("มาตรา 41/1"), ["41/1"])
        self.assertEqual(firewall.cited_sections("มาตรา 193/30"), ["193/30"])


class RegistryAndGateTests(unittest.TestCase):
    def test_thai_article_matches_arabic_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            registry = firewall.load_registry(kb)
            missing = firewall.missing_citations(firewall.extract_citations("ปพพ. มาตรา ๒๑๓"), registry)
            self.assertEqual(missing, [])

    def test_pdpa_section_118_does_not_pass_on_lpa_118(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = write_kb(Path(tmp))
            registry = firewall.load_registry(kb)
            self.assertEqual(registry["lpa"], {"118"})
            self.assertNotIn("118", registry.get("pdpa", set()))
            cites = firewall.extract_citations("Personal Data Protection Act, Section 118")
            self.assertEqual(cites, [("pdpa", "118")])
            missing = firewall.missing_citations(cites, registry)
            self.assertEqual(missing, ["pdpa:118"])

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

    def test_registry_without_url_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp)
            (kb / "reg.md").write_text("statute: ccc\n- มาตรา 213\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
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
