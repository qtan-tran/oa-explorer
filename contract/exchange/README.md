# Exchange contracts (drafts)

- `roara_contract_v0.3.1.schema.json` — **current draft** internal contract
  (schema_version `0.3.1-draft`), attached 2026-11-08 as the owner-reviewed
  successor design. **Not ratified.** Adds to v0.3: `publication_linked`
  effective interpretation (published and promulgated are distinct source
  events), unknown-start cohort semantics, stricter public archive-link
  language, and score actor/action semantics. See
  [`docs/plans/2026-11-08-exchange-v0.3.1-slice.md`](../../docs/plans/2026-11-08-exchange-v0.3.1-slice.md)
  for the test delta, schema-contradiction check and the eight still-open
  questions.
- `roara_contract_v0.3.schema.json` — superseded draft internal contract
  (schema_version `0.3-draft`), attached 2026-11-08. **Not ratified.** It
  implements six corpus-team decisions (score observations separated from
  provisions; issuer URL vs archived snapshot kept distinct; typed cohort
  triggers; `retrieved_at` as the only retrieval event; explicit
  duplicate-byte aliases; mandatory provision cohort applicability). See
  [`docs/plans/2026-11-08-exchange-v0.3-slice.md`](../../docs/plans/2026-11-08-exchange-v0.3-slice.md)
  for the v0.2→v0.3 migration notes and unresolved fields.
- `roara_contract_v0.2.schema.json` — superseded draft exchange contract
  (schema_version `0.2-draft`), provided 2026-11-08 as a design fixture for
  the explorer's v0.2 exchange slice. Retained for migration reference. It
  is **not ratified**; field semantics may change when the corpus team
  resolves the open questions listed in
  [`docs/plans/2026-11-08-exchange-v0.2-slice.md`](../../docs/plans/2026-11-08-exchange-v0.2-slice.md).

Notes:

- The schema checks **shape only**. Cross-record references, duplicate
  source hashes, rights/review gating and date-claim semantics are
  validated by `pipeline/exchange_lib.py` on top of it.
- The internal pilot QC workbook (`pilot_source_qc_v0.2.csv`) is **not
  part of this repository** and is never committed: it contains internal
  review state about real sources. The explorer's tests use the
  clearly-labelled synthetic exchange fixture
  (`synthetic/exchange_v02.json`) whose records mirror the QC workbook's
  *structural* scenarios with fictional issuers only.
