"""Test 3 — status/null semantics: value_state invariants, the four-way
distinction unknown / not_applicable / reviewed_absent / measured zero,
and lossless CSV→JSON→CSV round trips."""
import copy
import json
import sys
import unittest

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
    return data, schemas


def errors_for(data):
    return cl.validate_dataset(data, CONTRACT, label="mutated-copy")


class SemanticsTests(unittest.TestCase):

    def test_value_without_measured_state_rejected(self):
        data, _ = load_copy()
        for org in data["organization"]:
            if org["org_id"] == "O-XB-0002":  # reviewed absence: has_policy N
                org["has_policy_value_state"] = "unknown"
        errs = errors_for(data)
        self.assertTrue(any("has_policy" in e for e in errs), errs)

    def test_measured_state_with_empty_value_rejected(self):
        data, _ = load_copy()
        for org in data["organization"]:
            if org["org_id"] == "O-XB-0002":
                org["has_policy"] = ""
        errs = errors_for(data)
        self.assertTrue(any("has_policy" in e for e in errs), errs)

    def test_numeric_zero_is_a_valid_measured_value(self):
        """comp_compliance = 0 with state measured must validate, and must
        stay distinguishable from unknown and from reviewed absence."""
        data, _ = load_copy()
        v = [r for r in data["policy_version"]
             if r["version_id"] == "V-XA-0001"][0]
        self.assertEqual(v["score_comp_compliance"], "0")
        self.assertEqual(v["score_comp_compliance_value_state"], "measured")
        self.assertEqual(errors_for(data), [])

    def test_unknown_score_state(self):
        data, _ = load_copy()
        v = [r for r in data["policy_version"]
             if r["version_id"] == "V-XB-0001"][0]
        for d in ["ms_mandate_strength", "rl_rights_licensing",
                  "comp_compliance", "inf_infrastructure", "fund_funding",
                  "repo_repository", "eval_evaluation", "mon_monitoring",
                  "gov_governance", "osb_os_breadth"]:
            self.assertEqual(v[f"score_{d}"], "")
            self.assertEqual(v[f"score_{d}_value_state"], "unknown")
        # all-unknown version: no family mean, no composite
        self.assertEqual(v["derived_family_normative_force"], "")
        self.assertEqual(v["derived_composite_0_30"], "")

    def test_composite_only_when_all_ten_measured(self):
        data, _ = load_copy()
        v = [r for r in data["policy_version"]
             if r["version_id"] == "V-XA-0002"][0]
        self.assertEqual(v["derived_composite_0_30"], "21")  # 10/10 measured
        # Break one dimension: composite must disappear, not be recomputed.
        v["score_eval_evaluation"] = ""
        v["score_eval_evaluation_value_state"] = "unknown"
        errs = errors_for(data)
        self.assertTrue(any("composite" in e.lower() for e in errs), errs)

    def test_not_applicable_distinct_from_unknown(self):
        data, _ = load_copy()
        v = [r for r in data["policy_version"]
             if r["version_id"] == "V-XA-0003"][0]
        self.assertEqual(v["score_eval_evaluation"], "")
        self.assertEqual(v["score_eval_evaluation_value_state"],
                         "not_applicable")

    def test_review_state_vocabulary_enforced(self):
        data, _ = load_copy()
        data["policy_version"][0]["review_state"] = "magic"
        errs = errors_for(data)
        self.assertTrue(any("review_state" in e for e in errs), errs)

    def test_round_trip_preserves_all_null_semantics(self):
        """CSV → JSON → CSV must be byte-equal for every entity, keeping
        unknown, not_applicable, reviewed_absent and measured zero distinct."""
        data, schemas = load_copy()
        js = cl.dataset_to_json(data, schemas)
        restored = cl.dataset_from_json(js, schemas)
        self.assertEqual(restored, data)

    def test_round_trip_through_json_string_preserves_zero_vs_empty(self):
        data, schemas = load_copy()
        js = json.loads(cl.dataset_to_json(data, schemas))
        js_v = js["policy_version"]["V-XA-0001"]
        self.assertEqual(js_v["score_comp_compliance"], "0")  # numeric zero
        self.assertEqual(js_v["derived_composite_0_30"], "")  # not computed
        self.assertNotEqual(js_v["score_comp_compliance"], "")


if __name__ == "__main__":
    unittest.main()
