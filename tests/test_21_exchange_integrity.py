"""Test 21 — exchange v0.2 cross-references and duplicate hashes.

Beyond JSON shape: FK integrity, composite evidence binding,
component chains (signed resolution + annex), relationship acyclicity,
and duplicate source-hash rules.
"""
import copy
import sys
import unittest

try:
    from tests.util import load_exchange_doc
except ImportError:  # pragma: no cover
    from util import load_exchange_doc

REPO = sys.path[0] if sys.path[0] else "."
sys.path.insert(0, REPO + "/pipeline" if not REPO.endswith("pipeline")
                else REPO)
import exchange_lib as xl  # noqa: E402


def xref_errors(doc):
    errs = []
    xl.validate_cross_references(doc, errs)
    return errs


def find(seq, key, val):
    return next(x for x in seq if x[key] == val)


def find_version(doc, vid):
    return find(doc["versions"], "id", vid)


def find_manifestation(doc, mid):
    return find(doc["manifestations"], "id", mid)


class CrossReferences(unittest.TestCase):
    def test_baseline_clean(self):
        self.assertEqual(xref_errors(load_exchange_doc()), [])

    def test_dangling_family_issuer(self):
        doc = load_exchange_doc()
        find_version(doc, "V-MAR-OA-2011")["family_id"] = "F-NOPE"
        self.assertTrue(any("unknown family" in e for e in xref_errors(doc)))
        doc = load_exchange_doc()
        doc["families"][0]["issuer_id"] = "O-NOPE"
        self.assertTrue(any("unknown issuer" in e for e in xref_errors(doc)))

    def test_dangling_manifestation_version(self):
        doc = load_exchange_doc()
        find_manifestation(doc, "M-MAR-OA-2011-PDF")["version_id"] = \
            "V-NOPE"
        self.assertTrue(any("unknown version" in e for e in xref_errors(doc)))

    def test_dangling_provision_manifestation(self):
        doc = load_exchange_doc()
        find(doc["provisions"], "id", "P-MAR-2011-1")["manifestation_id"] = \
            "M-NOPE"
        self.assertTrue(any("unknown manifestation" in e
                            for e in xref_errors(doc)))

    def test_provision_bound_to_other_versions_manifestation(self):
        # evidence must come from a manifestation of the SAME version
        doc = load_exchange_doc()
        find(doc["provisions"], "id", "P-MAR-2011-1")["manifestation_id"] = \
            "M-BOR-REPO-2016-PDF"  # belongs to V-BOR-REPO-2016
        errs = xref_errors(doc)
        self.assertTrue(any("evidence" in e and
                            "same version" in e for e in errs), errs)

    def test_null_version_binding_allowed_for_unrecovered_lead(self):
        # M-BNRA-018-2022-LEAD has version_id null; must not error
        doc = load_exchange_doc()
        m = find_manifestation(doc, "M-BNRA-018-2022-LEAD")
        self.assertIsNone(m["version_id"])
        self.assertEqual(xref_errors(doc), [])

    def test_component_of_missing_self_and_cycle(self):
        doc = load_exchange_doc()
        find_manifestation(doc, "M-BOR-NOS-ANNEX")[
            "component_of_manifestation_id"] = "M-NOPE"
        self.assertTrue(any("component_of" in e and "does not exist" in e
                            for e in xref_errors(doc)))
        doc = load_exchange_doc()
        find_manifestation(doc, "M-BOR-NOS-ANNEX")[
            "component_of_manifestation_id"] = "M-BOR-NOS-ANNEX"
        self.assertTrue(any("component_of itself" in e
                            for e in xref_errors(doc)))
        # two-node cycle: RES -> ANNEX -> RES
        doc = load_exchange_doc()
        find_manifestation(doc, "M-BOR-NOS-RES")[
            "component_of_manifestation_id"] = "M-BOR-NOS-ANNEX"
        self.assertTrue(any("cycle" in e for e in xref_errors(doc)))

    def test_signed_resolution_annex_chain_present(self):
        # the design fixture: annex is component_of the resolution
        doc = load_exchange_doc()
        annex = find_manifestation(doc, "M-BOR-NOS-ANNEX")
        self.assertEqual(annex["component_of_manifestation_id"],
                         "M-BOR-NOS-RES")
        res = find_manifestation(doc, "M-BOR-NOS-RES")
        self.assertEqual(res["role"], "controlling_original")
        self.assertEqual(res["rights_status"], "internal_only")
        self.assertIn("signed resolution", res["authority_evidence"])

    def test_duplicate_ids_rejected(self):
        doc = load_exchange_doc()
        doc["versions"].append(copy.deepcopy(doc["versions"][0]))
        errs = xref_errors(doc)
        self.assertTrue(any("duplicate version id" in e for e in errs))
        doc = load_exchange_doc()
        doc["manifestations"].append(
            copy.deepcopy(doc["manifestations"][0]))
        self.assertTrue(any("duplicate manifestation id" in e
                            for e in xref_errors(doc)))

    def test_relationship_unknown_endpoint_and_self(self):
        doc = load_exchange_doc()
        find(doc["relationships"], "id", "R-BNRA-2023-01")[
            "later_version_id"] = "V-NOPE"
        self.assertTrue(any("later_version_id" in e and "unknown" in e
                            for e in xref_errors(doc)))
        doc = load_exchange_doc()
        r = find(doc["relationships"], "id", "R-BNRA-2023-01")
        r["earlier_version_id"] = r["later_version_id"]
        self.assertTrue(any("relates a version to itself" in e
                            for e in xref_errors(doc)))

    def test_relationship_cycle_detected(self):
        # R-BNRA: 018-2022 -> 012-2023 (earlier->later); adding the
        # reverse edge closes a cycle and must be reported loudly
        doc = load_exchange_doc()
        doc["relationships"].append({
            "id": "R-CYCLE-01",
            "earlier_version_id": "V-BOR-BNRA-012-2023",
            "later_version_id": "V-BNRA-018-2022",
            "type": "explicit_replacement",
            "evidence_manifestation_id": None,
            "anchor": None,
            "review": {"state": "analyst_checked"},
        })
        self.assertTrue(any("cycle" in e for e in xref_errors(doc)))

    def test_relationship_evidence_pointer_validated(self):
        doc = load_exchange_doc()
        find(doc["relationships"], "id", "R-BNRA-2023-01")[
            "evidence_manifestation_id"] = "M-NOPE"
        self.assertTrue(any("evidence manifestation" in e
                            for e in xref_errors(doc)))


class DuplicateHashes(unittest.TestCase):
    def test_legal_mirror_duplicate_is_a_note(self):
        doc = load_exchange_doc()
        errors, notes = xl.check_duplicate_hashes(doc)
        self.assertEqual(errors, [])
        self.assertEqual(len(notes), 1)
        self.assertIn("mirror", notes[0])

    def test_cross_version_duplicate_is_an_error(self):
        doc = load_exchange_doc()
        # point the BNRA mirror at a different version, keep the hash
        m = find_manifestation(doc, "M-BOR-BNRA-2023-MIRROR")
        m["version_id"] = "V-BOR-REPO-2016"
        errors, _ = xl.check_duplicate_hashes(doc)
        self.assertTrue(any("across versions" in e for e in errors))

    def test_translation_duplicate_is_an_error(self):
        doc = load_exchange_doc()
        m = find_manifestation(doc, "M-BOR-BNRA-2023-MIRROR")
        m["role"] = "translation"
        errors, _ = xl.check_duplicate_hashes(doc)
        self.assertTrue(any("translation" in e for e in errors))

    def test_distinct_hashes_no_findings(self):
        doc = load_exchange_doc()
        # break the only duplicate: no findings at all
        find_manifestation(doc, "M-BOR-BNRA-2023-MIRROR")["sha256"] = \
            "ab" * 32
        errors, notes = xl.check_duplicate_hashes(doc)
        self.assertEqual(errors, [])
        self.assertEqual(notes, [])


if __name__ == "__main__":
    unittest.main()
