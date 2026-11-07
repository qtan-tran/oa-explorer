"""Test 5 — permission and review filtering: no private marker may reach
the public export or the built site; non-approved records are excluded;
not-permitted excerpts are blanked while links survive; unrecovered sources
are summarized, never linked; every exported column is allowlisted."""
import unittest

try:
    from tests.util import (APPROVED_VERSIONS, CANARY, CONTRACT,
                            NOT_PERMITTED_PROVISION, REPO,
                            UNRECOVERED_MANIFESTATION, WITHHELD_ORG,
                            WITHHELD_VERSION, fixture, read_csv,
                            read_csv_by_id, scan_tree_for)
except ImportError:
    from util import (APPROVED_VERSIONS, CANARY, CONTRACT,
                      NOT_PERMITTED_PROVISION, REPO,
                      UNRECOVERED_MANIFESTATION, WITHHELD_ORG,
                      WITHHELD_VERSION, fixture, read_csv,
                      read_csv_by_id, scan_tree_for)
import csv


class PermissionTests(unittest.TestCase):

    def test_canary_absent_from_public_export(self):
        hits = scan_tree_for(fixture().export_dir, CANARY)
        self.assertEqual(hits, [])

    def test_canary_absent_from_built_site(self):
        hits = scan_tree_for(fixture().site_dir, CANARY)
        self.assertEqual(hits, [])

    def test_draft_version_excluded_everywhere(self):
        rows = read_csv_by_id(fixture().export_dir / "policy_versions.csv",
                              "version_id")
        self.assertNotIn(WITHHELD_VERSION, rows)
        ids = {r["version_id"] for r in
               read_csv(fixture().export_dir / "policy_versions.csv")}
        self.assertEqual(ids, set(APPROVED_VERSIONS))
        self.assertFalse((fixture().site_dir / "record" /
                          f"{WITHHELD_VERSION}.html").exists())

    def test_unreviewed_organization_excluded(self):
        rows = read_csv_by_id(fixture().export_dir / "organizations.csv",
                              "org_id")
        self.assertNotIn(WITHHELD_ORG, rows)

    def test_unrecovered_manifestation_excluded_but_summarized(self):
        rows = read_csv_by_id(fixture().export_dir / "manifestations.csv",
                              "manifestation_id")
        self.assertNotIn(UNRECOVERED_MANIFESTATION, rows)
        v = read_csv_by_id(fixture().export_dir / "policy_versions.csv",
                           "version_id")["V-XB-0001"]
        self.assertEqual(v["derived_manifestation_count"], "1")
        self.assertEqual(v["derived_manifestation_public_count"], "0")
        self.assertIn("unrecovered", v["derived_source_status_summary"])

    def test_unrecovered_source_never_linked_on_site(self):
        html = (fixture().site_dir / "record" / "V-XB-0001.html"
                ).read_text(encoding="utf-8")
        self.assertNotIn(UNRECOVERED_MANIFESTATION, html)
        self.assertNotIn("http://private", html)
        self.assertIn("none publicly accessible", html)

    def test_not_permitted_excerpt_blanked_but_source_link_present(self):
        p = read_csv_by_id(fixture().export_dir / "provisions.csv",
                           "provision_id")[NOT_PERMITTED_PROVISION]
        self.assertEqual(p["excerpt_text"], "")
        self.assertEqual(p["excerpt_value_state"], "not_applicable")
        # the manifestation carrying the provision is still public
        m = read_csv_by_id(fixture().export_dir / "manifestations.csv",
                           "manifestation_id")
        self.assertIn(p["manifestation_id"], m)

    def test_every_exported_column_is_allowlisted(self):
        with open(CONTRACT / "public_allowlist.csv", newline="",
                  encoding="utf-8") as fh:
            allow = {}
            for r in csv.DictReader(fh):
                allow.setdefault(r["entity"], set()).add(r["field"])
        for entity, fname in [("country", "countries.csv"),
                              ("organization", "organizations.csv"),
                              ("policy_family", "policy_families.csv"),
                              ("policy_version", "policy_versions.csv"),
                              ("manifestation", "manifestations.csv"),
                              ("provision", "provisions.csv"),
                              ("version_relationship",
                               "version_relationships.csv"),
                              ("text", "texts.csv"),
                              ("version_function", "version_functions.csv")]:
            with open(fixture().export_dir / fname, newline="",
                      encoding="utf-8") as fh:
                cols = next(csv.reader(fh))
            extra = [c for c in cols if c not in allow[entity]]
            self.assertEqual(extra, [],
                             f"{fname}: non-allowlisted columns {extra}")

    def test_public_rows_all_approved_and_visible(self):
        for fname, key in [("countries.csv", "country_id"),
                           ("organizations.csv", "org_id"),
                           ("policy_families.csv", "family_id"),
                           ("policy_versions.csv", "version_id"),
                           ("manifestations.csv", "manifestation_id"),
                           ("provisions.csv", "provision_id"),
                           ("version_relationships.csv", "relationship_id"),
                           ("texts.csv", "entity_id"),
                           ("version_functions.csv", "version_id")]:
            for r in read_csv(fixture().export_dir / fname):
                self.assertEqual(r["review_state"], "approved_public",
                                f"{fname}: non-approved row {r[key]}")
                self.assertEqual(r["public_visible"], "true",
                                 f"{fname}: non-visible row {r[key]}")

    def test_export_manifest_records_counts_and_synthetic_flag(self):
        import json
        m = json.loads((fixture().export_dir / "manifest.json")
                       .read_text(encoding="utf-8"))
        self.assertTrue(m["contains_synthetic_records"])
        self.assertEqual(m["record_counts"]["policy_version"], len(APPROVED_VERSIONS))


if __name__ == "__main__":
    unittest.main()
