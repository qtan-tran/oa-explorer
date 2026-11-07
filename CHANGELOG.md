# Changelog

All notable changes to this repository. Format: Keep a Changelog; versioning:
the repository follows the plan's milestones, contract semver is separate.

## [0.4.2] - 2026-11-08
### Added (v0.3.2 exchange-contract draft: eight questions resolved, synthetic only)
- Draft exchange contract v0.3.2 (`contract/exchange/roara_contract_v0.3.2.schema.json`,
  `0.3.2-draft`, attached verbatim; not ratified). All fifteen prior exchange
  questions now resolved.
- `pipeline/exchange_v03_lib.py` v0.3.2 semantic layer: internal QC hold
  independent of release approval (Q2, local-only gitignored workbook);
  authority/source orthogonality + QC-conflict routing + evidence-only
  legacy enum migration (Q4); captured-HTML rights default unreviewed,
  link-only as affirmative reviewed decision (Q7); `languages` arrays
  with edition-vs-bilingual-file rules (Q10); physical page count vs
  printed label anchors + `pagination_note` (Q11); nullable `issuer_type`
  with identity review (Q12); `release.as_of` content cutoff vs nullable
  `published_at` (Q13); null `version_id` only for family-bound
  unrecovered leads (Q15).
- `synthetic/exchange_v032.json`: nine synthetic scenarios incl. draft
  PDF recovered, attested-approved without operative bytes, en/fr
  editions vs bilingual single file, 85-page PDF with physical p.56 /
  printed p.53, null-version family lead, unreviewed HTML capture.
  Ten-score numeric fields unpopulated; gates closed.
- Tests 31–33 (42 new; 272 total, all passing).
- `.gitignore` guard: `pilot_source_qc*.csv` never committed (test-enforced).
- `docs/plans/2026-11-08-exchange-v0.3.2-slice.md`: decision table,
  schema/semantic mismatches (incl. unsupported `allOf/if/then` handled
  semantically), test outcomes, remaining questions.

## [0.4.1] - 2026-11-08
### Added (v0.3.1 exchange-contract draft: corpus decisions, synthetic only)
- Draft exchange contract v0.3.1 (`contract/exchange/roara_contract_v0.3.1.schema.json`,
  `0.3.1-draft`, attached verbatim; not ratified; adds `publication_linked`,
  stricter cohort/archive/score descriptions). v0.3 schema retained.
- `pipeline/exchange_v03_lib.py` is now version-aware: in `0.3.1-draft`
  documents `publication_linked` derives only from `published` and
  `promulgation_linked` only from `promulgated`; disagreeing event dates
  are both preserved and only an explicit trigger may choose (unclear
  trigger = error). Public archive links require a `verified_bytes`
  snapshot plus link-rights and review gates (`url_only`/bare
  `archived_url` stay internal). Unknown-start cohorts are excluded from
  definite date-filtered claims; supported unbounded end
  (`not_applicable`) distinguished from unknown end. Score actor/action
  are the policy actor/evaluated action (null when mixed, basis
  provisions retained). Attested-but-unrecovered leads are excluded
  from comparison-eligible and public versions.
- `synthetic/exchange_v031.json`: adds synthetic BRIN Regulation
  12/2023 (promulgation_linked) and UPTC Agreement 2/2026
  (attested_unrecovered lead, adoption 2026-01-29 issuer-attested only);
  CO Resolution 0777 model switched to `publication_linked`.
  `public_release_approved: false`; no original files or excerpts.
- Tests 28–30 (27 new; 230 total, all passing).
- `docs/plans/2026-11-08-exchange-v0.3.1-slice.md`: schema delta + contradiction
  check (none found), test delta, unresolved fields, and the eight
  still-open v0.2 questions verbatim (Q2, Q4, Q7, Q10–Q13, Q15).

## [0.4.0] - 2026-11-08
### Added (v0.3 exchange-contract draft: six corpus decisions, synthetic only)
- Draft exchange contract v0.3 (`contract/exchange/roara_contract_v0.3.schema.json`,
  `0.3-draft`, attached verbatim from the owner's review; not ratified;
  v0.2 schema retained for migration reference).
- `pipeline/exchange_v03_lib.py` (+ CLI): reuses the v0.2 shape validator and
  enforces the six owner-reviewed decisions — score observations separate
  from provisions with no hardcoded labels and no composite (always
  withheld publicly until the ten-score codebook arrives); issuer
  `source_url` vs corroborated `archived_url`/`archive_snapshots`; typed
  cohort `event_type` triggers whose bounds never infer an effective
  date; `retrieved_at` as the only retrieval event (legacy
  `dateClaim.type=retrieved` rejected); explicit `duplicate_of_manifestation_id`
  aliases only on matching bytes/same version, counting one underlying
  manifestation; mandatory provision `cohort_applicability_status` +
  `cohort_ids` with `unknown` never displayed as "all cohorts".
- `synthetic/exchange_v03.json`: synthetic v0.3 fixture with
  `public_release_approved: false` (all public gates closed), incl. the
  Colombia Resolution 0777 structural regression case (signed 2022-08-03,
  Art. 3 effective on publication, gazette issue 52.243 of 2022-12-09,
  mirror + pending official host, resolution and annex as one version)
  and the UCT 2014-label/amended-2014-2016/2020 genealogy case (no clean
  2014 baseline or effective date inferred). No original files or
  excerpts imported.
- Tests 24–27 (52 cases): shape mutations, the six decisions, both
  regression cases, closed public gates, CLI. Suite total 203, all
  passing.
- `docs/plans/2026-11-08-exchange-v0.3-slice.md`: implementation report,
  v0.2→v0.3 migration table, resolution of v0.2 open questions Q1/Q3/Q5/Q6/
  Q8/Q9/Q14, unresolved fields; Q2/Q4/Q7/Q10–Q13/Q15 remain open.

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
