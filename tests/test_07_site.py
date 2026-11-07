"""Test 7 — site content and filter wiring: index.json matches the exported
versions exactly, record pages exist for each, the no-JS table carries the
data attributes the JS filters use, and synthetic labels are everywhere."""
import json
import re
import unittest

try:
    from tests.util import (APPROVED_VERSIONS, fixture, run_cli,  # noqa: F401
                            site_page)
except ImportError:
    from util import (APPROVED_VERSIONS, fixture, run_cli,  # noqa: F401
                      site_page)


class SiteTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.index_html = site_page("index.html")
        cls.index_json = json.loads(site_page("index.json"))

    def test_index_json_covers_exactly_approved_versions(self):
        ids = {v["version_id"] for v in self.index_json["versions"]}
        self.assertEqual(ids, set(APPROVED_VERSIONS))

    def test_deep_link_page_per_version(self):
        for vid in APPROVED_VERSIONS:
            page = fixture().site_dir / "record" / f"{vid}.html"
            self.assertTrue(page.exists(), f"missing record page {vid}")

    def test_every_version_row_carries_filter_attributes(self):
        for vid in APPROVED_VERSIONS:
            m = re.search(
                rf'<tr data-version="{vid}"([^>]*)>',
                self.index_html)
            self.assertTrue(m, f"no table row for {vid}")
            attrs = m.group(1)
            for attr in ("data-country", "data-issuer-type", "data-function",
                         "data-area", "data-source-status", "data-search"):
                self.assertIn(attr, attrs, f"{vid}: missing {attr}")

    def test_table_attributes_agree_with_index_json(self):
        by_id = {v["version_id"]: v for v in self.index_json["versions"]}
        for vid in APPROVED_VERSIONS:
            m = re.search(rf'<tr data-version="{vid}"([^>]*)>',
                          self.index_html)
            attrs = dict(re.findall(r'(data-[\w-]+)="([^"]*)"', m.group(1)))
            v = by_id[vid]
            self.assertEqual(attrs["data-country"], v["country"])
            self.assertEqual(attrs["data-issuer-type"], v["issuer_type"])
            self.assertEqual(attrs["data-function"], v["function"])
            self.assertEqual(attrs["data-area"], v["area"])
            self.assertEqual(attrs["data-source-status"], v["source_status"])
            if v["adopted_year"]:
                self.assertEqual(attrs["data-year"], v["adopted_year"])

    def test_no_js_table_lists_all_versions_with_links(self):
        for vid in APPROVED_VERSIONS:
            self.assertIn(f'href="record/{vid}.html"', self.index_html)

    def test_bilingual_titles_in_index_json(self):
        by_id = {v["version_id"]: v for v in self.index_json["versions"]}
        titles = by_id["V-XA-0002"]["titles"]
        self.assertIn("de", titles)
        self.assertIn("en", titles)
        self.assertIn("Richtlinie", titles["de"])
        self.assertIn("Open Access Policy", titles["en"])

    def test_synthetic_labels_on_every_page(self):
        pages = ["index.html", "about.html"] + [
            f"record/{vid}.html" for vid in APPROVED_VERSIONS]
        for p in pages:
            html = site_page(p)
            self.assertIn("SYNTHETIC", html.upper(), f"{p} not labelled")

    def test_purposive_sampling_note_on_index_and_about(self):
        for p in ("index.html", "about.html"):
            html = site_page(p)
            self.assertIn("purposive", html.lower(), p)

    def test_record_page_has_citation_note_and_evidence(self):
        html = site_page("record/V-XA-0002.html")
        self.assertIn("cite", html.lower())
        self.assertIn("excerpt", html.lower())
        self.assertIn("§ 2 Abs. 1", html)  # physical anchor
        self.assertIn("example.org", html)  # source link

    def test_review_state_shown_on_record(self):
        html = site_page("record/V-XA-0002.html")
        self.assertIn("approved_public", html)

    def test_link_inventory_covers_all_public_urls(self):
        """pipeline/check_links.py must inventory every live and archived
        URL of the export (offline; the network --check run stays an
        opt-in maintenance step, plan test 12)."""
        import csv, tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "links.csv"
            res = run_cli(["pipeline/check_links.py",
                           "--export", str(fixture().export_dir),
                           "--report", str(report)])
            self.assertEqual(res.returncode, 0,
                             res.stdout + res.stderr)
            rows = list(csv.DictReader(open(report, newline="",
                                            encoding="utf-8")))
        urls = {r["url"] for r in rows}
        live = {r["url"] for r in rows if r["kind"] == "live_url"}
        archived = {r["url"] for r in rows if r["kind"] == "archived_url"}
        self.assertEqual(len(urls), 8)  # 4 manifestations x (live + archived)
        self.assertEqual(len(live), 4)
        self.assertEqual(len(archived), 4)
        for r in rows:
            self.assertEqual(r["http_result"], "not_checked")  # offline

    def test_data_files_published_with_manifest(self):
        for f in ["countries.csv", "organizations.csv",
                  "policy_families.csv", "policy_versions.csv",
                  "manifestations.csv", "provisions.csv",
                  "version_relationships.csv", "texts.csv",
                  "version_functions.csv", "manifest.json"]:
            self.assertTrue((fixture().site_dir / "data" / f).exists(), f)


if __name__ == "__main__":
    unittest.main()
