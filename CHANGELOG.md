# Changelog

All notable changes to this repository. Format: Keep a Changelog; versioning:
the repository follows the plan's milestones, contract semver is separate.

## [0.3.0] - 2026-11-08
### Added (v0.2 exchange-contract vertical slice, synthetic data only)
- Draft exchange contract v0.2 (`contract/exchange/roara_contract_v0.2.schema.json`,
  `0.2-draft`, copied verbatim from the corpus project's design fixture;
  not ratified). The internal pilot QC workbook is never committed.
- `pipeline/exchange_lib.py`: JSON-Schema-subset shape validation;
  cross-reference validation (FK integrity, provision evidence must
  bind to a manifestation of the same version, `component_of` chains,
  relationship acyclicity); duplicate source-hash rules (same-version
  mirrors legal, cross-version/translation duplicates errors); typed
  date-claim semantics (cohort thresholds never infer general
  effective dates; promulgation/approval linkage declared, not
  silent); rights/review-gated public reader views with independently
  configurable document links, downloads and excerpts; technical
  collection columns (hashes, reviewer identity) never exported.
- `synthetic/exchange_v02.json`: fictional exchange fixture (10
  versions, 12 manifestations, 8 provisions, 2 relationships) covering
  the QC structural scenarios: call-opened cohort, dual award cohorts
  (bounded + open-ended), effective-on-promulgation, signed resolution
  + annex, mutable HTML captures, legal mirror duplicate hash,
  explicit-effective contrast.
- `site/build_exchange.py`: deterministic static reader site grouped by
  function stratum (institutional / funder / national strategy /
  repository / APC / research data governance / announcement kept
  separate; no country prevalence, ranking or composite score);
  "Unknown / not established" effective-date display.
- Tests 20–23 (63 cases): shape mutations, cross-reference and
  duplicate-hash rules, the four QC date scenarios, gating/toggle
  behaviour, determinism. Suite total 151, all passing.
- `docs/plans/2026-11-08-exchange-v0.2-slice.md`: implementation
  report, v0.1→v0.2 migration note, 15 open questions for the corpus
  thread.

## [0.2.0] - 2026-11-08
### Added (Milestone M1: local vertical slice, synthetic data only)
- Contract layer: 9 JSON Schemas (draft 2020-12, `x-column-order`),
  vocabularies, public-field allowlist, v1 legacy mapping; contract
  version 0.1.0 DRAFT; `data_origin` column proposed pending ratification.
- Pipeline (stdlib only): `contract_lib.py` (schema/vocabulary/value-state/
  date/permission/FK/cycle/derived-value validation, CSV↔JSON round trip),
  `export_ledger.py` validator CLI, `build_public.py` allowlist+approval
  exporter v0.2.0 (non-public manifestations and bound provisions withheld
  with derived summaries; not-permitted excerpts blanked; manifest with
  per-file sha256, counts, synthetic flag), `check_links.py` offline link
  inventory.
- Synthetic seed corpus (64 rows, 9 files, all `data_origin=synthetic`,
  user-assigned ISO codes XA/XB, example.org URLs) covering the six
  required demo cases; planted permission-filter canary.
- Static site generator (stdlib `string.Template`; ADR 0002): filters and
  search (country, issuer type, function, year, OA/OS scope, source
  status), record pages with relationships, original-language evidence,
  physical anchors, ten-dimension profile, chart with stated denominator
  and excluded strata, purposive-sampling and limitations pages, CSV +
  manifest downloads; WCAG-minded markup (skip link, landmarks, focus
  styles, labels, svg title/desc); no-JS content complete.
- Test suite: 88 automated checks in 10 modules (schema, integrity,
  semantics, dates, permissions, relationships, site, accessibility
  structure, charts/denominators, reproducible builds) — all passing.
- ADR 0002 (stdlib-only toolchain, Jinja2 fallback), M1 implementation
  report, continuation note (M2 + expected Axis 2 data handoff),
  `docs/handover.md`, `synthetic/README.md`, README quickstart.
### Fixed (found by the new tests during M1)
- CSV↔JSON round trip collapsed composite-key rows (bilingual texts).
- Public export wrote all schema columns (disallowed ones as empty
  columns); now exactly the allowlisted subset.
- `vocabularies.csv` stale `Unclear` term removed (legacy mapping covers
  it; schema enum excludes it).
- Record-page header/footer/style links were root-relative and broken
  from `record/`; now root-prefixed per page.
- `index.html` lacked an `h1`; `manifest.json` lacked per-file checksums.
- `check_links.py` could not read the allowlist-projected export (strict
  schema reader); now reads the export tolerantly (8 URLs inventoried).
### Not done (honest)
- Plan §7 tests 11–14 (browser interaction, keyboard walkthrough,
  screen-reader pass, networked dead-link run): open for M3.
- No real corpus data, no publication, no push; GitHub state untouched.

## [0.1.0] - 2026-11-07
### Added
- Planning session 1 (planning only; no application code, no data).
- Repository `oa-explorer` created public by the owner; planning documents
  committed to main (decisions D1–D4 recorded in the plan).
- Master plan: milestones M0–M5 with acceptance tests and rollback, target
  repository layout, data pipeline, test plan, ten-year maintenance checklist,
  risks, assumptions, inspection record of the corpus repository.
- ADR 0001: pre-rendered static site (Python + Jinja2) on GitHub Pages when
  authorized; rejected alternative documented; provider limits checked
  against official docs on 2026-11-07; costs and portable alternatives.
- Data contract v0.1 DRAFT: entities (country, organization, policy family,
  policy version, manifestation, provision, relationship), stable IDs,
  value_state null/status semantics, date precision blocks, per-manifestation
  permissions, provenance, public export vs local private ledger, schema
  versioning/validation/migration, mapping from the 56-column v1 schema,
  open questions OQ1–OQ8 for the corpus team.
- AGENTS.md working rules; MIT (code) and CC BY 4.0 (docs) licences.
