"""Test 10 — reproducible builds: two clean export+build runs from the same
inputs must be byte-identical, and the export manifest's checksums must
match the exported files. This is the restore/rebuild guarantee: anyone
can rebuild the site from the repository without network access."""
import json
import tempfile
import unittest
from pathlib import Path

try:
    from tests.util import (CONTRACT, REPO, SYNTHETIC, fixture, read_csv,
                            run_cli, tree_hashes)
except ImportError:
    from util import (CONTRACT, REPO, SYNTHETIC, fixture, read_csv,
                      run_cli, tree_hashes)


def export_and_build(tmp: Path) -> tuple[Path, Path]:
    export_dir = tmp / "exports" / "public"
    site_dir = tmp / "_site"
    r1 = run_cli(["pipeline/build_public.py", "--input", str(SYNTHETIC),
                  "--contract", str(CONTRACT), "--output", str(export_dir)])
    assert r1.returncode == 0, r1.stdout + r1.stderr
    r2 = run_cli(["site/build.py", "--export", str(export_dir),
                  "--output", str(site_dir)])
    assert r2.returncode == 0, r2.stdout + r2.stderr
    return export_dir, site_dir


class ReproducibleTests(unittest.TestCase):

    def test_two_clean_builds_byte_identical(self):
        with tempfile.TemporaryDirectory() as t1, \
                tempfile.TemporaryDirectory() as t2:
            _, site1 = export_and_build(Path(t1))
            _, site2 = export_and_build(Path(t2))
            h1, h2 = tree_hashes(site1), tree_hashes(site2)
            self.assertEqual(set(h1), set(h2), "file sets differ")
            diffs = [k for k in h1 if h1[k] != h2[k]]
            self.assertEqual(diffs, [], "differing files")

    def test_two_clean_exports_byte_identical(self):
        with tempfile.TemporaryDirectory() as t1, \
                tempfile.TemporaryDirectory() as t2:
            exp1, _ = export_and_build(Path(t1))
            exp2, _ = export_and_build(Path(t2))
            h1, h2 = tree_hashes(exp1), tree_hashes(exp2)
            self.assertEqual(set(h1), set(h2), "file sets differ")
            diffs = [k for k in h1 if h1[k] != h2[k]]
            self.assertEqual(diffs, [], "differing files")

    def test_manifest_checksums_match_files(self):
        import hashlib
        export_dir = fixture().export_dir
        manifest = json.loads((export_dir / "manifest.json")
                              .read_text(encoding="utf-8"))
        hashes = manifest["sha256"]
        checked = 0
        for fname, digest in hashes.items():
            f = export_dir / fname
            self.assertTrue(f.is_file(), f"manifest names missing {fname}")
            actual = hashlib.sha256(f.read_bytes()).hexdigest()
            self.assertEqual(actual, digest, f"checksum mismatch: {fname}")
            checked += 1
        self.assertGreaterEqual(checked, 9,
                                "manifest has no verifiable file checksums")

    def test_manifest_pins_contract_and_exporter_version(self):
        manifest = json.loads((fixture().export_dir / "manifest.json")
                              .read_text(encoding="utf-8"))
        self.assertRegex(manifest["contract_version"], r"^\d+\.\d+\.\d+$")
        self.assertRegex(manifest["exporter_version"], r"^\d+\.\d+\.\d+$")

    def test_validator_and_export_agree_on_row_counts(self):
        """The manifest's counts must match the exported CSV row counts."""
        manifest = json.loads((fixture().export_dir / "manifest.json")
                              .read_text(encoding="utf-8"))
        files = {"countries.csv": "country",
                 "organizations.csv": "organization",
                 "policy_families.csv": "policy_family",
                 "policy_versions.csv": "policy_version",
                 "manifestations.csv": "manifestation",
                 "provisions.csv": "provision",
                 "version_relationships.csv": "version_relationship",
                 "texts.csv": "text",
                 "version_functions.csv": "version_function"}
        for fname, entity in files.items():
            n_rows = len(read_csv(fixture().export_dir / fname))
            self.assertEqual(dict(manifest["record_counts"])[entity], n_rows,
                            f"manifest count wrong for {entity}")


if __name__ == "__main__":
    unittest.main()
