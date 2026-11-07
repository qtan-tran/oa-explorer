"""Test 6 — version relationships: edges render on both endpoints with
evidence, links resolve to real record pages, and the data layer rejects
cycles (covered fully in test 02; here we assert the rendered graph)."""
import unittest

try:
    from tests.util import fixture, read_csv, read_csv_by_id  # noqa: F401
except ImportError:
    from util import fixture, read_csv, read_csv_by_id  # noqa: F401


class RelationshipTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rel = read_csv(fixture().export_dir / "version_relationships.csv")
        cls.rel_by_id = read_csv_by_id(
            fixture().export_dir / "version_relationships.csv",
            "relationship_id")

    def test_replaces_edge_present_in_data(self):
        edges = {(r["from_version_id"], r["to_version_id"], r["type"])
                 for r in self.rel}
        self.assertIn(("V-XA-0002", "V-XA-0001", "replaces"), edges)

    def test_replaces_edge_renders_on_both_endpoints(self):
        for vid in ("V-XA-0001", "V-XA-0002"):
            html = (fixture().site_dir / "record" / f"{vid}.html"
                    ).read_text(encoding="utf-8")
            self.assertIn("replaces", html, f"edge missing on {vid}")
            self.assertIn("V-XA-0001", html)
            self.assertIn("V-XA-0002", html)
            # both pages state the direction
            self.assertTrue(
                "incoming" in html or "outgoing" in html,
                f"edge direction not stated on {vid}")

    def test_related_edge_between_borealia_versions(self):
        edges = {(r["from_version_id"], r["to_version_id"], r["type"])
                 for r in self.rel}
        self.assertIn(("V-XB-0002", "V-XB-0001", "related"), edges)
        for vid in ("V-XB-0001", "V-XB-0002"):
            html = (fixture().site_dir / "record" / f"{vid}.html"
                    ).read_text(encoding="utf-8")
            self.assertIn("related", html)

    def test_relationship_evidence_rendered(self):
        html = (fixture().site_dir / "record" / "V-XA-0002.html"
                ).read_text(encoding="utf-8")
        self.assertIn("ersetzt die Fassung von 2020", html)

    def test_all_relationship_links_resolve_to_real_pages(self):
        """Every related version mentioned on a record page must have a
        page (no dead deep links inside the relationship graph)."""
        import re
        for vid in ("V-XA-0001", "V-XA-0002", "V-XA-0003",
                    "V-XB-0001", "V-XB-0002"):
            html = (fixture().site_dir / "record" / f"{vid}.html"
                    ).read_text(encoding="utf-8")
            page_dir = fixture().site_dir / "record"
            for target in re.findall(r'href="([^"#]+\.html)"', html):
                resolved = (page_dir / target).resolve()
                self.assertTrue(resolved.exists(),
                                 f"{vid}: dead link {target}")

    def test_isolated_version_states_absence_explicitly(self):
        html = (fixture().site_dir / "record" / "V-XA-0003.html"
                ).read_text(encoding="utf-8")
        self.assertIn("No recorded relationships", html)


if __name__ == "__main__":
    unittest.main()
