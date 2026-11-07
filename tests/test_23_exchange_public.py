"""Test 23 — exchange v0.2 public gating, display toggles, and the
reader site build.

Gates: only analyst_checked / independently_reviewed versions and only
rights-passing manifestations appear; links, downloads and excerpts are
independently configurable; technical collection columns never surface;
the build is deterministic.
"""
import json
import sys
import unittest

try:
    from tests.util import (EXCHANGE_HIDDEN_MANIFESTATIONS,
                            EXCHANGE_HIDDEN_VERSIONS,
                            EXCHANGE_PUBLIC_VERSIONS, exchange_fixture,
                            load_exchange_doc, tree_hashes)
except ImportError:  # pragma: no cover
    from util import (EXCHANGE_HIDDEN_MANIFESTATIONS,
                      EXCHANGE_HIDDEN_VERSIONS, EXCHANGE_PUBLIC_VERSIONS,
                      exchange_fixture, load_exchange_doc, tree_hashes)

REPO = sys.path[0] if sys.path[0] else "."
sys.path.insert(0, REPO + "/pipeline" if not REPO.endswith("pipeline")
                else REPO)
import exchange_lib as xl  # noqa: E402

FAKE_HASHES = ["11" * 32, "22" * 32, "33" * 32, "44" * 32, "55" * 32,
               "66" * 32, "77" * 32, "88" * 32, "99" * 32]


def find_version(doc, vid):
    return next(v for v in doc["versions"] if v["id"] == vid)


def find_manifestation(doc, mid):
    return next(m for m in doc["manifestations"] if m["id"] == mid)


class PublicGating(unittest.TestCase):
    def test_six_public_four_withheld(self):
        fx = exchange_fixture()
        self.assertTrue(fx.views["release_approved"])
        self.assertEqual(len(fx.views["records"]), 6)
        self.assertEqual(fx.views["withheld_count"], 4)
        self.assertEqual(sorted(r["id"] for r in fx.views["records"]),
                         sorted(EXCHANGE_PUBLIC_VERSIONS))

    def test_withheld_ids_absent_from_model_and_html(self):
        fx = exchange_fixture()
        blob = fx.index_html + json.dumps(fx.views)
        for vid in EXCHANGE_HIDDEN_VERSIONS:
            self.assertNotIn(vid, blob)
        for mid in EXCHANGE_HIDDEN_MANIFESTATIONS:
            self.assertNotIn(mid, blob)

    def test_technical_columns_never_surface(self):
        fx = exchange_fixture()
        blob = fx.index_html + json.dumps(fx.views)
        for h in FAKE_HASHES:
            self.assertNotIn(h, blob)
        self.assertNotIn('"sha256"', json.dumps(fx.views))
        # reviewer identity and review extent are not exported
        for r in fx.views["records"]:
            self.assertNotIn("reviewer", r)
            self.assertNotIn("extent", r)

    def test_version_review_flip_hides_record(self):
        doc = load_exchange_doc()
        find_version(doc, "V-BOR-REPO-2016")["review"] = {
            "state": "conflicted"}
        views = xl.build_public_views(doc, xl.PublicConfig())
        ids = [r["id"] for r in views["records"]]
        self.assertNotIn("V-BOR-REPO-2016", ids)
        self.assertEqual(views["withheld_count"], 5)

    def test_manifestation_rights_flip_hides_sources_not_record(self):
        doc = load_exchange_doc()
        find_manifestation(doc, "M-BOR-REPO-2016-PDF")["rights_status"] = \
            "internal_only"
        views = xl.build_public_views(doc, xl.PublicConfig())
        rec = next(r for r in views["records"]
                   if r["id"] == "V-BOR-REPO-2016")
        self.assertEqual(rec["sources"], [])
        # its provision disappears too (evidence manifestation hidden)
        self.assertEqual(rec["provisions"], [])

    def test_unapproved_release_withholds_everything(self):
        doc = load_exchange_doc()
        doc["release"]["public_release_approved"] = False
        views = xl.build_public_views(doc, xl.PublicConfig())
        self.assertFalse(views["release_approved"])
        self.assertEqual(views["records"], [])
        self.assertEqual(views["withheld_count"], 10)


class DisplayToggles(unittest.TestCase):
    def get_record(self, views, vid):
        return next(r for r in views["records"] if r["id"] == vid)

    def test_links_toggle(self):
        doc = load_exchange_doc()
        on = xl.build_public_views(doc, xl.PublicConfig(document_links=True))
        off = xl.build_public_views(doc, xl.PublicConfig(document_links=False))
        rec_on = self.get_record(on, "V-MAR-OA-2011")
        rec_off = self.get_record(off, "V-MAR-OA-2011")
        self.assertTrue(rec_on["sources"][0]["url"])
        self.assertIsNone(rec_off["sources"][0]["url"])
        # record itself still shown
        self.assertEqual(len(off["records"]), 6)

    def test_downloads_default_off_and_selective_on(self):
        doc = load_exchange_doc()
        default = xl.build_public_views(doc, xl.PublicConfig())
        for r in default["records"]:
            for s in r["sources"]:
                self.assertIsNone(s["download_url"])
        on = xl.build_public_views(doc, xl.PublicConfig(downloads=True))
        downloads = {(r["id"], s["url"]) for r in on["records"]
                     for s in r["sources"] if s["download_url"]}
        # only the redistribution-approved controlling original of
        # V-BOR-BNRA-012-2023 is downloadable
        self.assertEqual(downloads, {
            ("V-BOR-BNRA-012-2023",
             "https://example.org/bnra/regulation-012-2023.pdf")})

    def test_excerpts_rights_withhold_but_keep_anchor_and_reason(self):
        doc = load_exchange_doc()
        views = xl.build_public_views(doc, xl.PublicConfig())
        rec = self.get_record(views, "V-MAR-OA-2011")
        withheld = next(p for p in rec["provisions"]
                        if p["anchor"].startswith("§ 3"))
        self.assertIsNone(withheld["original_excerpt"])
        self.assertEqual(withheld["excerpt_withheld_reason"],
                         "rights_not_approved")
        self.assertIsNotNone(withheld["actor"])  # clause analysis stays

    def test_excerpts_toggle_off_hides_even_approved_excerpts(self):
        doc = load_exchange_doc()
        off = xl.build_public_views(doc, xl.PublicConfig(excerpts=False))
        rec = self.get_record(off, "V-ARC-GRANT-2020")
        p = rec["provisions"][0]
        self.assertIsNone(p["original_excerpt"])
        self.assertEqual(p["excerpt_withheld_reason"], "excerpts_disabled")

    def test_hidden_counterpart_in_relationship(self):
        doc = load_exchange_doc()
        views = xl.build_public_views(doc, xl.PublicConfig())
        rec = self.get_record(views, "V-BOR-TRI-2026")
        rel = rec["relationships"][0]
        self.assertTrue(rel["other_withheld"])
        self.assertIsNone(rel["other_version"])


class ReaderSite(unittest.TestCase):
    def test_cli_build_exit_zero(self):
        fx = exchange_fixture()
        self.assertEqual(fx.build.returncode, 0, fx.build.stderr)

    def test_html_contents(self):
        fx = exchange_fixture()
        # whitespace-normalised copy: phrase checks must survive the
        # template's own line wrapping
        page = fx.index_html
        flat = " ".join(page.split())
        # synthetic banner
        self.assertIn("SYNTHETIC DEMONSTRATION DATA", page)
        # function strata as separate sections
        for label in ("Institutional OA/OS policy", "Funder grant terms",
                      "Repository rules", "Research data governance",
                      "Announcement"):
            self.assertIn(label, page)
        # unknown effective display rendered
        self.assertIn("Unknown / not established", page)
        # withheld note
        self.assertIn("4 of 10 records are withheld", page)
        # no prevalence / ranking beyond the explicit disclaimer
        self.assertIn("no country prevalence", flat)
        self.assertIn("no ranking", flat)
        self.assertNotIn("prevalence:", flat)
        # accessibility basics: skip link, landmarks, lang
        self.assertIn('class="skip-link"', page)
        self.assertIn('<html lang="en">', page)
        self.assertIn('role="banner"', page)
        self.assertIn('role="main"', page)
        # no fake hash anywhere in the HTML
        for h in FAKE_HASHES:
            self.assertNotIn(h, page)
        # no positive tabindex
        self.assertNotIn("tabindex=", page)

    def test_two_builds_byte_identical(self):
        fx = exchange_fixture()
        cp, out = fx.build_variant()
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual(tree_hashes(out), tree_hashes(fx.site_dir))


if __name__ == "__main__":
    unittest.main()
