"""Test 32 — the nine synthetic v0.3.2 scenarios.

1. draft PDF recovered (draft + original_recovered, orthogonal)
2. issuer-attested approved version with no operative bytes
3. en/fr issuer editions under one version vs a bilingual single file
4. 85-page PDF with physical p.56 / printed p.53 anchor
5. null-version family lead accepted; null version on controlling
   original fails (in test_31)
6. HTML capture with rights_status=unreviewed blocked from public
   content redistribution
7. public_release_approved=true does not clear an internal QC hold
8. release as_of preceding published_at (in test_31)
9. contradictory authority evidence routed to QC conflict
"""
import json
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


def approved_views(doc, qc_holds=None):
    doc["release"]["public_release_approved"] = True
    return x3.build_public_views_v03(doc, x3.PublicConfigV03(),
                                     qc_holds=qc_holds)


class Scenario1DraftPdfRecovered(unittest.TestCase):
    def test_draft_and_original_recovered_are_orthogonal(self):
        doc = load_exchange_v032_doc()
        v = find_version(doc, "V-XA-DRAFT-2024")
        self.assertEqual(v["authority_status"], "draft")
        self.assertEqual(v["source_status"], "original_recovered")
        m = find_man(doc, "M-XA-DRAFT-PDF")
        self.assertEqual(m["role"], "controlling_original")
        self.assertEqual(m["format"], "pdf")
        self.assertIsNotNone(m["sha256"])
        errors, _, _ = validate(doc)
        self.assertEqual(errors, [], errors)


class Scenario2AttestedApprovedNoBytes(unittest.TestCase):
    def test_approved_plus_attested_unrecovered_with_caveat(self):
        doc = load_exchange_v032_doc()
        v = find_version(doc, "V-XA-ATTESTED-2026")
        self.assertEqual(v["authority_status"], "approved")
        self.assertEqual(v["source_status"], "attested_unrecovered")
        self.assertIn("caveat", v["review"]["note"])
        m = find_man(doc, "M-XA-ATT-LEAD")
        self.assertIsNone(m["sha256"])
        # bound to its registered version, not null (Q15)
        self.assertEqual(m["version_id"], "V-XA-ATTESTED-2026")
        errors, warnings, _ = validate(doc)
        self.assertEqual(errors, [], errors)
        self.assertFalse(any(v["id"] in w for w in warnings), warnings)

    def test_missing_caveat_warns(self):
        doc = load_exchange_v032_doc()
        v = find_version(doc, "V-XA-ATTESTED-2026")
        v["review"]["note"] = None
        _, warnings, _ = validate(doc)
        self.assertTrue(any("caveat" in w for w in warnings), warnings)

    def test_excluded_from_comparison_and_public(self):
        doc = load_exchange_v032_doc()
        ids = [v["id"] for v in x3.comparison_eligible_versions(doc)]
        self.assertNotIn("V-XA-ATTESTED-2026", ids)
        views = approved_views(doc)
        self.assertNotIn("V-XA-ATTESTED-2026", json.dumps(views))


class Scenario3Bilingual(unittest.TestCase):
    def test_editions_are_two_manifestations_one_version(self):
        doc = load_exchange_v032_doc()
        v = find_version(doc, "V-XA-BIL-ED-2023")
        self.assertEqual(sorted(v["languages"]), ["en", "fr"])
        mans = [m for m in doc["manifestations"]
                if m["version_id"] == v["id"]]
        self.assertEqual(len(mans), 2)
        self.assertEqual({tuple(m["languages"]) for m in mans},
                         {("en",), ("fr",)})
        self.assertEqual(len({m["version_id"] for m in mans}), 1)
        errors, _, _ = validate(doc)
        self.assertEqual(errors, [], errors)

    def test_bilingual_single_file_one_manifestation(self):
        doc = load_exchange_v032_doc()
        v = find_version(doc, "V-XA-BIL-SF-2023")
        mans = [m for m in doc["manifestations"]
                if m["version_id"] == v["id"]]
        self.assertEqual(len(mans), 1)
        self.assertEqual(sorted(mans[0]["languages"]), ["en", "fr"])

    def test_manifestation_language_outside_version_warns(self):
        doc = load_exchange_v032_doc()
        find_man(doc, "M-XA-BIL-EN")["languages"] = ["en", "de"]
        _, warnings, _ = validate(doc)
        self.assertTrue(any("not present in version" in w for w in warnings),
                        warnings)


class Scenario4Pagination(unittest.TestCase):
    def test_85_page_pdf_physical_printed_anchor(self):
        doc = load_exchange_v032_doc()
        m = find_man(doc, "M-CO-0777-PDF")
        self.assertEqual(m["physical_pages"], 85)
        p = doc["provisions"][0]
        self.assertTrue(p["anchor"].startswith("physical p.56"))
        self.assertIn("printed p.53", p["anchor"])
        v = find_version(doc, "V-CO-RES-0777-2022")
        eff = x3.resolve_effective_v03(v, schema_version="0.3.2-draft")
        self.assertEqual((eff.value, eff.basis), ("2022-12-09",
                                                   "in force on publication"))


class Scenario6HtmlRightsDefault(unittest.TestCase):
    def test_unreviewed_html_capture_blocked_from_public(self):
        doc = load_exchange_v032_doc()
        m = find_man(doc, "M-XA-HTML-PAGE")
        self.assertEqual(m["role"], "issuer_html_capture")
        self.assertEqual(m["rights_status"], "unreviewed")
        self.assertEqual(m["review"]["state"], "analyst_checked")
        views = approved_views(doc)
        blob = json.dumps(views)
        self.assertNotIn("M-XA-HTML-PAGE", blob)
        self.assertNotIn("notice-2026", blob)

    def test_html_capture_can_never_be_redistribution_approved(self):
        doc = load_exchange_v032_doc()
        find_man(doc, "M-XA-HTML-PAGE")["rights_status"] = \
            "public_redistribution_approved"
        errors, _, _ = validate(doc)
        self.assertTrue(any("never" in e and "link-only" in e
                            for e in errors), errors)

    def test_link_only_requires_affirmative_review(self):
        doc = load_exchange_v032_doc()
        m = find_man(doc, "M-XA-HTML-PAGE")
        m["rights_status"] = "link_only_approved"
        m["review"]["state"] = "provisionally_reviewed"
        _, warnings, _ = validate(doc)
        self.assertTrue(any("affirmative decision" in w for w in warnings),
                        warnings)


class Scenario7QcHoldVsReleaseApproval(unittest.TestCase):
    def test_release_approval_does_not_clear_internal_hold(self):
        doc = load_exchange_v032_doc()
        holds = {"V-XA-DRAFT-2024"}  # internal QC hold (local-only workbook)
        views = approved_views(doc, qc_holds=holds)
        blob = json.dumps(views)
        self.assertNotIn("V-XA-DRAFT-2024", blob)
        record = next((r for r in views["records"]
                       if r["id"] == "V-XA-BIL-ED-2023"), None)
        self.assertIsNotNone(record)  # non-held versions still visible
        # the hold flag itself is never exported
        self.assertNotIn("hold", blob.lower().replace("withheld", ""))

    def test_without_hold_the_version_is_visible_when_approved(self):
        doc = load_exchange_v032_doc()
        views = approved_views(doc)
        ids = [r["id"] for r in views["records"]]
        self.assertIn("V-XA-DRAFT-2024", ids)


class Scenario9AuthorityContradiction(unittest.TestCase):
    def test_contradiction_routed_to_qc_conflict(self):
        doc = load_exchange_v032_doc()
        v = find_version(doc, "V-XA-DRAFT-2024")
        v["authority_status"] = "approved"  # evidence says draft PDF
        errors, _, _ = validate(doc)
        self.assertTrue(any("QC conflict" in e and "never silently" in e
                            for e in errors), errors)


class ScoresStayUnpopulated(unittest.TestCase):
    def test_no_numeric_ten_score_fields(self):
        doc = load_exchange_v032_doc()
        self.assertEqual(len(doc["score_definitions"]), 1)
        for o in doc["score_observations"]:
            self.assertIsNone(o["value"])
        views = approved_views(doc)
        self.assertEqual(views["score_observations"]["shown"], 0)


if __name__ == "__main__":
    unittest.main()
