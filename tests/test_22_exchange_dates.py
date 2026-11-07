"""Test 22 — exchange v0.2 typed date semantics.

The four QC-driven scenarios:
1. call-opened cohort (2021-01-01) with NO inferred general effective
   date — display stays "Unknown / not established";
2. dual award cohorts (bounded legacy + open-ended 2027) alongside
   each other, still no general effective date;
3. effective-on-promulgation (adopted != promulgated != effective);
4. signed approval resolution linked to an annex.

Plus precision/value invariants, webpage modification (published vs
retrieved) and cohort bound checks.
"""
import copy
import sys
import unittest

try:
    from tests.util import load_exchange_doc, load_exchange_schema
except ImportError:  # pragma: no cover
    from util import load_exchange_doc, load_exchange_schema

REPO = sys.path[0] if sys.path[0] else "."
sys.path.insert(0, REPO + "/pipeline" if not REPO.endswith("pipeline")
                else REPO)
import exchange_lib as xl  # noqa: E402


def date_errors(doc):
    errors, warnings = [], []
    xl.validate_date_semantics(doc, errors, warnings)
    return errors


def find_version(doc, vid):
    return next(v for v in doc["versions"] if v["id"] == vid)


def claim_of(version, ctype):
    return next(c for c in version["dates"] if c["type"] == ctype)


class CohortIsNotEffective(unittest.TestCase):
    """Scenario 1: funder terms with a call-opened cohort."""

    def test_cohort_start_is_not_resolved_as_effective(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-ARC-GRANT-2020")
        eff = xl.resolve_effective(v)
        self.assertIsNone(eff.value)
        self.assertEqual(xl.effective_display(eff),
                         "Unknown / not established")

    def test_display_never_uses_cohort_threshold(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-ARC-GRANT-2020")
        self.assertEqual(v["cohorts"][0]["start"]["value"], "2021-01-01")
        eff = xl.resolve_effective(v)
        self.assertNotIn("2021", xl.effective_display(eff))

    def test_inferred_effective_from_cohort_is_rejected(self):
        # the exact mistake the contract must prevent: copying the
        # cohort start into a general effective claim under
        # cohort_only interpretation
        doc = load_exchange_doc()
        v = find_version(doc, "V-ARC-GRANT-2020")
        v["dates"].append({
            "type": "effective", "value": "2021-01-01",
            "precision": "day", "status": "inferred",
        })
        errors, warnings = xl.validate_exchange(doc,
                                                load_exchange_schema())
        self.assertTrue(any("cohort_only" in e and "threshold" in e
                            for e in errors), errors)


class DualAwardCohorts(unittest.TestCase):
    """Scenario 2: dual award cohorts - an open-ended 2027
    cohort next to its bounded predecessor cohort."""

    def test_both_cohorts_present_and_distinct(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-BOR-TRI-2026")
        by_id = {c["id"]: c for c in v["cohorts"]}
        self.assertIn("C-BOR-TRI-LEGACY", by_id)
        self.assertIn("C-BOR-TRI-2027", by_id)
        self.assertEqual(by_id["C-BOR-TRI-LEGACY"]["start"]["value"],
                         "2015-05-01")
        self.assertEqual(by_id["C-BOR-TRI-LEGACY"]["end"]["value"],
                         "2026-12-31")
        self.assertEqual(by_id["C-BOR-TRI-2027"]["start"]["value"],
                         "2027-01-01")
        self.assertIsNone(by_id["C-BOR-TRI-2027"]["end"]["value"])

    def test_still_no_general_effective_date(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-BOR-TRI-2026")
        self.assertEqual(v["effective_date_interpretation"], "cohort_only")
        eff = xl.resolve_effective(v)
        self.assertIsNone(eff.value)
        self.assertEqual(xl.effective_display(eff),
                         "Unknown / not established")

    def test_open_ended_cohort_needs_unknown_precision_end(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-BOR-TRI-2026")
        c = next(c for c in v["cohorts"] if c["id"] == "C-BOR-TRI-2027")
        c["end"]["precision"] = "day"  # value still null
        self.assertTrue(any("open ended" in e for e in date_errors(doc)))

    def test_cohort_without_start_value_rejected(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-BOR-TRI-2026")
        c = next(c for c in v["cohorts"] if c["id"] == "C-BOR-TRI-2027")
        c["start"]["value"] = None
        self.assertTrue(any("no start value" in e for e in date_errors(doc)))


class EffectiveOnPromulgation(unittest.TestCase):
    """Scenario 3: regulation in force on promulgation."""

    def test_effective_resolves_from_promulgation(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-BOR-BNRA-012-2023")
        eff = xl.resolve_effective(v)
        self.assertEqual(eff.value, "2023-10-17")
        self.assertIn("promulgation", eff.basis)
        self.assertEqual(xl.effective_display(eff),
                         "2023-10-17 (in force on promulgation)")

    def test_adopted_promulgated_effective_all_distinct(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-BOR-BNRA-012-2023")
        adopted = claim_of(v, "adopted")["value"]
        promulgated = claim_of(v, "promulgated")["value"]
        self.assertEqual(adopted, "2023-10-09")
        self.assertEqual(promulgated, "2023-10-17")
        self.assertNotEqual(adopted, promulgated)
        # the effective CLAIM itself stays empty (value null, unknown):
        # the derivation is declared, not silently stored
        eff_claim = claim_of(v, "effective")
        self.assertIsNone(eff_claim["value"])
        self.assertEqual(eff_claim["precision"], "unknown")

    def test_promulgation_linked_conflicts_with_explicit_claim(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-BOR-BNRA-012-2023")
        v["dates"].append({
            "type": "effective", "value": "2023-10-20",
            "precision": "day", "status": "verified",
        })
        errors = date_errors(doc)
        self.assertTrue(any("conflicts with an explicit" in e
                            for e in errors), errors)

    def test_linked_interpretation_requires_source_claim(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-BOR-BNRA-012-2023")
        claim_of(v, "promulgated")["value"] = None
        claim_of(v, "promulgated")["precision"] = "unknown"
        self.assertTrue(any("no valued promulgated claim" in e
                            for e in date_errors(doc)))


class ResolutionAndAnnex(unittest.TestCase):
    """Scenario 4: signed approval resolution linked to an annex."""

    def test_annex_component_of_resolution(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-BOR-NOS-2022")
        self.assertEqual(v["authority_status"], "approved")
        res = next(m for m in doc["manifestations"]
                   if m["id"] == "M-BOR-NOS-RES")
        annex = next(m for m in doc["manifestations"]
                     if m["id"] == "M-BOR-NOS-ANNEX")
        self.assertEqual(annex["component_of_manifestation_id"],
                         res["id"])
        self.assertEqual(annex["role"], "ancillary")
        self.assertEqual(res["version_id"], annex["version_id"])

    def test_approved_claim_unknown_until_resolution_verified(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-BOR-NOS-2022")
        approved = claim_of(v, "approved")
        self.assertIsNone(approved["value"])
        self.assertEqual(approved["status"], "unreviewed")
        # adopted stays attested and separate from approved
        adopted = claim_of(v, "adopted")
        self.assertEqual(adopted["value"], "2022-08-03")
        self.assertEqual(adopted["status"], "issuer_attested")


class PrecisionAndModification(unittest.TestCase):
    def test_precision_unknown_requires_null_value(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-MAR-OA-2011")
        claim_of(v, "effective")["value"] = "2011-03-23"
        self.assertTrue(any("precision unknown but a value" in e
                            for e in date_errors(doc)))

    def test_value_must_match_precision(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-BOR-TRI-2026")
        pub = claim_of(v, "published")
        pub["precision"] = "day"  # value stays "2026"
        self.assertTrue(any("does not match precision" in e
                            for e in date_errors(doc)))

    def test_webpage_modification_distinct_from_publication(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-ARC-ANN-2020")
        published = claim_of(v, "published")
        retrieved = claim_of(v, "retrieved")
        self.assertEqual(published["value"], "2020-11-02")
        self.assertEqual(retrieved["value"], "2026-10-05")
        self.assertNotEqual(published["value"], retrieved["value"])
        # capture date also sits on the manifestation
        m = next(m for m in doc["manifestations"]
                 if m["id"] == "M-ARC-ANN-2020-HTML")
        self.assertEqual(m["role"], "issuer_html_capture")
        self.assertEqual(m["retrieved_at"], "2026-10-05")

    def test_two_valued_effective_claims_rejected(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-BOR-REPO-2016")
        v["dates"].append(copy.deepcopy(claim_of(v, "effective")))
        self.assertTrue(any("at most one is unambiguous" in e
                            for e in date_errors(doc)))

    def test_explicit_interpretation_needs_valued_claim(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-BOR-REPO-2016")
        claim_of(v, "effective")["value"] = None
        claim_of(v, "effective")["precision"] = "unknown"
        self.assertTrue(any("'explicit'" in e and
                            "no valued effective claim" in e
                            for e in date_errors(doc)))

    def test_explicit_effective_contrast_case(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-BOR-REPO-2016")
        eff = xl.resolve_effective(v)
        self.assertEqual(eff.value, "2016-03-01")
        self.assertEqual(xl.effective_display(eff), "2016-03-01")
        adopted = claim_of(v, "adopted")["value"]
        self.assertNotEqual(adopted, eff.value)


if __name__ == "__main__":
    unittest.main()
