"""Test 8 — automated accessibility checks (static analysis of the built
HTML/CSS/JS). These catch structural WCAG 2.2 regressions; they do NOT
replace a manual keyboard and screen-reader pass, which has NOT been
performed for M1 and is documented as an open limitation."""
import re
import unittest

try:
    from tests.util import APPROVED_VERSIONS, fixture, site_page  # noqa: F401
except ImportError:
    from util import APPROVED_VERSIONS, fixture, site_page  # noqa: F401

PAGES = ["index.html", "about.html"] + [f"record/{vid}.html"
                                        for vid in APPROVED_VERSIONS]


class AccessibilityTests(unittest.TestCase):

    def test_html_lang_attribute_every_page(self):
        for p in PAGES:
            html = site_page(p)
            m = re.search(r"<html[^>]*\slang=\"([^\"]+)\"", html)
            self.assertTrue(m, f"{p}: missing lang on <html>")

    def test_skip_link_is_first_focusable_element(self):
        for p in PAGES:
            html = site_page(p)
            body = html[html.index("<body"):]
            first_interactive = re.search(
                r"<a\b[^>]*>.*?</a>", body, re.S)
            self.assertTrue(first_interactive, f"{p}: no interactive element")
            self.assertIn("Skip to main content",
                          re.sub(r"<[^>]+>", "", first_interactive.group(0)),
                          f"{p}: skip link is not first focusable element")
            self.assertIn('href="#main"', first_interactive.group(0),
                          f"{p}: skip link target")

    def test_landmarks_present(self):
        for p in PAGES:
            html = site_page(p)
            self.assertIn("<main", html, f"{p}: no main landmark")
            self.assertIn("<nav", html, f"{p}: no nav landmark")
            self.assertIn('id="main"', html, f"{p}: main has no id")

    def test_heading_order_no_skipped_levels(self):
        for p in PAGES:
            html = site_page(p)
            levels = [int(m.group(1)) for m in
                      re.finditer(r"<h([1-6])\b", html)]
            self.assertTrue(levels, f"{p}: no headings")
            self.assertEqual(levels[0], 1, f"{p}: page must open with h1")
            for prev, cur in zip(levels, levels[1:]):
                self.assertLessEqual(cur, prev + 1,
                                     f"{p}: heading level jump "
                                     f"h{prev}->h{cur}")

    def test_no_positive_tabindex(self):
        for p in PAGES:
            html = site_page(p)
            self.assertNotRegex(
                html, r'tabindex="[1-9]',
                f"{p}: positive tabindex is forbidden")

    def test_focus_visible_css(self):
        css = (fixture().site_dir / "static" / "style.css"
               ).read_text(encoding="utf-8")
        self.assertIn(":focus-visible", css)
        self.assertRegex(css, r"outline:\s*\S+", "focus indicator styles")

    def test_svg_charts_have_role_title_desc(self):
        for p in PAGES:
            html = site_page(p)
            for svg in re.finditer(r"<svg\b[^>]*>", html):
                self.assertIn('role="img"', svg.group(0),
                              f"{p}: svg without role=img")
                block = html[svg.start():svg.start() + 2000]
                self.assertIn("<title", block, f"{p}: svg without <title>")
                self.assertIn("<desc", block, f"{p}: svg without <desc>")

    def test_tables_have_headers_and_caption(self):
        for p in PAGES:
            html = site_page(p)
            for table in re.finditer(r"<table[^>]*>(.*?)</table>",
                                     html, re.S):
                block = table.group(0)
                self.assertIn("<th", block, f"{p}: table without th")
                self.assertIn("<caption", block, f"{p}: table without caption")
                for th in re.finditer(r"<th\b([^>]*)>", block):
                    self.assertRegex(th.group(1), r'scope="(col|row)"',
                                     f"{p}: th without scope")
                if "<thead" in block:
                    self.assertIn('scope="col"', block,
                                  f"{p}: data table without col scope")

    def test_filter_controls_get_labels_in_js(self):
        js = (fixture().site_dir / "static" / "explorer.js"
              ).read_text(encoding="utf-8")
        # every dynamically created select/input must get a <label for=...>
        self.assertEqual(js.count('createElement("label")'),
                         js.count('setAttribute("for"'))
        self.assertIn('aria-live="polite"', site_page("index.html"))

    def test_links_have_discernible_text(self):
        """No bare 'click here' link text; no empty anchors."""
        for p in PAGES:
            html = site_page(p)
            for m in re.finditer(r"<a\b[^>]*>(.*?)</a>", html, re.S):
                text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
                self.assertTrue(text, f"{p}: empty link text")
                low = text.lower()
                self.assertNotIn(low, ("click here", "here", "more"),
                                f"{p}: vague link text {text!r}")

    def test_images_have_alt(self):
        for p in PAGES:
            html = site_page(p)
            for m in re.finditer(r"<img\b[^>]*>", html):
                self.assertIn("alt=", m.group(0), f"{p}: img without alt")


if __name__ == "__main__":
    unittest.main()
