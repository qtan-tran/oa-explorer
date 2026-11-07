# Exchange contract v0.2 (draft)

`roara_contract_v0.2.schema.json` is the corpus project's **draft** exchange
contract (schema_version `0.2-draft`), provided 2026-11-08 as a design
fixture for the explorer's v0.2 exchange slice. It is **not ratified**;
field semantics may change when the corpus team resolves the open
questions listed in
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
