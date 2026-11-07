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
