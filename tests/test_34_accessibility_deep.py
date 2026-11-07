"""Test 34 — M3 hardening: deeper WCAG 2.2 AA structural checks on the
synthetic M1 site.

Still NOT done (honest): axe-core in a real browser, a manual keyboard-only
walkthrough, and a screen-reader spot check — no browser/SR exists in this
offline environment. These tests extend the automated structural net:
contrast ratios computed per WCAG, form labelling, landmark/ARIA
correctness, no fake links, unique ids, viewport.
"""
import re
import unittest

try:
    from tests.util import APPROVED_VERSIONS, fixture, site_page
except ImportError:  # pragma: no cover
    from util import APPROVED_VERSIONS, fixture, site_page

PAGES = ["index.html", "about.html"] + [f"record/{vid}.html"
                                        for vid in APPROVED_VERSIONS]


def _lum(hexcolor: str) -> float:
    h = hexcolor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    def chan(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def contrast(fg: str, bg: str) -> float:
    l1, l2 = sorted((_lum(fg), _lum(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


class ContrastTests(unittest.TestCase):
    """WCAG 2.2 AA: normal text needs >= 4.5:1. Computed from the shipped
    CSS variables and hardcoded text colours, not asserted by hand."""

    def _vars(self):
        css = (fixture().site_dir / "static" / "style.css"
               ).read_text(encoding="utf-8")
        root = css[css.index(":root"):css.index("}", css.index(":root"))]
        return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", root))

    def test_text_colour_pairs_meet_aa(self):
        v = self._vars()
        pairs = [
            (v["ink"], v["paper"]),            # body text
            (v["accent"], v["paper"]),         # links
            (v["accent-ink"], v["accent"]),    # text on accent
            (v["synth-ink"], v["synth-bg"]),   # synthetic badge
            (v["ink"], v["soft"]),             # header/footer/thead
            (v["ink"], v["warn-bg"]),          # warning banner
            ("#444444", v["paper"]),           # .meta/.verbatim
            ("#333333", v["paper"]),           # .gloss
        ]
        for fg, bg in pairs:
            ratio = contrast(fg, bg)
            self.assertGreaterEqual(
                ratio, 4.5,
                f"contrast {fg} on {bg} = {ratio:.2f}:1 < 4.5:1 (AA)")


class StructureTests(unittest.TestCase):
    def test_viewport_meta_every_page(self):
        for p in PAGES:
            self.assertIn('name="viewport"', site_page(p), p)

    def test_ids_are_unique_per_page(self):
        for p in PAGES:
            html = site_page(p)
            ids = re.findall(r'\bid="([^"]+)"', html)
            dupes = {i for i in ids if ids.count(i) > 1}
            self.assertEqual(dupes, set(), f"{p}: duplicate ids {dupes}")

    def test_no_placeholder_links_or_hash_hrefs(self):
        for p in PAGES:
            html = site_page(p)
            self.assertNotIn('href="#"', html, p)
            for m in re.finditer(r'<a\b[^>]*href="([^"]*)"', html):
                self.assertTrue(m.group(1).strip(), f"{p}: empty href")

    def test_no_inline_handlers_on_noninteractive_elements(self):
        for p in PAGES:
            html = site_page(p)
            for m in re.finditer(
                    r"<(div|span|p|li|td|h[1-6])\b[^>]*on(click|mouseover|"
                    r"keydown)\w*=", html):
                self.fail(f"{p}: inline handler on <{m.group(1)}>")

    def test_nav_has_aria_label_and_current_page(self):
        for p in PAGES:
            html = site_page(p)
            nav = re.search(r"<nav\b[^>]*>", html).group(0)
            self.assertIn("aria-label=", nav, f"{p}: nav without aria-label")

    def test_skip_link_target_exists(self):
        for p in PAGES:
            html = site_page(p)
            self.assertIn('id="main"', html, f"{p}: #main missing")

    def test_static_form_controls_are_labelled(self):
        """Any select/input present in the static HTML (as opposed to the
        JS-built filter bar) must have an associated label."""
        for p in PAGES:
            html = site_page(p)
            for m in re.finditer(r"<(select|input)\b[^>]*>", html):
                tag = m.group(0)
                idm = re.search(r'\bid="([^"]+)"', tag)
                if idm:
                    self.assertIn(f'for="{idm.group(1)}"', html,
                                  f"{p}: control {idm.group(1)} unlabelled")
                else:
                    self.fail(f"{p}: control without id cannot be "
                              f"labelled: {tag}")

    def test_search_input_has_label_or_aria(self):
        # the search box is built by explorer.js; its label must be wired
        js = (fixture().site_dir / "static" / "explorer.js"
              ).read_text(encoding="utf-8")
        self.assertIn('search.id = "flt-search"', js)
        self.assertIn('searchLb.setAttribute("for", "flt-search")', js)
        self.assertIn('searchLb.textContent = "Search titles and issuers"',
                      js)
        self.assertIn('search.type = "search"', js)


if __name__ == "__main__":
    unittest.main()
