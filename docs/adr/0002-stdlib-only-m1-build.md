# ADR 0002 — Standard-library-only build and test toolchain for M1

- **Status:** Accepted (2026-11-08, M1)
- **Deciders:** Repository owner (Quoc-Tan Tran) with implementing agent
- **Supersedes:** none; refines the implementation choice in
  [ADR 0001](0001-static-data-driven-explorer.md)
- **Date:** 2026-11-08

## Context

ADR 0001 chose a pre-rendered, data-driven static site (Python build script
+ template engine) over a server-backed or JS-framework alternative. Its
default implementation stack named Python + **Jinja2** as the template
engine and **pytest** as the likely test runner.

During M1 implementation, the build environment available for the session
did not permit installing third-party Python packages. Rather than block the
milestone, we evaluated whether the milestone's needs actually require any
third-party dependency at all.

## Decision

1. The M1 pipeline, site generator, exporter and tests use **only the
   Python standard library** (Python ≥ 3.11; developed against 3.12):
   - `string.Template` for page templating (two templates, no inheritance);
   - `unittest` for tests (run via `python3 -m unittest discover -s tests -t .`);
   - `csv`, `json`, `hashlib`, `argparse`, `pathlib` for the pipeline.
2. `pipeline/requirements.txt` records this decision and contains **no
   third-party pins**. If Jinja2 is adopted later, exact pins get added
   there (e.g. `Jinja2==3.1.4`), not before.
3. **Jinja2 remains the documented fallback**, not the M1 choice: if
   templates grow real logic (conditionals, loops over nested structures,
   filters), migrate to Jinja2 in a dedicated refactor. Migration cost is
   low because all template data is already passed as plain dictionaries
   and the template surface is small.
4. No JavaScript build step: `site/static/explorer.js` is plain,
   syntax-checked, progressively enhancing script (unminified, no
   framework, no network calls beyond fetching `index.json` from the same
   origin).

## Consequences

**Positive**

- **Ten-year maintainability improves**: zero dependencies means zero
  dependency-security advisories, zero breaking releases, zero
  supply-chain updates, and no lockfile rot for the core of the project.
  This directly serves the plan's portability goal (plan §1).
- Install, validate, build and test all run with one command on any
  machine with a modern Python, fully offline.
- Reproducibility is easier to guarantee (test 10 asserts byte-identical
  rebuilds).

**Negative / risks**

- `string.Template` is weaker than Jinja2: no autoescaping (we call
  `html.escape` explicitly at every interpolation; tested by the canary
  test 05 and a dedicated escaping discipline), no filters, no
  inheritance. Template complexity is capped by convention; when that cap
  breaks, migrate (point 3).
- `unittest` is more verbose than pytest; acceptable at ~90 assertions.
- The zero-dependency choice is unusual for HTML generation and must be
  revisited if the site gains real interactive features in M3+.

## Compliance

- WCAG output is unaffected: accessibility lives in the generated HTML/CSS
  and the JS enhancement, not in the template engine.
- The sandbox constraint that motivated this ADR is recorded honestly: it
  is an environment constraint, not a claim that Jinja2 is unavailable in
  general. The fallback path exists precisely because the constraint may
  not apply to the owner's local machine or CI.
