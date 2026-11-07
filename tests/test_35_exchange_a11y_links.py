"""Test 35 — M3 hardening on the exchange reader site + offline link
inventory baseline.

Applies the core structural accessibility checks to the exchange site
(synthetic v0.2 fixture), verifies the withheld-count transparency and
that no score observations leak, and runs pipeline/check_links.py in
offline inventory mode on the synthetic public export as the dead-link
baseline (networked --check remains a manual quarterly task).
"""
import csv
import re
import unittest
from pathlib import Path

try:
    from tests.util import (exchange_fixture, fixture, run_cli, SYNTHETIC,
                            CONTRACT)
except ImportError:  # pragma: no cover
    from util import (exchange_fixture, fixture, run_cli, SYNTHETIC,
                      CONTRACT)


class ExchangeSiteAccessibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx = exchange_fixture()
        cls.html = cls.fx.index_html

    def test_lang_skip_link_landmarks(self):
        self.assertIn('<html lang="en">', self.html)
        self.assertIn("Skip to main content", self.html)
        self.assertIn('id="main"', self.html)
        self.assertRegex(self.html, r"<nav\b[^>]*aria-label=")

    def test_no_positive_tabindex_no_empty_hrefs(self):
        self.assertNotRegex(self.html, r'tabindex="[1-9]')
        self.assertNotIn('href="#"', self.html)

    def test_viewport_and_unique_ids(self):
        self.assertIn('name="viewport"', self.html)
        ids = re.findall(r'\bid="([^"]+)"', self.html)
        dupes = {i for i in ids if ids.count(i) > 1}
        self.assertEqual(dupes, set())

    def test_links_have_discernible_text(self):
        for m in re.finditer(r"<a\b[^>]*>(.*?)</a>", self.html, re.S):
            text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            self.assertTrue(text, "empty link text")
            self.assertNotIn(text.lower(), ("click here", "here", "more"))

    def test_withheld_count_transparency(self):
        self.assertIn("withheld", self.html.lower())

    def test_no_score_observations_or_hashes(self):
        self.assertNotIn("score_observation", self.html)
        self.assertNotRegex(self.html, r"\b[0-9a-f]{64}\b")


class LinkInventoryBaseline(unittest.TestCase):
    """Offline inventory of the synthetic public export — the baseline for
    the quarterly networked dead-link report (plan test 12, manual)."""

    def test_check_links_offline_inventory(self):
        fx = fixture()
        report = fx.tmp / "links-baseline.csv"
        cp = run_cli(["pipeline/check_links.py",
                      "--export", str(fx.export_dir),
                      "--report", str(report)])
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        self.assertTrue(report.exists())
        rows = list(csv.DictReader(report.open(encoding="utf-8")))
        self.assertGreaterEqual(len(rows), 8)  # matches M1 changelog count
        for r in rows:
            self.assertTrue(r["url"].startswith("http"), r)


if __name__ == "__main__":
    unittest.main()
