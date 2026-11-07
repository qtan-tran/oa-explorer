"""Test 25 — the six v0.3 design decisions as semantic rules.

D1 score observations separate from provisions, no hardcoded labels, no
   composite;
D2 issuer URL vs archived_url vs verified snapshots;
D3 typed cohort triggers; cohort bounds never a general effective date;
D4 retrieved_at only retrieval event; signature/gazette/attachment-update
   distinct;
D5 explicit duplicate_of alias after matching bytes; one underlying
   manifestation; conflicting versions fail;
D6 provision cohort_applicability_status + cohort_ids; unknown never
   displays as "all cohorts".
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


class D1ScoresSeparateNoComposite(unittest.TestCase):
    def test_no_dimension_labels_hardcoded_in_library(self):
        # the authoritative ten-score codebook has not been supplied; the
        # library must not contain the ten ROARA dimension labels
        src = open(x3.__file__, encoding="utf-8").read()
        for label in ("mandate", "embargo", "licence", "apc", "repository",
                      "infrastructure", "monitoring", "governance"):
            self.assertNotIn(f'"{label}"', src)

    def test_no_composite_in_public_views(self):
        doc = load_exchange_v03_doc()
        doc["release"]["public_release_approved"] = True
        views = x3.build_public_views_v03(doc, x3.PublicConfigV03())
        self.assertEqual(views["score_observations"]["shown"], 0)
        self.assertEqual(views["score_observations"]["withheld_count"], 3)
        for record in views["records"]:
            self.assertNotIn("scores", record)
            self.assertNotIn("composite", record)

    def test_observations_are_not_provisions(self):
        doc = load_exchange_v03_doc()
        prov_ids = {p["id"] for p in doc["provisions"]}
        obs_ids = {o["id"] for o in doc["score_observations"]}
        self.assertTrue(prov_ids.isdisjoint(obs_ids))
        for o in doc["score_observations"]:
            self.assertIn("status", o)
            self.assertIn("review_extent", o)
            self.assertIn("source_scope", o)
            self.assertIn("comparability_note", o)


class D2SourceVsArchive(unittest.TestCase):
    def test_archived_url_without_verified_snapshot_is_error(self):
        doc = load_exchange_v03_doc()
        m = find_man(doc, "M-UCT-2014-HTML")
        m["archived_url"] = "https://archive.example.org/snap/other"
        errors, _, _ = validate(doc)
        self.assertTrue(any("archived_url" in e and "no archive_snapshots "
                            "entry" in e for e in errors), errors)

    def test_archived_url_must_not_be_inferred_from_live_url(self):
        doc = load_exchange_v03_doc()
        m = find_man(doc, "M-UCT-2016-HTML")
        m["archived_url"] = m["source_url"]  # the mistake D2 forbids
        errors, _, _ = validate(doc)
        self.assertTrue(any("do not infer" in e for e in errors), errors)

    def test_mutable_html_capture_without_snapshot_warns(self):
        _, warnings, _ = validate(load_exchange_v03_doc())
        self.assertTrue(any("M-UCT-2016-HTML" in w and "time-stable" in w
                            for w in warnings), warnings)

    def test_verified_snapshot_present_for_2020(self):
        doc = load_exchange_v03_doc()
        m = find_man(doc, "M-UCT-2020-PDF")
        self.assertEqual(m["archive_snapshots"][0]["capture_status"],
                         "verified_bytes")
        self.assertEqual(m["archived_url"],
                         m["archive_snapshots"][0]["url"])


class D3TypedCohortTriggers(unittest.TestCase):
    def test_event_type_enum_enforced_by_shape(self):
        doc = load_exchange_v03_doc()
        co = find_version(doc, "V-CO-RES-0777-2022")["cohorts"][0]
        co["applies_to"]["event_type"] = "whenever"
        errors, _, _ = validate(doc)
        self.assertTrue(errors, "free-text event type must fail shape")

    def test_cohort_start_must_be_typed_cohort_start(self):
        doc = load_exchange_v03_doc()
        co = find_version(doc, "V-CO-RES-0777-2022")["cohorts"][0]
        co["start"]["type"] = "effective"
        errors, _, _ = validate(doc)
        self.assertTrue(any("cohort_start" in e for e in errors), errors)

    def test_cohort_threshold_never_resolves_as_effective(self):
        doc = load_exchange_v03_doc()
        v = find_version(doc, "V-CO-RES-0777-2022")
        # effective comes from gazette publication (2022-12-09) via
        # promulgation linkage; the cohort start shares the date value
        # here, so prove the basis is NOT the cohort
        eff = x3.resolve_effective_v03(v, schema_version="0.3-draft")
        self.assertNotIn("cohort", eff.basis.lower())


class D4RetrievalAndDistinctDates(unittest.TestCase):
    def test_signature_gazette_and_attachment_update_distinct(self):
        doc = load_exchange_v03_doc()
        v = find_version(doc, "V-CO-RES-0777-2022")
        types = {c["type"]: c for c in v["dates"]}
        self.assertEqual(types["adopted"]["value"], "2022-08-03")
        self.assertEqual(types["published"]["value"], "2022-12-09")
        self.assertEqual(types["published"]["physical_anchor"],
                         "Diario Oficial, edición 52.243")
        self.assertEqual(types["other"]["status"], "unknown")
        self.assertIsNone(types["other"]["value"])


class D5DuplicateAliases(unittest.TestCase):
    def test_alias_collapses_to_one_underlying_manifestation(self):
        doc = load_exchange_v03_doc()
        self.assertEqual(len(doc["manifestations"]), 7)
        self.assertEqual(len(x3.distinct_manifestations(doc)), 6)

    def test_alias_with_mismatched_bytes_fails(self):
        doc = load_exchange_v03_doc()
        find_man(doc, "M-CO-0777-RES-MIRROR-B")["sha256"] = "0" * 64
        errors, _, _ = validate(doc)
        self.assertTrue(any("matching bytes" in e for e in errors), errors)

    def test_conflicting_version_assignment_fails(self):
        doc = load_exchange_v03_doc()
        find_man(doc, "M-CO-0777-RES-MIRROR-B")["version_id"] = \
            "V-ZA-UCT-2020"
        errors, _, _ = validate(doc)
        self.assertTrue(any("conflicting version" in e for e in errors),
                        errors)

    def test_cross_version_identical_hash_fails(self):
        doc = load_exchange_v03_doc()
        find_man(doc, "M-UCT-2020-PDF")["sha256"] = \
            find_man(doc, "M-CO-0777-RES-MIRROR")["sha256"]
        find_man(doc, "M-UCT-2020-PDF")["duplicate_of_manifestation_id"] = \
            None
        errors, _, _ = validate(doc)
        self.assertTrue(any("across versions" in e for e in errors), errors)

    def test_alias_to_missing_target_fails(self):
        doc = load_exchange_v03_doc()
        find_man(doc, "M-CO-0777-RES-MIRROR-B")["duplicate_of_manifestation_id"] = "M-NOPE"
        errors, _, _ = validate(doc)
        self.assertTrue(any("does not exist" in e for e in errors), errors)


class D6ProvisionCohortApplicability(unittest.TestCase):
    def test_subset_without_cohort_ids_fails(self):
        doc = load_exchange_v03_doc()
        p = next(p for p in doc["provisions"] if p["id"] == "P-CO-0777-ART3")
        p["cohort_ids"] = []
        errors, _, _ = validate(doc)
        self.assertTrue(any("subset" in e and "cohort id" in e
                            for e in errors), errors)

    def test_subset_citing_foreign_cohort_fails(self):
        doc = load_exchange_v03_doc()
        p = next(p for p in doc["provisions"] if p["id"] == "P-CO-0777-ART3")
        p["cohort_ids"] = ["C-FOREIGN"]
        errors, _, _ = validate(doc)
        self.assertTrue(any("not a cohort of version" in e for e in errors),
                        errors)

    def test_unknown_status_must_carry_empty_cohort_ids(self):
        doc = load_exchange_v03_doc()
        p = next(p for p in doc["provisions"]
                 if p["id"] == "P-UCT-2016-CLAUSE")
        p["cohort_ids"] = ["C-CO-0777-AWARD"]
        errors, _, _ = validate(doc)
        self.assertTrue(any("must be empty" in e for e in errors), errors)

    def test_unknown_never_displays_as_all_cohorts(self):
        doc = load_exchange_v03_doc()
        p = next(p for p in doc["provisions"]
                 if p["id"] == "P-UCT-2016-CLAUSE")
        display = x3.cohort_applicability_display(p)
        self.assertEqual(display, "Unknown")
        self.assertNotIn("All", display)

    def test_subset_displays_cited_cohorts(self):
        doc = load_exchange_v03_doc()
        p = next(p for p in doc["provisions"] if p["id"] == "P-CO-0777-ART3")
        self.assertIn("C-CO-0777-AWARD",
                      x3.cohort_applicability_display(p))


if __name__ == "__main__":
    unittest.main()
