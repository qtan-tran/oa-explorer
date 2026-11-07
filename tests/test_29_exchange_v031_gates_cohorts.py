"""Test 29 — v0.3.1: public archive-link gate, unknown-start cohorts,
and the attested-but-unrecovered UPTC Agreement 2/2026 lead.

- A public archive link requires a verified snapshot (contents/date)
  PLUS separate link-rights/review gates; a bare archived_url or a
  url_only snapshot stays internal.
- Unknown-start cohorts are not valid from negative infinity and are
  excluded from definite date-filtered claims; a supported unbounded
  end (not_applicable) is distinct from an unknown end.
- UPTC 2/2026: issuer news dates adoption to 2026-01-29, but no signed
  PDF/annex, effective date, physical clause or hash is verified — it
  stays out of the main-version comparison and public document views.
"""
import json
import sys
import unittest

try:
    from tests.util import load_exchange_v031_doc
except ImportError:  # pragma: no cover
    from util import load_exchange_v031_doc

REPO = sys.path[0] if sys.path[0] else "."
sys.path.insert(0, REPO + "/pipeline" if not REPO.endswith("pipeline")
                else REPO)
import exchange_v03_lib as x3  # noqa: E402


def find_version(doc, vid):
    return next(v for v in doc["versions"] if v["id"] == vid)


def find_man(doc, mid):
    return next(m for m in doc["manifestations"] if m["id"] == mid)


def public_views(doc):
    doc["release"]["public_release_approved"] = True
    for v in doc["versions"]:
        if v["review"]["state"] in ("provisionally_reviewed", "conflicted"):
            v["review"]["state"] = "analyst_checked"
    for m in doc["manifestations"]:
        if m["review"]["state"] != "analyst_checked":
            m["review"]["state"] = "analyst_checked"
    return x3.build_public_views_v03(doc, x3.PublicConfigV03())


class PublicArchiveLinkGate(unittest.TestCase):
    def test_verified_bytes_plus_gates_makes_public_link(self):
        doc = load_exchange_v031_doc()
        m = find_man(doc, "M-UCT-2020-PDF")
        self.assertEqual(x3.public_archive_link(m),
                         "https://archive.example.org/snap/uct-repo-policy-2020")

    def test_url_only_snapshot_never_public(self):
        doc = load_exchange_v031_doc()
        brin = find_man(doc, "M-ID-BRIN-12-2023-HTML")
        self.assertIsNotNone(brin["archived_url"])  # bare archived_url
        self.assertEqual(brin["archive_snapshots"][0]["capture_status"],
                         "url_only")
        self.assertIsNone(x3.public_archive_link(brin))
        co = find_man(doc, "M-CO-0777-RES-MIRROR")
        self.assertIsNone(co["archived_url"])  # url_only snapshot only
        self.assertIsNone(x3.public_archive_link(co))

    def test_issuer_attested_snapshot_not_public(self):
        doc = load_exchange_v031_doc()
        m = find_man(doc, "M-UCT-2014-HTML")
        self.assertIsNone(x3.public_archive_link(m))

    def test_rights_gate_blocks_public_archive_link(self):
        doc = load_exchange_v031_doc()
        m = find_man(doc, "M-UCT-2020-PDF")
        m["rights_status"] = "internal_only"
        self.assertIsNone(x3.public_archive_link(m))

    def test_review_gate_blocks_public_archive_link(self):
        doc = load_exchange_v031_doc()
        m = find_man(doc, "M-UCT-2020-PDF")
        m["review"]["state"] = "unreviewed"
        self.assertIsNone(x3.public_archive_link(m))

    def test_views_expose_only_verified_archive_links(self):
        doc = load_exchange_v031_doc()
        views = public_views(doc)
        blob = json.dumps(views)
        self.assertIn("uct-repo-policy-2020", blob)   # verified_bytes
        self.assertNotIn("id-brin-12-2023", blob)     # url_only
        self.assertNotIn("co-res0777", blob)          # url_only
        self.assertNotIn("uct-repo-policy\"", blob)   # issuer_attested only


class UnknownStartCohorts(unittest.TestCase):
    def test_unknown_start_is_not_negative_infinity(self):
        doc = load_exchange_v031_doc()
        v = find_version(doc, "V-CO-UPTC-2-2026")
        co = v["cohorts"][0]
        self.assertFalse(x3.cohort_definite_start(co))
        self.assertEqual(x3.cohorts_with_definite_start(v), [])

    def test_unknown_start_excluded_from_definite_claims(self):
        doc = load_exchange_v031_doc()
        v = find_version(doc, "V-CO-RES-0777-2022")
        self.assertEqual([c["id"] for c in x3.cohorts_with_definite_start(v)],
                         ["C-CO-0777-AWARD"])

    def test_unbounded_end_vs_unknown_end(self):
        doc = load_exchange_v031_doc()
        co = find_version(doc, "V-CO-RES-0777-2022")["cohorts"][0]
        uptc = find_version(doc, "V-CO-UPTC-2-2026")["cohorts"][0]
        self.assertEqual(x3.cohort_end_kind(co), "unbounded_supported")
        self.assertEqual(x3.cohort_end_kind(uptc), "unknown")

    def test_end_null_with_verified_status_is_error(self):
        from tests.util import load_exchange_v031_schema
        doc = load_exchange_v031_doc()
        co = find_version(doc, "V-CO-RES-0777-2022")["cohorts"][0]
        co["end"]["status"] = "verified"
        errors, _, _ = x3.validate_v03(doc, load_exchange_v031_schema())
        self.assertTrue(any("not_applicable" in e for e in errors), errors)


class UptcUnrecoveredLead(unittest.TestCase):
    def test_attested_but_unrecovered(self):
        doc = load_exchange_v031_doc()
        v = find_version(doc, "V-CO-UPTC-2-2026")
        self.assertEqual(v["source_status"], "attested_unrecovered")
        self.assertEqual(v["authority_status"], "announcement_attested")
        adopted = next(c for c in v["dates"] if c["type"] == "adopted")
        self.assertEqual(adopted["value"], "2026-01-29")
        self.assertEqual(adopted["status"], "issuer_attested")
        self.assertEqual(v["effective_date_interpretation"], "unknown")
        m = find_man(doc, "M-UPTC-2-2026-LEAD")
        self.assertIsNone(m["sha256"])
        self.assertIsNone(m["retrieved_at"])
        self.assertEqual(m["role"], "unrecovered_lead")

    def test_excluded_from_comparison_eligible_versions(self):
        doc = load_exchange_v031_doc()
        ids = [v["id"] for v in x3.comparison_eligible_versions(doc)]
        self.assertNotIn("V-CO-UPTC-2-2026", ids)

    def test_excluded_from_public_views_even_when_approved(self):
        doc = load_exchange_v031_doc()
        views = public_views(doc)
        blob = json.dumps(views)
        self.assertNotIn("V-CO-UPTC-2-2026", blob)
        self.assertNotIn("uptc", blob.lower())

    def test_no_effective_date_inferred_for_lead(self):
        doc = load_exchange_v031_doc()
        v = find_version(doc, "V-CO-UPTC-2-2026")
        eff = x3.resolve_effective_v03(v, schema_version="0.3.1-draft")
        self.assertIsNone(eff.value)
        self.assertEqual(x3.effective_display_v03(eff),
                         "Unknown / not established")


if __name__ == "__main__":
    unittest.main()
