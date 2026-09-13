#!/usr/bin/env python3
"""Regression tests for the public citation firewall.

Proves the publication-gate parser: Thai numerals match Arabic registry keys,
HTML outline comments are not citations, and unmatched sections still fail
closed.
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

    def test_arabic_lecture_cite_still_counts(self) -> None:
        self.assertIn("222", firewall.cited_sections("ปพพ. มาตรา 222"))


class RegistryAndGateTests(unittest.TestCase):
    def test_thai_article_matches_arabic_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp)
            (kb / "reg.md").write_text(
                "Official source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 213\n",
                encoding="utf-8",
            )
            registry = firewall.load_registry(kb)
            self.assertIn("213", registry)
            missing = set(firewall.cited_sections("มาตรา ๒๑๓")) - registry
            self.assertEqual(missing, set())

    def test_unknown_section_remains_a_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp)
            (kb / "reg.md").write_text(
                "Official source: https://www.ocs.go.th/searchlaw-law\n- มาตรา 213\n",
                encoding="utf-8",
            )
            registry = firewall.load_registry(kb)
            missing = set(firewall.cited_sections("มาตรา 99999")) - registry
            self.assertEqual(missing, {"99999"})

    def test_registry_without_url_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = Path(tmp)
            (kb / "reg.md").write_text("- มาตรา 213\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                firewall.load_registry(kb)


if __name__ == "__main__":
    unittest.main()
