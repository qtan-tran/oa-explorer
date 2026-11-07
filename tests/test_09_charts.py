"""Test 9 — charts and denominators: the overview chart counts exactly the
exported versions, the denominator is stated next to it, excluded strata
are named, and no ranking/composite messaging appears."""
import json
import re
import unittest

try:
    from tests.util import APPROVED_VERSIONS, fixture, site_page  # noqa: F401
except ImportError:
    from util import APPROVED_VERSIONS, fixture, site_page  # noqa: F401


class ChartTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.html = site_page("index.html")
        cls.data = json.loads(site_page("index.json"))

    def test_denominator_equals_exported_versions(self):
        self.assertIn(f"n = {len(APPROVED_VERSIONS)}", self.html)
        self.assertEqual(len(self.data["versions"]), len(APPROVED_VERSIONS))

    def test_chart_counts_match_index_json(self):
        counts: dict[str, int] = {}
        for v in self.data["versions"]:
            counts[v["country"]] = counts.get(v["country"], 0) + 1
        for country, n in counts.items():
            # the svg must mention each bar's count
            self.assertRegex(
                self.html,
                rf"{country}[^<]*</text>|{n}",
                f"country {country} missing from chart")
        self.assertEqual(sum(counts.values()), len(APPROVED_VERSIONS))

    def test_chart_title_and_desc_state_the_denominator(self):
        svg = re.search(r"<svg\b.*?</svg>", self.html, re.S).group(0)
        self.assertRegex(svg, r'<title id="chart-title">')
        desc = re.search(r"<desc id=\"chart-desc\">(.*?)</desc>", svg, re.S)
        self.assertTrue(desc, "chart has no desc")
        counts = {}
        for v in self.data["versions"]:
            counts[v["country"]] = counts.get(v["country"], 0) + 1
        for country, n in counts.items():
            self.assertIn(f"{country}: {n} version", desc.group(1))

    def test_limitations_note_names_excluded_strata(self):
        self.assertIn("Excluded from this chart", self.html)
        self.assertRegex(self.html, r"not approved for\s+publication")
        self.assertIn("screening", self.html)

    def test_purposive_sample_disclaimer_next_to_chart(self):
        self.assertIn("purposive sample", self.html)
        self.assertIn("never a census", self.html)

    def test_no_country_ranking_language(self):
        text = re.sub(r"<[^>]+>", " ", self.html)
        text = re.sub(r"\s+", " ", text)
        for phrase in ("ranked", "ranks first", "leading country",
                       "best country", "top country"):
            self.assertNotIn(phrase.lower(), text.lower(),
                             f"ranking language: {phrase}")

    def test_composite_only_as_descriptive_profile(self):
        """The composite score appears only inside the record's own profile
        table, never as a site-level comparison or league table."""
        text = re.sub(r"<[^>]+>", " ", self.html)
        self.assertNotIn("composite", text.lower(),
                         "composite must not appear on the index page")
        record = site_page("record/V-XA-0002.html")
        self.assertIn("never aggregated into a ranking", record)

    def test_chart_is_svg_with_accessible_names(self):
        svg = re.search(r"<svg\b.*?</svg>", self.html, re.S).group(0)
        self.assertIn('role="img"', svg)
        self.assertIn("<title", svg)
        self.assertIn("<desc", svg)


if __name__ == "__main__":
    unittest.main()
