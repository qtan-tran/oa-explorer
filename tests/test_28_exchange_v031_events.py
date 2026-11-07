"""Test 28 — v0.3.1: published and promulgated are different source
events.

CO Resolution 0777 (synthetic model): effective on publication →
publication_linked; signed 2022-08-03; published in Diario Oficial
52.243 dated 2022-12-09; effective provisionally 2022-12-09 with the
gazette-mirror caveat. BRIN Regulation 12/2023 (synthetic model):
explicitly in force on promulgation → promulgation_linked. If both
event dates disagree, both are preserved and the effective date is
chosen only from the original's explicit trigger; conflict if unclear.
"""
import sys
import unittest

try:
    from tests.util import (load_exchange_v031_doc,
                            load_exchange_v031_schema)
except ImportError:  # pragma: no cover
    from util import (load_exchange_v031_doc, load_exchange_v031_schema)

REPO = sys.path[0] if sys.path[0] else "."
sys.path.insert(0, REPO + "/pipeline" if not REPO.endswith("pipeline")
                else REPO)
import exchange_v03_lib as x3  # noqa: E402


def validate(doc):
    return x3.validate_v03(doc, load_exchange_v031_schema())


def find_version(doc, vid):
    return next(v for v in doc["versions"] if v["id"] == vid)


def claim_of(version, ctype):
    return next(c for c in version["dates"] if c["type"] == ctype)


class FixtureValid(unittest.TestCase):
    def test_v031_fixture_passes_with_zero_errors(self):
        errors, warnings, notes = validate(load_exchange_v031_doc())
        self.assertEqual(errors, [], errors)


class PublicationVsPromulgation(unittest.TestCase):
    def test_co_resolution_is_publication_linked(self):
        v = find_version(load_exchange_v031_doc(), "V-CO-RES-0777-2022")
        self.assertEqual(v["effective_date_interpretation"],
                         "publication_linked")
        pub = claim_of(v, "published")
        self.assertEqual(pub["value"], "2022-12-09")
        self.assertEqual(pub["physical_anchor"],
                         "Diario Oficial, edición 52.243")
        self.assertEqual(claim_of(v, "adopted")["value"], "2022-08-03")

    def test_co_effective_provisional_with_gazette_mirror_caveat(self):
        doc = load_exchange_v031_doc()
        v = find_version(doc, "V-CO-RES-0777-2022")
        eff = x3.resolve_effective_v03(v, schema_version="0.3.1-draft")
        self.assertEqual(eff.value, "2022-12-09")
        self.assertEqual(eff.basis, "in force on publication")
        # provisional: the gazette date is issuer_attested via mirror
        self.assertEqual(eff.status, "issuer_attested")
        self.assertIn("2022-12-09 (in force on publication)",
                      x3.effective_display_v03(eff))

    def test_brin_regulation_is_promulgation_linked(self):
        doc = load_exchange_v031_doc()
        v = find_version(doc, "V-ID-BRIN-12-2023")
        self.assertEqual(v["effective_date_interpretation"],
                         "promulgation_linked")
        eff = x3.resolve_effective_v03(v, schema_version="0.3.1-draft")
        self.assertEqual(eff.value, "2023")
        self.assertEqual(eff.basis, "in force on promulgation")
        # promulgation_linked must NOT derive from a published claim
        v2 = find_version(load_exchange_v031_doc(), "V-CO-RES-0777-2022")
        v2["effective_date_interpretation"] = "promulgation_linked"
        eff2 = x3.resolve_effective_v03(v2, schema_version="0.3.1-draft")
        self.assertIsNone(eff2.value)

    def test_disagreeing_event_dates_with_explicit_trigger_preserved(self):
        doc = load_exchange_v031_doc()
        v = find_version(doc, "V-CO-RES-0777-2022")
        v["dates"].append({
            "type": "promulgated", "value": "2022-12-20",
            "precision": "day", "status": "issuer_attested",
            "note": "conflicting promulgation event date, preserved"})
        errors, warnings, notes = validate(doc)
        self.assertEqual([e for e in errors if "disagree" in e], [],
                         errors)
        self.assertTrue(any("both preserved" in n and
                            "publication_linked" in n for n in notes),
                        notes)
        # effective still derives only from the explicit trigger
        eff = x3.resolve_effective_v03(v, schema_version="0.3.1-draft")
        self.assertEqual(eff.value, "2022-12-09")
        self.assertEqual(eff.basis, "in force on publication")

    def test_disagreeing_event_dates_with_unclear_trigger_conflict(self):
        doc = load_exchange_v031_doc()
        v = find_version(doc, "V-CO-RES-0777-2022")
        v["dates"].append({
            "type": "promulgated", "value": "2022-12-20",
            "precision": "day", "status": "issuer_attested"})
        v["effective_date_interpretation"] = "unknown"
        errors, _, _ = validate(doc)
        self.assertTrue(any("disagree" in e and "unclear" in e
                            for e in errors), errors)

    def test_publication_linked_needs_a_published_claim(self):
        doc = load_exchange_v031_doc()
        v = find_version(doc, "V-ID-BRIN-12-2023")
        v["effective_date_interpretation"] = "publication_linked"
        errors, _, _ = validate(doc)
        self.assertTrue(any("publication_linked" in e and "published" in e
                            for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
