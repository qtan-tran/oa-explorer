# Project handover (M1 state)

This file is the short, durable handover for anyone (including a future
maintainer or a future session of this project) picking the repository up
cold. It answers: what is this, what runs, what doesn't, what must never
happen, and where the detailed knowledge lives.

## One-paragraph summary

The OA/OS Policy Explorer turns reviewed rows of the ROARA policy corpus
(separate repository `oa-os-policy-collections`) into a fully static,
offline-buildable, accessibility-minded website plus machine-readable CSV
exports. As of M1 (2026-11-08) the whole pipeline runs locally on clearly
labelled **synthetic** data only; no real corpus data, no deployment, no
publication. The data contract is DRAFT status pending corpus-team
ratification (open questions OQ1–OQ8 in
`docs/plans/2026-11-07-data-contract-v0.1.md`).

## Commands (the complete operational surface)

Run from the repository root; no package installation needed
(Python ≥ 3.11, stdlib only — ADR 0002):

```bash
# 1. Validate a dataset against the contract (exit 0 = valid)
python3 pipeline/export_ledger.py --input synthetic --contract contract

# 2. Build the reviewed-and-approved public export (allowlist-enforced)
python3 pipeline/build_public.py --input synthetic --contract contract \
    --output exports/public

# 3. Build the static site from that export
python3 site/build.py --export exports/public --output _site

# 4. Preview locally (open http://localhost:8000)
python3 -m http.server -d _site 8000

# 5. Run the full test suite (88 tests; includes two clean rebuilds)
python3 -m unittest discover -s tests -t . -v

# 6. Offline inventory of source links (no network unless --check given)
python3 pipeline/check_links.py --export exports/public \
    --report link-report.txt
```

`exports/`, `_site/`, `ledger/` are gitignored build products. Everything
needed to rebuild them is committed (code, contract, synthetic data).

## What exists (M1, 2026-11-08)

- `contract/` — versioned data contract: 9 JSON Schemas (draft 2020-12
  with `x-column-order`), vocabularies, public-field allowlist, v1→v2
  legacy mapping. Contract version 0.1.0, status DRAFT.
- `pipeline/` — validator (`export_ledger.py`), allowlist exporter with
  approval gating (`build_public.py`, exporter v0.2.0), link inventory
  (`check_links.py`), shared library (`contract_lib.py`).
- `synthetic/` — 64-row synthetic seed corpus in 9 CSV files, every row
  `data_origin=synthetic`; includes all six required demo cases.
- `site/` — stdlib static site generator + templates + progressive JS
  filters + WCAG-minded CSS. Output: index with filters/search and
  chart-with-denominator, one record page per approved version
  (evidence, relationships, ten-dimension profile), about/limitations
  page, CSV + manifest downloads.
- `tests/` — 88 automated checks in 10 modules (schema, integrity,
  semantics, dates, permissions, relationships, site, accessibility,
  charts, reproducibility). **All passing.** Not performed and not
  claimed: tests 11–14 of plan §7 (browser-level filter interaction,
  keyboard walkthrough, screen-reader pass, dead-link network run) and
  any manual accessibility audit.

## Hard rules that survive every handover

1. Never publish (GitHub Pages, releases, any host) without the owner's
   explicit authorization; the site stays local until milestone M4.
2. Never commit the detailed research ledger, source PDFs, private notes
   or secrets; the public repo carries only code, contract, docs and
   approved exports. The ledger lives in gitignored local directories.
3. Synthetic data is always labelled, in data (`data_origin=synthetic`)
   and on every page ("SYNTHETIC" badge/banner).
4. The contract's semantics are non-negotiable: unknown ≠ not applicable
   ≠ reviewed absence ≠ numeric zero; adoption vs effective dates; no
   invented date precision; per-manifestation permission review; no
   prevalence, ranking or composite claims anywhere in the UI.
5. Do not modify the corpus repository; this repo consumes its pinned
   releases.
6. Provider-dependent statements (Pages limits, archival services) carry
   a verification date and must be re-checked before relying on them.

## Where the detailed knowledge lives

- Master plan: `docs/plans/2026-11-07-explorer-plan.md` (milestones §6,
  tests §7, maintenance §8, ten-year checklist).
- M1 implementation report: `docs/plans/2026-11-08-m1-implementation-report.md`.
- Continuation note (next milestone + expected data handoff):
  `docs/plans/2026-11-08-continuation-note.md`.
- Working rules: `AGENTS.md`. Decisions: `docs/adr/`.
- Data contract draft: `docs/plans/2026-11-07-data-contract-v0.1.md`.
