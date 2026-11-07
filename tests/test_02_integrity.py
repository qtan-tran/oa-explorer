"""Test 2 — referential integrity: foreign keys, uniqueness (primary and
composite keys), acyclicity of version relationships. Each test mutates an
in-memory copy of the synthetic corpus and must produce a validation error."""
import copy
import sys
import unittest
from pathlib import Path

try:
    from tests.util import CONTRACT, REPO, fixture  # noqa: F401
except ImportError:
    from util import CONTRACT, REPO, fixture  # noqa: F401

sys.path.insert(0, str(REPO / "pipeline"))
import contract_lib as cl  # noqa: E402


def load_copy():
    schemas = cl.load_schemas(CONTRACT)
    data, load_errors = cl.load_dataset(REPO / "synthetic", schemas)
    assert not load_errors, load_errors
    return data


def errors_for(data):
    return cl.validate_dataset(data, CONTRACT, label="mutated-copy")


class IntegrityTests(unittest.TestCase):

    def test_synthetic_corpus_valid(self):
        self.assertEqual(errors_for(load_copy()), [])

    def test_cli_validate_exit_zero(self):
        res = fixture().validate
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("VALID", res.stdout)

    def test_missing_foreign_key_family(self):
        data = load_copy()
        data["policy_version"][0]["family_id"] = "F-XX-9999"
        errs = errors_for(data)
        self.assertTrue(any("F-XX-9999" in e for e in errs), errs)

    def test_missing_foreign_key_manifestation_to_version(self):
        data = load_copy()
        data["manifestation"][0]["version_id"] = "V-XX-9999"
        errs = errors_for(data)
        self.assertTrue(any("V-XX-9999" in e for e in errs), errs)

    def test_missing_foreign_key_country(self):
        data = load_copy()
        data["organization"][0]["country_id"] = "XX"
        errs = errors_for(data)
        self.assertTrue(any("XX" in e for e in errs), errs)

    def test_duplicate_primary_key(self):
        data = load_copy()
        dup = copy.deepcopy(data["policy_version"][0])
        data["policy_version"].append(dup)
        errs = errors_for(data)
        self.assertTrue(any("duplicate" in e.lower() for e in errs), errs)

    def test_duplicate_composite_key_text(self):
        data = load_copy()
        dup = copy.deepcopy(data["text"][0])
        data["text"].append(dup)
        errs = errors_for(data)
        self.assertTrue(any("duplicate" in e.lower() for e in errs), errs)

    def test_duplicate_composite_key_version_function(self):
        data = load_copy()
        dup = copy.deepcopy(data["version_function"][0])
        data["version_function"].append(dup)
        errs = errors_for(data)
        self.assertTrue(any("duplicate" in e.lower() for e in errs), errs)

    def test_relationship_cycle_detected(self):
        data = load_copy()
        # Existing edge: V-XA-0002 -[replaces]-> V-XA-0001.
        # Add the reverse edge to close a cycle of length 2.
        cyc = copy.deepcopy(data["version_relationship"][0])
        cyc["relationship_id"] = "R-9999"
        cyc["from_version_id"], cyc["to_version_id"] = \
            cyc["to_version_id"], cyc["from_version_id"]
        data["version_relationship"].append(cyc)
        errs = errors_for(data)
        self.assertTrue(any("cycle" in e.lower() for e in errs), errs)

    def test_self_reference_detected(self):
        data = load_copy()
        rel = copy.deepcopy(data["version_relationship"][0])
        rel["relationship_id"] = "R-9998"
        rel["to_version_id"] = rel["from_version_id"]
        data["version_relationship"].append(rel)
        errs = errors_for(data)
        self.assertTrue(any("self" in e.lower() or "cycle" in e.lower()
                            for e in errs), errs)


if __name__ == "__main__":
    unittest.main()
