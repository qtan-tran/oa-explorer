"""Test 20 — exchange v0.2 shape validation.

The synthetic fixture must pass the draft schema; targeted mutations must
each fail. These tests check shape only; cross-references, hashes and
date semantics have their own suites.
"""
import sys
import unittest

try:
    from tests.util import load_exchange_doc, load_exchange_schema
except ImportError:  # pragma: no cover - direct unittest invocation
    from util import load_exchange_doc, load_exchange_schema

REPO = sys.path[0] if sys.path[0] else "."
sys.path.insert(0, REPO + "/pipeline" if not REPO.endswith("pipeline")
                else REPO)
import exchange_lib as xl  # noqa: E402


def shape_errors(doc, schema=None):
    schema = schema or load_exchange_schema()
    return xl.validate_shape(doc, schema)


def find_version(doc, vid):
    return next(v for v in doc["versions"] if v["id"] == vid)


def find_manifestation(doc, mid):
    return next(m for m in doc["manifestations"] if m["id"] == mid)


class ShapeBaseline(unittest.TestCase):
    def test_fixture_passes_shape(self):
        self.assertEqual(shape_errors(load_exchange_doc()), [])

    def test_schema_version_const(self):
        doc = load_exchange_doc()
        doc["schema_version"] = "0.1"
        errs = shape_errors(doc)
        self.assertTrue(any("const" in e for e in errs), errs)

    def test_missing_required_root_key(self):
        doc = load_exchange_doc()
        del doc["relationships"]
        self.assertTrue(any("required property 'relationships'" in e
                            for e in shape_errors(doc)))

    def test_additional_property_rejected(self):
        doc = load_exchange_doc()
        doc["countries"][0]["population"] = 1
        self.assertTrue(any("additional property 'population'" in e
                            for e in shape_errors(doc)))

    def test_bad_country_pattern(self):
        doc = load_exchange_doc()
        doc["countries"][0]["code"] = "xa"  # lowercase
        self.assertTrue(any("pattern" in e for e in shape_errors(doc)))

    def test_bad_sha256_pattern(self):
        doc = load_exchange_doc()
        find_manifestation(doc, "M-MAR-OA-2011-PDF")["sha256"] = "not-a-hash"
        self.assertTrue(any("pattern" in e for e in shape_errors(doc)))

    def test_bad_enum_values(self):
        doc = load_exchange_doc()
        find_version(doc, "V-MAR-OA-2011")["authority_status"] = "rumoured"
        errs = shape_errors(doc)
        self.assertTrue(any("not in enum" in e for e in errs), errs)
        doc = load_exchange_doc()
        find_manifestation(doc, "M-MAR-OA-2011-PDF")["role"] = "the_original"
        self.assertTrue(any("not in enum" in e for e in shape_errors(doc)))

    def test_issuer_ids_min_items_and_uniqueness(self):
        doc = load_exchange_doc()
        v = find_version(doc, "V-BOR-TRI-2026")
        v["issuer_ids"] = []
        self.assertTrue(any("minItems" in e for e in shape_errors(doc)))
        doc = load_exchange_doc()
        v = find_version(doc, "V-BOR-TRI-2026")
        v["issuer_ids"] = ["O-XB-0001", "O-XB-0001"]
        self.assertTrue(any("not unique" in e for e in shape_errors(doc)))

    def test_date_claim_requires_all_four_keys(self):
        doc = load_exchange_doc()
        del find_version(doc, "V-MAR-OA-2011")["dates"][0]["status"]
        self.assertTrue(any("required property 'status'" in e
                            for e in shape_errors(doc)))

    def test_date_claim_value_pattern_by_precision(self):
        # pattern lives on the dateClaim value; wrong shape is caught by
        # the pattern itself, precision consistency by the semantic layer
        doc = load_exchange_doc()
        find_version(doc, "V-MAR-OA-2011")["dates"][0]["value"] = "22.03.2011"
        self.assertTrue(any("pattern" in e for e in shape_errors(doc)))

    def test_type_error(self):
        doc = load_exchange_doc()
        doc["release"]["public_release_approved"] = "yes"
        self.assertTrue(any("expected type" in e for e in shape_errors(doc)))

    def test_null_handling(self):
        # nullable fields accept null: unrecovered lead, translation
        doc = load_exchange_doc()
        m = find_manifestation(doc, "M-BOR-TRI-2015-LEAD")
        self.assertIsNone(m["source_url"])
        self.assertIsNone(m["sha256"])
        self.assertEqual(shape_errors(doc), [])
        # but null where a plain string is required must fail
        doc = load_exchange_doc()
        find_version(doc, "V-MAR-OA-2011")["title_original"] = None
        self.assertTrue(any("expected type" in e for e in shape_errors(doc)))

    def test_physical_pages_minimum(self):
        doc = load_exchange_doc()
        find_manifestation(doc, "M-BOR-NOS-RES")["physical_pages"] = 0
        errs = shape_errors(doc)
        self.assertTrue(any("minimum" in e.lower() for e in errs), errs)

    def test_full_validation_clean(self):
        # shape + cross-references + hashes + dates: 0 errors
        doc = load_exchange_doc()
        errors, warnings = xl.validate_exchange(doc, load_exchange_schema())
        self.assertEqual(errors, [])
        # exactly one expected note: the legal mirror duplicate hash
        self.assertEqual(len(warnings), 1)
        self.assertIn("mirror", warnings[0])


if __name__ == "__main__":
    unittest.main()
