# Synthetic demonstration corpus

Every file in this directory is **entirely fictional demonstration data**.

- All rows carry `data_origin=synthetic` and appear with a visible
  SYNTHETIC badge/banner in every built page and in `manifest.json`
  (`contains_synthetic_records: true`).
- Countries use ISO 3166-1 **user-assigned** codes `XA` (Republic of
  Arcadia, bilingual de/en) and `XB` (Kingdom of Borealia). No real
  country, institution, funder, repository or policy is described.
- All URLs use the reserved domains `example.org` / `example-archive.org`;
  they resolve to nothing by design.
- Purpose: exercising the data contract, the validator, the public
  exporter's permission/approval gates and the site templates **before
  any real corpus data passes through them**. The six required demo
  cases (replaced version, unrecovered source, partial dates, conditional
  provision, two languages, reviewed absence vs unknown) live here; see
  the M1 implementation report for the mapping.
- One deliberate planted marker, `SYNTHETIC-CANARY-PRIVATE-MARKER-9F2`,
  sits in fields that must never reach a public export (a draft version's
  withhold reason, a not-permitted excerpt, a private permission note).
  The permission tests (tests/test_05_permissions.py) fail loudly if it
  ever leaks into `exports/` or `_site/`.
- This corpus is never merged with real data. Real pilot data arrives in
  a local, gitignored `ledger/` directory (continuation note), validated
  separately, and only its `approved_public` rows are exported.
- Do not use these records to test claims about real countries, and do
  not cite them.

## Exchange fixture (Session 3)

- `exchange_v02.json` is the **synthetic demonstration exchange
  document** for the draft v0.2 contract (`schema_version:
  0.2-draft`): 10 versions, 12 manifestations, 8 provisions,
  2 relationships, 9 fictional organizations in the same XA/XB
  universe, with fake repeated-hex sha256 values and example.org URLs.
- Its scenarios (call-opened cohort, dual award cohorts, effective on
  promulgation, signed resolution + annex, mutable HTML captures,
  legal mirror duplicate hash) mirror the *structure* of the internal
  pilot QC workbook. No real record, issuer name, excerpt or URL from
  that workbook is included, and the QC workbook itself is never
  committed to this repository.
- Do not import this file as if it were a corpus release; it exists to
  exercise `pipeline/exchange_lib.py` and `site/build_exchange.py`
  before any real data passes through them.

## Exchange fixture (Session 4, v0.3 draft)

- `exchange_v03.json` is the **synthetic demonstration exchange document**
  for the draft v0.3 contract (`schema_version: 0.3-draft`): 4 versions,
  7 manifestations (6 underlying after one duplicate-byte alias),
  2 provisions, 2 relationships, 1 placeholder score definition and
  3 score observations. `public_release_approved` is **false** — all
  public download/excerpt/score gates are closed.
- It adds two named **regression scenarios** that model the *structure*
  of real cases without importing any original file, excerpt or URL
  path: a Colombian Resolution 0777 (2022) model (signed 2022-08-03,
  Article 3 effective on publication, gazette facsimile issue 52.243 of
  2022-12-09, mirror provenance with official-host corroboration pending,
  resolution and annex as one version) and a UCT repository-policy
  genealogy model (2014 label pointing to amended 2014/2016 text, then a
  2020 revision; no clean 2014 baseline or effective date inferable).
  All excerpts are `[SYNTHETIC PLACEHOLDER …]` strings.
- Score dimensions use a single placeholder (`SD-SYNTH-DIM-01`); the
  authoritative ten-score codebook has not been supplied, so no labels
  are hardcoded and no composite is computed.
- Do not import this file as if it were a corpus release; it exists to
  exercise `pipeline/exchange_v03_lib.py` before any real data passes
  through it.

## Exchange fixture (Session 5, v0.3.1 draft)

- `exchange_v031.json` is the **synthetic demonstration exchange document**
  for the draft v0.3.1 contract (`schema_version: 0.3.1-draft`): 6
  versions, 9 manifestations (8 underlying after one duplicate-byte
  alias), 2 provisions, 2 relationships, 1 placeholder score definition,
  3 score observations. `public_release_approved` is **false** — all
  public gates closed.
- New structural scenarios: Colombia Resolution 0777 modelled as
  `publication_linked` (signed 2022-08-03; Diario Oficial 52.243 published
  2022-12-09, issuer-attested with gazette-mirror caveat; effective
  provisionally 2022-12-09); BRIN Regulation 12/2023 modelled as
  `promulgation_linked` (year-precision synthetic promulgation); UPTC
  Agreement 2/2026 as an `attested_unrecovered` news lead (adoption
  2026-01-29 issuer-attested; no verified PDF/annex, effective date,
  clause or hash; excluded from comparison and public views); a
  UPTC unknown-start cohort (not negative infinity; unknown end ≠
  unbounded end).
- All excerpts are `[SYNTHETIC PLACEHOLDER …]` strings; no original policy
  file, excerpt or URL path is imported.

## Exchange fixture (Session 6, v0.3.2 draft)

- `exchange_v032.json` is the **synthetic demonstration exchange document**
  for the draft v0.3.2 contract (`schema_version: 0.3.2-draft`): 6
  versions, 8 manifestations, 1 provision, 1 placeholder score definition,
  1 unpopulated score observation. `public_release_approved` is
  **false**; `published_at` is null until publication.
- It covers the nine v0.3.2 scenarios: recovered draft PDF
  (`draft`+`original_recovered`), issuer-attested approved version with
  no operative bytes (`approved`+`attested_unrecovered`, bound to its
  version), en/fr issuer editions as two manifestations of one version
  vs one bilingual single file, an 85-page PDF with a "physical p.56;
  printed p.53" anchor, a null-version family-bound unrecovered lead, and
  an HTML capture with `rights_status=unreviewed`. The internal QC-hold
  workbook pattern (`pilot_source_qc*.csv`) is gitignored and never
  committed; tests use inline synthetic hold rows instead.
- Ten-score numeric fields stay unpopulated until the corpus thread
  supplies labels, scale anchors and a codebook version.
