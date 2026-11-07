"""Test 33 — v0.3.2 cross-record integrity and CLI.

Cross-record references on the v0.3.2 fixture, the internal QC-hold
CSV reader (local-only file), and the validation CLI on the v0.3.2
fixture. Also verifies the pilot QC workbook pattern is never committed
(gitignore guard) and that no effective date is ever inferred from
award/call cohorts in v0.3.2.
"""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from tests.util import (EXCHANGE_V032_INPUT, EXCHANGE_V032_SCHEMA,
                            REPO, load_exchange_v032_doc,
                            load_exchange_v032_schema, run_cli)
except ImportError:  # pragma: no cover
    from util import (EXCHANGE_V032_INPUT, EXCHANGE_V032_SCHEMA,
                      REPO, load_exchange_v032_doc,
                      load_exchange_v032_schema, run_cli)

REPO = sys.path[0] if sys.path[0] else "."
sys.path.insert(0, REPO + "/pipeline" if not REPO.endswith("pipeline")
                else REPO)
import exchange_v03_lib as x3  # noqa: E402


def validate(doc):
    return x3.validate_v03(doc, load_exchange_v032_schema())


def find_version(doc, vid):
    return next(v for v in doc["versions"] if v["id"] == vid)


class CrossRecordIntegrity(unittest.TestCase):
    def test_fixture_fully_valid(self):
        errors, warnings, notes = validate(load_exchange_v032_doc())
        self.assertEqual(errors, [], errors)

    def test_dangling_family_reference_fails(self):
        doc = load_exchange_v032_doc()
        doc["versions"][0]["family_id"] = "F-NOPE"
        errors, _, _ = validate(doc)
        self.assertTrue(any("unknown family" in e for e in errors), errors)

    def test_null_version_lead_family_must_exist(self):
        doc = load_exchange_v032_doc()
        m = next(m for m in doc["manifestations"] if m["id"] == "M-XA-FAM-LEAD")
        m["family_id"] = "F-NOPE"
        errors, _, _ = validate(doc)
        self.assertTrue(any("unknown family_id" in e for e in errors),
                        errors)

    def test_provision_must_bind_same_version_manifestation(self):
        doc = load_exchange_v032_doc()
        doc["provisions"][0]["manifestation_id"] = "M-XA-DRAFT-PDF"
        errors, _, _ = validate(doc)
        self.assertTrue(any("not of" in e or "same version" in e
                            for e in errors), errors)

    def test_score_basis_must_be_same_version_provision(self):
        doc = load_exchange_v032_doc()
        doc["score_observations"][0]["basis_provision_ids"] = ["P-NOPE"]
        errors, _, _ = validate(doc)
        self.assertTrue(any("unknown basis provision" in e for e in errors),
                        errors)


class NoCohortInferredEffective(unittest.TestCase):
    def test_award_call_cohort_never_sets_effective(self):
        doc = load_exchange_v032_doc()
        v = find_version(doc, "V-CO-RES-0777-2022")
        co = v["cohorts"][0]
        self.assertIn(co["applies_to"]["event_type"],
                      ("publication_date", "award_made", "call_opened",
                       "grant_period_started", "submission_date"))
        eff = x3.resolve_effective_v03(v, schema_version="0.3.2-draft")
        self.assertEqual(eff.basis, "in force on publication")
        self.assertNotIn("cohort", eff.basis.lower())


class InternalQcHoldReader(unittest.TestCase):
    def test_hold_csv_reads_held_version_ids(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "pilot_source_qc_v0.3.2.csv"
            p.write_text(
                "country,version_id,public_import_status\n"
                "XA,V-XA-DRAFT-2024,hold\n"
                "XA,V-XA-BIL-ED-2023,review\n", encoding="utf-8")
            holds = x3.load_internal_qc_holds(p)
        self.assertEqual(holds, {"V-XA-DRAFT-2024"})

    def test_pilot_qc_workbook_is_gitignored(self):
        repo = Path(__file__).resolve().parents[1]
        gitignore = (repo / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("pilot_source_qc*.csv", gitignore)
        tracked = subprocess.run(
            ["git", "-C", str(repo), "ls-files"],
            capture_output=True, text=True).stdout
        self.assertNotIn("pilot_source_qc", tracked)


class Cli(unittest.TestCase):
    def test_cli_passes_on_v032_fixture(self):
        cp = run_cli(["pipeline/exchange_v03_lib.py",
                      "--input", str(EXCHANGE_V032_INPUT),
                      "--schema", str(EXCHANGE_V032_SCHEMA), "--json"])
        self.assertEqual(cp.returncode, 0, cp.stderr)
        report = json.loads(cp.stdout)
        self.assertEqual(report["schema_version"], "0.3.2-draft")
        self.assertEqual(report["errors"], [])

    def test_cli_rejects_legacy_enum_with_guidance(self):
        doc = load_exchange_v032_doc()
        doc["versions"][1]["authority_status"] = "announcement_attested"
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.json"
            bad.write_text(json.dumps(doc), encoding="utf-8")
            cp = run_cli(["pipeline/exchange_v03_lib.py",
                          "--input", str(bad),
                          "--schema", str(EXCHANGE_V032_SCHEMA)])
        self.assertEqual(cp.returncode, 1)
        self.assertIn("never by string mapping", cp.stdout)


if __name__ == "__main__":
    unittest.main()
