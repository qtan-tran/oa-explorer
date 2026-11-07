"""Test 4 — date precision: partial dates survive the pipeline without an
invented day, adopted vs effective stay distinct, verbatim wording is
preserved, and day precision demands a full date."""
import sys
import unittest

try:
    from tests.util import CONTRACT, REPO, fixture, read_csv_by_id  # noqa: F401
except ImportError:
    from util import CONTRACT, REPO, fixture, read_csv_by_id  # noqa: F401

sys.path.insert(0, str(REPO / "pipeline"))
import contract_lib as cl  # noqa: E402


def load_copy():
    schemas = cl.load_schemas(CONTRACT)
    data, load_errors = cl.load_dataset(REPO / "synthetic", schemas)
    assert not load_errors, load_errors
    return data


def errors_for(data):
    return cl.validate_dataset(data, CONTRACT, label="mutated-copy")


class DateTests(unittest.TestCase):

    def test_year_precision_survives_export_without_invented_day(self):
        rows = read_csv_by_id(fixture().export_dir / "policy_versions.csv",
                              "version_id")
        v = rows["V-XA-0001"]
        self.assertEqual(v["adopted_date_iso"], "2020")
        self.assertEqual(v["adopted_date_precision"], "year")
        self.assertNotIn("2020-01-01", v["adopted_date_iso"])

    def test_month_precision_survives_export(self):
        rows = read_csv_by_id(fixture().export_dir / "policy_versions.csv",
                              "version_id")
        v = rows["V-XB-0001"]
        self.assertEqual(v["adopted_date_iso"], "2023-03")
        self.assertEqual(v["adopted_date_precision"], "month")

    def test_verbatim_wording_preserved(self):
        rows = read_csv_by_id(fixture().export_dir / "policy_versions.csv",
                              "version_id")
        self.assertIn("Tag nicht angegeben",
                      rows["V-XA-0001"]["adopted_date_verbatim"])
        self.assertIn("März 2023",
                      rows["V-XB-0001"]["adopted_date_verbatim"])

    def test_adopted_unknown_effective_known(self):
        """Adoption and effective dates are distinct facts: one can be
        unknown while the other is a full date."""
        rows = read_csv_by_id(fixture().export_dir / "policy_versions.csv",
                              "version_id")
        v = rows["V-XA-0003"]
        self.assertEqual(v["adopted_date_iso"], "")
        self.assertEqual(v["adopted_date_precision"], "")
        self.assertEqual(v["effective_date_iso"], "2021-01-01")
        self.assertEqual(v["effective_date_precision"], "day")
        self.assertIn("not stated", v["adopted_date_verbatim"])

    def test_adoption_and_effective_both_present_and_distinct(self):
        rows = read_csv_by_id(fixture().export_dir / "policy_versions.csv",
                              "version_id")
        v = rows["V-XA-0002"]
        self.assertEqual(v["adopted_date_iso"], "2024-06-15")
        self.assertEqual(v["effective_date_iso"], "2024-10-01")
        self.assertNotEqual(v["adopted_date_iso"], v["effective_date_iso"])

    def test_day_precision_requires_full_date(self):
        data = load_copy()
        v = [r for r in data["policy_version"]
             if r["version_id"] == "V-XA-0001"][0]
        v["adopted_date_precision"] = "day"  # but value is "2020"
        errs = errors_for(data)
        self.assertTrue(any("adopted" in e.lower() for e in errs), errs)

    def test_month_precision_requires_month_value(self):
        data = load_copy()
        v = [r for r in data["policy_version"]
             if r["version_id"] == "V-XA-0001"][0]
        v["adopted_date_precision"] = "month"  # but value is "2020"
        errs = errors_for(data)
        self.assertTrue(any("adopted" in e.lower() for e in errs), errs)

    def test_no_invented_day_in_site_json(self):
        import json
        d = json.loads((fixture().site_dir / "index.json")
                       .read_text(encoding="utf-8"))
        v = {r["version_id"]: r for r in d["versions"]}
        self.assertEqual(v["V-XA-0001"]["adopted_year"], "2020")
        self.assertEqual(v["V-XA-0001"]["adopted_precision"], "year")
        self.assertIsNone(v["V-XA-0003"]["adopted_year"])  # unknown, not 0/1900

    def test_record_page_shows_precision_not_fake_day(self):
        html = (fixture().site_dir / "record" / "V-XA-0001.html"
                ).read_text(encoding="utf-8")
        self.assertIn("precision: year", html)
        self.assertIn("2020", html)
        self.assertNotIn("2020-01-01", html)


if __name__ == "__main__":
    unittest.main()
