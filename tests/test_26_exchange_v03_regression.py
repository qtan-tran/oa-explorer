"""Test 26 — synthetic regression fixtures for v0.3.

Case A: Colombia Resolution 0777 structural scenario — signed
2022-08-03, Article 3 effective on publication, gazette facsimile issue
52.243 dated 2022-12-09, mirror provenance with official-host
corroboration pending, resolution and annex as ONE version.

Case B: UCT genealogy fixture — the repository's 2014 label points to an
amended 2014/2016 text, followed by a 2020 revision; no clean 2014
clause baseline or effective date may be inferred.

All records are SYNTHETIC; no original policy file or excerpt is
imported.
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


def find_man(doc, mid):
    return next(m for m in doc["manifestations"] if m["id"] == mid)


class ColombiaResolution0777(unittest.TestCase):
    def setUp(self):
        self.doc = load_exchange_v03_doc()
        self.v = find_version(self.doc, "V-CO-RES-0777-2022")

    def test_fixture_valid(self):
        errors, _, _ = validate(self.doc)
        self.assertEqual(errors, [], errors)

    def test_signature_and_gazette_dates_distinct(self):
        by_type = {c["type"]: c for c in self.v["dates"]}
        self.assertEqual(by_type["adopted"]["value"], "2022-08-03")
        self.assertEqual(by_type["published"]["value"], "2022-12-09")
        self.assertEqual(by_type["published"]["physical_anchor"],
                         "Diario Oficial, edición 52.243")

    def test_article_3_effective_on_publication(self):
        # v0.3-draft fixture: promulgation linkage derived from the
        # gazette 'published' claim (legacy behaviour)
        self.assertEqual(self.v["effective_date_interpretation"],
                         "promulgation_linked")
        eff = x3.resolve_effective_v03(self.v, schema_version="0.3-draft")
        self.assertEqual(eff.value, "2022-12-09")
        self.assertIn("promulgation", eff.basis)
        self.assertIn("2022-12-09", x3.effective_display_v03(eff))

    def test_effective_not_derived_from_cohort(self):
        # the award cohort starts on the same calendar day; the effective
        # basis must be gazette publication, not the cohort threshold
        eff = x3.resolve_effective_v03(self.v, schema_version="0.3-draft")
        self.assertNotIn("cohort", eff.basis.lower())
        co = self.v["cohorts"][0]
        self.assertEqual(co["applies_to"]["event_type"], "award_made")
        self.assertEqual(co["start"]["type"], "cohort_start")

    def test_resolution_and_annex_are_one_version(self):
        annex = find_man(self.doc, "M-CO-0777-ANNEX")
        res = find_man(self.doc, "M-CO-0777-RES-MIRROR")
        self.assertEqual(annex["version_id"], res["version_id"])
        self.assertEqual(annex["component_of_manifestation_id"], res["id"])
        self.assertNotEqual(annex["sha256"], res["sha256"])

    def test_mirror_provenance_and_official_host_pending(self):
        self.assertEqual(self.v["source_status"], "mirror_only")
        self.assertEqual(self.v["review"]["state"], "provisionally_reviewed")
        mirror = find_man(self.doc, "M-CO-0777-RES-MIRROR")
        lead = find_man(self.doc, "M-CO-0777-RES-OFFICIAL-LEAD")
        self.assertEqual(mirror["role"], "mirror")
        self.assertEqual(lead["role"], "unrecovered_lead")
        self.assertIsNone(lead["sha256"])
        self.assertIsNone(lead["retrieved_at"])
        # mirror bytes are aliased, not double-counted
        self.assertEqual(len(x3.distinct_manifestations(self.doc)), 6)

    def test_no_original_excerpt_imported(self):
        for p in self.doc["provisions"]:
            if p["version_id"] == "V-CO-RES-0777-2022":
                self.assertIn("SYNTHETIC PLACEHOLDER",
                              p["original_excerpt"])
                self.assertEqual(p["excerpt_rights_status"], "internal_only")


class UctGenealogy(unittest.TestCase):
    def setUp(self):
        self.doc = load_exchange_v03_doc()

    def test_no_clean_2014_effective_date_inferred(self):
        v2014 = find_version(self.doc, "V-ZA-UCT-2014-LABEL")
        self.assertEqual(v2014["effective_date_interpretation"], "unknown")
        eff = x3.resolve_effective_v03(v2014)
        self.assertIsNone(eff.value)
        self.assertEqual(x3.effective_display_v03(eff),
                         "Unknown / not established")

    def test_2014_label_points_to_amended_text(self):
        v2014 = find_version(self.doc, "V-ZA-UCT-2014-LABEL")
        self.assertEqual(v2014["review"]["state"], "conflicted")
        m2016 = find_man(self.doc, "M-UCT-2016-HTML")
        self.assertIn("labelled 2014", m2016["authority_evidence"])
        self.assertEqual(m2016["version_id"], "V-ZA-UCT-2016-AMD")

    def test_relationship_chain_2014_to_2016_to_2020(self):
        rels = {(r["earlier_version_id"], r["later_version_id"]): r
                for r in self.doc["relationships"]}
        r1 = rels[("V-ZA-UCT-2014-LABEL", "V-ZA-UCT-2016-AMD")]
        r2 = rels[("V-ZA-UCT-2016-AMD", "V-ZA-UCT-2020")]
        self.assertEqual(r1["type"], "amendment")
        self.assertEqual(r2["type"], "explicit_replacement")

    def test_no_reviewed_2014_clause_baseline(self):
        # no provision may be bound to the 2014-labelled version as a
        # clean baseline
        for p in self.doc["provisions"]:
            if p["version_id"] == "V-ZA-UCT-2014-LABEL":
                self.assertIn(p["code_status"], ("unreviewed",))


if __name__ == "__main__":
    unittest.main()
