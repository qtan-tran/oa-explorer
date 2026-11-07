"""Test 27 — v0.3 public gating: download/excerpt/score gates stay
closed. The fixture ships with public_release_approved=false; even with
the flag flipped, score observations are never shown, internal-only
excerpts stay blank, and unknown cohort applicability never displays as
"all cohorts". Also exercises the validation CLI.
"""
import json
import sys
import unittest

try:
    from tests.util import (EXCHANGE_V03_INPUT, EXCHANGE_V03_SCHEMA,
                            load_exchange_v03_doc, run_cli)
except ImportError:  # pragma: no cover
    from util import (EXCHANGE_V03_INPUT, EXCHANGE_V03_SCHEMA,
                      load_exchange_v03_doc, run_cli)

REPO = sys.path[0] if sys.path[0] else "."
sys.path.insert(0, REPO + "/pipeline" if not REPO.endswith("pipeline")
                else REPO)
import exchange_v03_lib as x3  # noqa: E402


class GatesClosed(unittest.TestCase):
    def test_release_not_approved_withholds_everything(self):
        doc = load_exchange_v03_doc()
        views = x3.build_public_views_v03(doc, x3.PublicConfigV03())
        self.assertFalse(views["release_approved"])
        self.assertEqual(views["records"], [])
        self.assertEqual(views["withheld_count"], 4)

    def test_scores_never_public_even_when_release_approved(self):
        doc = load_exchange_v03_doc()
        doc["release"]["public_release_approved"] = True
        views = x3.build_public_views_v03(doc, x3.PublicConfigV03())
        self.assertEqual(views["score_observations"]["shown"], 0)
        self.assertEqual(views["score_observations"]["withheld_count"], 3)
        blob = json.dumps(views)
        self.assertNotIn("SO-SYNTH-01", blob)

    def test_internal_excerpts_stay_blank_when_flag_flipped(self):
        doc = load_exchange_v03_doc()
        doc["release"]["public_release_approved"] = True
        for v in doc["versions"]:
            if v["review"]["state"] in ("provisionally_reviewed",):
                v["review"]["state"] = "analyst_checked"
        views = x3.build_public_views_v03(doc, x3.PublicConfigV03())
        blob = json.dumps(views)
        self.assertNotIn("SYNTHETIC PLACEHOLDER", blob)
        for record in views["records"]:
            for pv in record["provisions"]:
                self.assertIsNone(pv["original_excerpt"])
                self.assertEqual(pv["excerpt_withheld_reason"],
                                 "rights_not_approved")

    def test_unknown_cohort_never_displays_as_all_cohorts(self):
        doc = load_exchange_v03_doc()
        doc["release"]["public_release_approved"] = True
        for v in doc["versions"]:
            if v["id"] == "V-ZA-UCT-2016-AMD":
                v["review"]["state"] = "analyst_checked"
        for m in doc["manifestations"]:
            if m["id"] == "M-UCT-2016-HTML":
                m["review"]["state"] = "analyst_checked"
        views = x3.build_public_views_v03(doc, x3.PublicConfigV03())
        record = next(r for r in views["records"]
                      if r["id"] == "V-ZA-UCT-2016-AMD")
        pv = record["provisions"][0]
        self.assertEqual(pv["cohort_applicability"], "Unknown")
        self.assertNotIn("All cohorts", json.dumps(views))

    def test_technical_columns_never_exported(self):
        doc = load_exchange_v03_doc()
        doc["release"]["public_release_approved"] = True
        for v in doc["versions"]:
            if v["review"]["state"] in ("provisionally_reviewed",
                                        "conflicted"):
                v["review"]["state"] = "analyst_checked"
        views = x3.build_public_views_v03(doc, x3.PublicConfigV03())
        blob = json.dumps(views)
        self.assertNotIn("d23c52fe", blob)          # source sha256
        self.assertNotIn("reviewer", blob)
        self.assertNotIn("review_extent", blob)
        self.assertNotIn("evidence_manifestation_id", blob)


class Cli(unittest.TestCase):
    def test_cli_passes_on_fixture(self):
        cp = run_cli(["pipeline/exchange_v03_lib.py",
                      "--input", str(EXCHANGE_V03_INPUT),
                      "--schema", str(EXCHANGE_V03_SCHEMA), "--json"])
        self.assertEqual(cp.returncode, 0, cp.stderr)
        report = json.loads(cp.stdout)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["distinct_manifestation_count"], 6)

    def test_cli_fails_on_legacy_retrieved_claim(self):
        doc = load_exchange_v03_doc()
        doc["versions"][0]["dates"].append({
            "type": "retrieved", "value": "2026-11-08",
            "precision": "day", "status": "verified"})
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.json"
            bad.write_text(json.dumps(doc), encoding="utf-8")
            cp = run_cli(["pipeline/exchange_v03_lib.py",
                          "--input", str(bad),
                          "--schema", str(EXCHANGE_V03_SCHEMA)])
        self.assertEqual(cp.returncode, 1)
        self.assertIn("retrieved", cp.stdout)


if __name__ == "__main__":
    unittest.main()
