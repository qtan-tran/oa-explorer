"""Test 1 — contract schemas: structure, ID patterns, schema/vocabulary
consistency, contract versioning, allowlist coverage."""
import csv
import json
import unittest
from pathlib import Path

try:
    from tests.util import CONTRACT, REPO, fixture  # noqa: F401
except ImportError:
    from util import CONTRACT, REPO, fixture  # noqa: F401

SCHEMA_DIR = CONTRACT / "json-schema"
ENTITIES = ["country", "organization", "policy_family", "policy_version",
            "manifestation", "provision", "version_relationship", "text",
            "version_function"]
ID_PATTERNS = {
    "country": r"^[A-Z]{2}$",
    "organization": r"^O-[A-Z]{2}-\d{4}$",
    "policy_family": r"^F-[A-Z]{2}-\d{4}$",
    "policy_version": r"^V-[A-Z]{2}-\d{4}$",
    "manifestation": r"^M-[A-Z]{2}-\d{4}$",
    "provision": r"^P-[A-Z]{2}-\d{4}$",
    "version_relationship": r"^R-\d{4}$",
}
ENTITY_FILE = {"country": "countries.csv", "organization": "organizations.csv",
               "policy_family": "policy_families.csv",
               "policy_version": "policy_versions.csv",
               "manifestation": "manifestations.csv",
               "provision": "provisions.csv",
               "version_relationship": "version_relationships.csv"}


class SchemaTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.schemas = {e: json.loads(
            (SCHEMA_DIR / f"{e}.schema.json").read_text(encoding="utf-8"))
            for e in ENTITIES}

    def test_all_schemas_present_and_parse(self):
        for e in ENTITIES:
            s = self.schemas[e]
            self.assertEqual(s["$schema"],
                             "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(s["type"], "object")
            self.assertIn("x-column-order", s, e)

    def test_column_order_matches_properties(self):
        for e, s in self.schemas.items():
            order = s["x-column-order"]
            self.assertEqual(sorted(order), sorted(s["properties"]),
                              f"{e}: column order and properties diverge")
            self.assertEqual(len(order), len(set(order)),
                             f"{e}: duplicate column")

    def test_id_columns_required_with_pattern(self):
        for e, pat in ID_PATTERNS.items():
            id_col = self.schemas[e]["x-column-order"][0]
            self.assertIn(id_col, self.schemas[e]["required"], e)
            self.assertEqual(self.schemas[e]["properties"][id_col]["pattern"],
                             pat, e)

    def test_ids_in_synthetic_corpus_match_patterns(self):
        for e, pat in ID_PATTERNS.items():
            with open(REPO / "synthetic" / ENTITY_FILE[e], newline="",
                      encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertTrue(rows, f"{ENTITY_FILE[e]} is empty")
            id_col = self.schemas[e]["x-column-order"][0]
            for r in rows:
                self.assertRegex(r[id_col], pat,
                                 f"{ENTITY_FILE[e]}: bad id {r[id_col]}")

    def test_synthetic_ids_are_visibly_synthetic(self):
        """Sample IDs must be unmistakably synthetic in the data itself."""
        with open(REPO / "synthetic" / "countries.csv", newline="",
                  encoding="utf-8") as fh:
            countries = {r["country_id"] for r in csv.DictReader(fh)}
        self.assertEqual(countries, {"XA", "XB"},
                         "synthetic countries must use user-assigned ISO codes")

    def test_contract_version_is_semver(self):
        version = (CONTRACT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")

    def test_field_vocab_mapping_backed_by_vocabularies(self):
        """Every vocabulary used by FIELD_VOCAB must exist in
        vocabularies.csv; every schema enum must equal its vocabulary."""
        import sys
        sys.path.insert(0, str(REPO / "pipeline"))
        import contract_lib as cl

        with open(CONTRACT / "vocabularies.csv", newline="",
                  encoding="utf-8") as fh:
            vocab = {}
            for r in csv.DictReader(fh):
                vocab.setdefault(r["vocabulary"], set()).add(r["value"])

        for entity, cols in cl.FIELD_VOCAB.items():
            for col, voc_name in cols.items():
                self.assertIn(voc_name, vocab,
                              f"{entity}.{col}: missing vocabulary {voc_name}")
                spec = self.schemas[entity]["properties"].get(col)
                if spec and "enum" in spec:
                    # "" encodes "not set" in CSV and is not a vocabulary term
                    self.assertEqual(set(spec["enum"]) - {""},
                                     vocab[voc_name],
                                     f"{entity}.{col}: enum != vocabularies.csv")

    def test_allowlist_fields_exist_in_schemas(self):
        """Every allowlisted public field must exist in its entity schema,
        so the allowlist can never smuggle in an unknown column."""
        with open(CONTRACT / "public_allowlist.csv", newline="",
                  encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertTrue(rows, "public allowlist is empty")
        for r in rows:
            self.assertIn(r["entity"], self.schemas,
                         f"allowlist names unknown entity {r['entity']}")
            self.assertIn(r["field"],
                          self.schemas[r["entity"]]["properties"],
                          f"allowlist names unknown field "
                          f"{r['entity']}.{r['field']}")


if __name__ == "__main__":
    unittest.main()
