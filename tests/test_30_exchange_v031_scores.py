"""Test 30 — v0.3.1 score-observation semantics.

actor/action are the POLICY actor and the evaluated action (not the
analyst); for mixed clauses they are null and source_scope plus basis
provision references retain the detail. No numeric ten-score import and
no composite until the owner supplies labels, scale anchors and a
codebook version.
"""
import json
import sys
import unittest

try:
    from tests.util import (load_exchange_v031_doc, load_exchange_v031_schema,
                            EXCHANGE_V031_INPUT, EXCHANGE_V031_SCHEMA,
                            run_cli)
except ImportError:  # pragma: no cover
    from util import (load_exchange_v031_doc, load_exchange_v031_schema,
                      EXCHANGE_V031_INPUT, EXCHANGE_V031_SCHEMA, run_cli)

REPO = sys.path[0] if sys.path[0] else "."
sys.path.insert(0, REPO + "/pipeline" if not REPO.endswith("pipeline")
                else REPO)
import exchange_v03_lib as x3  # noqa: E402


def find_obs(doc, oid):
    return next(o for o in doc["score_observations"] if o["id"] == oid)


class ScoreActorActionSemantics(unittest.TestCase):
    def test_mixed_clause_uses_null_actor_action_with_scope_and_basis(self):
        doc = load_exchange_v031_doc()
        so = find_obs(doc, "SO-SYNTH-02")
        self.assertIsNone(so["actor"])
        self.assertIsNone(so["action"])
        self.assertIn("mixes actors/actions", so["source_scope"])
        self.assertIn("policy actor", so["comparability_note"])

    def test_unreviewed_observation_retains_basis_provisions(self):
        doc = load_exchange_v031_doc()
        so = find_obs(doc, "SO-SYNTH-01")
        self.assertEqual(so["basis_provision_ids"], ["P-CO-0777-ART3"])
        self.assertIsNone(so["value"])

    def test_valued_observation_with_actor_but_no_basis_warns(self):
        doc = load_exchange_v031_doc()
        so = find_obs(doc, "SO-SYNTH-02")
        so["actor"] = "SYNTHETIC actor without basis"
        errors, warnings, _ = x3.validate_v03(doc,
                                              load_exchange_v031_schema())
        self.assertEqual(errors, [], errors)
        self.assertTrue(any("no basis provision" in w for w in warnings),
                        warnings)

    def test_no_numeric_ten_score_import(self):
        doc = load_exchange_v031_doc()
        # only the single placeholder dimension exists; no ten labels
        self.assertEqual(len(doc["score_definitions"]), 1)
        self.assertEqual(doc["score_definitions"][0]["codebook_version"],
                         "not-supplied")

    def test_no_composite_even_when_release_approved(self):
        doc = load_exchange_v031_doc()
        doc["release"]["public_release_approved"] = True
        views = x3.build_public_views_v03(doc, x3.PublicConfigV03())
        self.assertEqual(views["score_observations"]["shown"], 0)
        self.assertEqual(views["score_observations"]["withheld_count"], 3)
        blob = json.dumps(views)
        self.assertNotIn("SO-SYNTH", blob)
        self.assertNotIn('"composite"', blob)  # no composite field/value
        for record in views["records"]:
            self.assertNotIn("scores", record)

    def test_cli_on_v031_fixture(self):
        cp = run_cli(["pipeline/exchange_v03_lib.py",
                      "--input", str(EXCHANGE_V031_INPUT),
                      "--schema", str(EXCHANGE_V031_SCHEMA), "--json"])
        self.assertEqual(cp.returncode, 0, cp.stderr)
        report = json.loads(cp.stdout)
        self.assertEqual(report["schema_version"], "0.3.1-draft")
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["distinct_manifestation_count"], 8)


if __name__ == "__main__":
    unittest.main()
