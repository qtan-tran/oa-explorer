"""Test 31 — v0.3.2 structural rules: legacy enum rejection with
evidence-based migration, Q15 null-version binding, Q12 null issuer
type, Q13 as_of vs published_at, Q11 pagination anchor.
"""
import sys
import unittest

try:
    from tests.util import (load_exchange_v032_doc, load_exchange_v032_schema)
except ImportError:  # pragma: no cover
    from util import (load_exchange_v032_doc, load_exchange_v032_schema)

REPO = sys.path[0] if sys.path[0] else "."
sys.path.insert(0, REPO + "/pipeline" if not REPO.endswith("pipeline")
                else REPO)
import exchange_v03_lib as x3  # noqa: E402


def validate(doc):
    return x3.validate_v03(doc, load_exchange_v032_schema())


def find_version(doc, vid):
    return next(v for v in doc["versions"] if v["id"] == vid)


def find_man(doc, mid):
    return next(m for m in doc["manifestations"] if m["id"] == mid)


class FixtureValid(unittest.TestCase):
    def test_v032_fixture_passes_with_zero_errors(self):
        errors, _, _ = validate(load_exchange_v032_doc())
        self.assertEqual(errors, [], errors)

    def test_schema_version(self):
        self.assertEqual(load_exchange_v032_doc()["schema_version"],
                         "0.3.2-draft")


class LegacyEnumMigration(unittest.TestCase):
    """Removed enum values are rejected with evidence-based guidance,
    never silently re-mapped."""

    def test_announcement_attested_rejected(self):
        doc = load_exchange_v032_doc()
        find_version(doc, "V-XA-ATTESTED-2026")["authority_status"] = \
            "announcement_attested"
        errors, _, _ = validate(doc)
        self.assertTrue(any("announcement_attested" in e and
                            "attested_unrecovered" in e and
                            "never by string mapping" in e for e in errors),
                        errors)

    def test_draft_only_rejected(self):
        doc = load_exchange_v032_doc()
        find_version(doc, "V-XA-DRAFT-2024")["source_status"] = "draft_only"
        errors, _, _ = validate(doc)
        self.assertTrue(any("draft_only" in e and "original_recovered" in e
                            for e in errors), errors)

    def test_issuer_type_unreviewed_rejected(self):
        doc = load_exchange_v032_doc()
        doc["organizations"][0]["issuer_type"] = "unreviewed"
        errors, _, _ = validate(doc)
        self.assertTrue(any("issuer_type" in e and "null" in e
                            for e in errors), errors)


class Q15NullVersionBinding(unittest.TestCase):
    def test_family_lead_with_null_version_accepted(self):
        doc = load_exchange_v032_doc()
        m = find_man(doc, "M-XA-FAM-LEAD")
        self.assertIsNone(m["version_id"])
        self.assertEqual(m["role"], "unrecovered_lead")
        self.assertEqual(m["family_id"], "F-XA-LEAD")
        errors, _, _ = validate(doc)
        self.assertEqual(errors, [], errors)

    def test_controlling_original_with_null_version_fails(self):
        doc = load_exchange_v032_doc()
        m = find_man(doc, "M-XA-DRAFT-PDF")
        m["version_id"] = None
        m["family_id"] = "F-XA-DRAFT"
        errors, _, _ = validate(doc)
        self.assertTrue(any("only for role=unrecovered_lead" in e
                            for e in errors), errors)

    def test_null_version_lead_without_family_fails(self):
        doc = load_exchange_v032_doc()
        m = find_man(doc, "M-XA-FAM-LEAD")
        m["family_id"] = None
        errors, _, _ = validate(doc)
        self.assertTrue(any("requires family_id" in e for e in errors),
                        errors)

    def test_lead_cannot_carry_provision_evidence(self):
        doc = load_exchange_v032_doc()
        p = dict(doc["provisions"][0])
        p["id"] = "P-LEAD"
        p["version_id"] = "V-CO-RES-0777-2022"
        p["manifestation_id"] = "M-XA-FAM-LEAD"
        doc["provisions"].append(p)
        errors, _, _ = validate(doc)
        self.assertTrue(any("no version" in e or "not of" in e
                            for e in errors), errors)


class Q12NullIssuerType(unittest.TestCase):
    def test_null_issuer_type_with_unreviewed_identity(self):
        doc = load_exchange_v032_doc()
        o = next(o for o in doc["organizations"] if o["issuer_type"] is None)
        self.assertEqual(o["identity_review"]["state"], "unreviewed")
        errors, warnings, _ = validate(doc)
        self.assertEqual(errors, [], errors)
        self.assertFalse(any(o["id"] in w for w in warnings), warnings)

    def test_null_type_with_checked_identity_warns(self):
        doc = load_exchange_v032_doc()
        o = next(o for o in doc["organizations"] if o["issuer_type"] is None)
        o["identity_review"]["state"] = "analyst_checked"
        errors, warnings, _ = validate(doc)
        self.assertTrue(any(o["id"] in w and "identity_review" in w
                            for w in warnings), warnings)


class Q13ReleaseDates(unittest.TestCase):
    def test_as_of_preceding_published_at_ok(self):
        doc = load_exchange_v032_doc()
        doc["release"]["published_at"] = "2026-11-10T09:00:00Z"
        errors, _, _ = validate(doc)
        self.assertEqual([e for e in errors if "as_of" in e], [], errors)

    def test_as_of_after_published_at_fails(self):
        doc = load_exchange_v032_doc()
        doc["release"]["published_at"] = "2026-11-01T09:00:00Z"
        errors, _, _ = validate(doc)
        self.assertTrue(any("as_of" in e and "published_at" in e
                            for e in errors), errors)

    def test_published_at_null_until_published(self):
        doc = load_exchange_v032_doc()
        self.assertIsNone(doc["release"]["published_at"])
        self.assertFalse(doc["release"]["public_release_approved"])


class Q11Pagination(unittest.TestCase):
    def test_physical_count_vs_printed_label(self):
        doc = load_exchange_v032_doc()
        m = find_man(doc, "M-CO-0777-PDF")
        self.assertEqual(m["physical_pages"], 85)
        self.assertIn("printed p.53", m["pagination_note"])
        p = doc["provisions"][0]
        self.assertIn("physical p.56", p["anchor"])
        self.assertIn("printed p.53", p["anchor"])

    def test_anchor_with_printed_but_no_physical_warns(self):
        doc = load_exchange_v032_doc()
        doc["provisions"][0]["anchor"] = "printed p.53 (annex Meta 31)"
        errors, warnings, _ = validate(doc)
        self.assertEqual(errors, [], errors)
        self.assertTrue(any("physical page" in w for w in warnings),
                        warnings)

    def test_html_physical_pages_must_be_null(self):
        doc = load_exchange_v032_doc()
        find_man(doc, "M-XA-HTML-PAGE")["physical_pages"] = 4
        _, warnings, _ = validate(doc)
        self.assertTrue(any("null for HTML" in w for w in warnings),
                        warnings)


if __name__ == "__main__":
    unittest.main()
