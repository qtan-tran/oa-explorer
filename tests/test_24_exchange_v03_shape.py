"""Test 24 — exchange v0.3 shape and decision-level validation.

The synthetic v0.3 fixture must pass full validation with zero errors;
targeted mutations of each of the six design decisions must fail.
"""
import sys
import unittest

try:
    from tests.util import (load_exchange_v03_doc,
                            load_exchange_v03_schema)
except ImportError:  # pragma: no cover
    from util import (load_exchange_v03_doc, load_exchange_v03_schema)

REPO = sys.path[0] if sys.path[0] else "."
sys.path.insert(0, REPO + "/pipeline" if not REPO.endswith("pipeline")
                else REPO)
import exchange_v03_lib as x3  # noqa: E402


def validate(doc):
    return x3.validate_v03(doc, load_exchange_v03_schema())


def find_version(doc, vid):
    return next(v for v in doc["versions"] if v["id"] == vid)


class FixtureIsValid(unittest.TestCase):
    def test_fixture_passes_with_zero_errors(self):
        errors, warnings, notes = validate(load_exchange_v03_doc())
        self.assertEqual(errors, [], errors)

    def test_schema_version_is_03_draft(self):
        self.assertEqual(load_exchange_v03_doc()["schema_version"],
                         "0.3-draft")

    def test_public_release_gate_is_closed(self):
        self.assertFalse(
            load_exchange_v03_doc()["release"]["public_release_approved"])


class ShapeMutations(unittest.TestCase):
    def test_wrong_schema_version_rejected(self):
        doc = load_exchange_v03_doc()
        doc["schema_version"] = "0.2-draft"
        errors, _, _ = validate(doc)
        self.assertTrue(any("0.3-draft" in e for e in errors), errors)

    def test_additional_property_rejected(self):
        doc = load_exchange_v03_doc()
        doc["versions"][0]["invented_field"] = 1
        errors, _, _ = validate(doc)
        self.assertTrue(any("invented_field" in e for e in errors), errors)

    def test_bad_sha256_pattern_rejected(self):
        doc = load_exchange_v03_doc()
        doc["manifestations"][0]["sha256"] = "not-a-hash"
        errors, _, _ = validate(doc)
        self.assertTrue(any("sha256" in e for e in errors), errors)

    def test_duplicate_version_id_rejected(self):
        doc = load_exchange_v03_doc()
        doc["versions"].append(dict(doc["versions"][0]))
        errors, _, _ = validate(doc)
        self.assertTrue(any("duplicate version id" in e for e in errors),
                        errors)


class Decision4LegacyRetrieved(unittest.TestCase):
    def test_legacy_retrieved_date_claim_rejected(self):
        doc = load_exchange_v03_doc()
        find_version(doc, "V-CO-RES-0777-2022")["dates"].append({
            "type": "retrieved", "value": "2026-11-08",
            "precision": "day", "status": "verified",
        })
        errors, _, _ = validate(doc)
        # rejected at shape (enum) or by the explicit v0.3 semantic rule
        self.assertTrue(any("retrieved" in e for e in errors), errors)

    def test_retrieved_at_is_the_only_retrieval_event(self):
        doc = load_exchange_v03_doc()
        for m in doc["manifestations"]:
            for v in doc["versions"]:
                for c in v.get("dates", []):
                    self.assertNotEqual(c["type"], "retrieved")
            if m["role"] != "unrecovered_lead":
                self.assertIsNotNone(m["retrieved_at"])


class Decision1ScoreShape(unittest.TestCase):
    def test_unknown_dimension_rejected(self):
        doc = load_exchange_v03_doc()
        doc["score_observations"][0]["dimension_id"] = "DIM-NOPE"
        errors, _, _ = validate(doc)
        self.assertTrue(any("DIM-NOPE" in e for e in errors), errors)

    def test_scale_mismatch_rejected(self):
        doc = load_exchange_v03_doc()
        doc["score_observations"][0]["scale_id"] = "SCALE-OTHER"
        errors, _, _ = validate(doc)
        self.assertTrue(any("SCALE-OTHER" in e for e in errors), errors)

    def test_status_value_pairing_enforced(self):
        doc = load_exchange_v03_doc()
        doc["score_observations"][0]["status"] = "provisional_value"
        doc["score_observations"][0]["value"] = None
        errors, _, _ = validate(doc)
        self.assertTrue(any("requires a value" in e for e in errors),
                        errors)
        doc = load_exchange_v03_doc()
        doc["score_observations"][0]["status"] = "unknown"
        doc["score_observations"][0]["value"] = 3
        errors, _, _ = validate(doc)
        self.assertTrue(any("must leave value null" in e for e in errors),
                        errors)

    def test_basis_provision_must_belong_to_same_version(self):
        doc = load_exchange_v03_doc()
        doc["score_observations"][0]["basis_provision_ids"] = [
            "P-UCT-2016-CLAUSE"]
        errors, _, _ = validate(doc)
        self.assertTrue(any("belongs to version" in e for e in errors),
                        errors)


if __name__ == "__main__":
    unittest.main()
