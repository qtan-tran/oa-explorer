# M3 (partial) — accessibility & test hardening on synthetic builds (Session 7, 2026-11-08)

Scope honesty: this session ran **only the offline-feasible part of M3**.
No browser, screen reader or network exists in this environment, so
axe-core scans, the manual keyboard-only walkthrough, the NVDA/VoiceOver
spot-check and the networked `check_links.py --check` remain **open** and
are not claimed. M2 (real-data pilot) stays blocked on U1 (reviewed Axis 2
export + explicit owner go); M4 publication untouched.

## What was added

- `tests/test_34_accessibility_deep.py` (M1 synthetic site):
  - WCAG contrast ratios **computed** from the shipped CSS (relative
    luminance per WCAG 2.2) for all text/background pairs — body, links,
    accent-on-accent, synthetic badge, header/thead, warning banner,
    `.meta`/`.gloss` — all asserted ≥ 4.5:1 (AA normal text).
  - viewport meta on every page; unique ids per page; no `href="#"` or
    empty hrefs; no inline event handlers on non-interactive elements;
    nav `aria-label`; skip-link target exists; static form controls
    labelled; JS-built search input verified to carry a wired `<label
    for="flt-search">`.
- `tests/test_35_exchange_a11y_links.py` (exchange reader site +
  link baseline):
  - same core structural checks on the exchange `index.html` (lang,
    skip link, landmarks, tabindex, unique ids, discernible link text);
  - transparency: withheld-count visible; no score observations and no
    64-hex hashes anywhere in the page;
  - `pipeline/check_links.py` offline inventory run against the synthetic
    public export as the dead-link **baseline** (≥8 URLs inventoried;
    networked `--check` stays a manual quarterly task, plan test 12).

## Test outcomes

- **288 tests, all passing** (was 272; +16 new).
- No source-code changes were needed: the M1/exchange markup already
  satisfied the deeper structural checks; the tests now lock that in.

## Still open for M3 (not claimed)

- axe-core scan in a real browser (zero critical violations target).
- Manual keyboard-only pass (list → filter → search → record → back) and
  one documented screen-reader spot check (NVDA or VoiceOver).
- Networked `check_links.py --check` on a network-enabled machine,
  quarterly, report attached to milestone review.
- Full corpus-scale local build for performance sanity (needs M2 data).

## How to verify

```
python3 -m unittest discover -s tests -t .   # 288 tests, all passing
```
