# AGENTS.md — working rules for humans and AI sessions on this repository

## What this repository is

The explorer for the ROARA OA/OS policy corpus. Planning began 2026-11-07.
The authoritative documents are `docs/plans/2026-11-07-explorer-plan.md` (master
plan) and `docs/adr/0001-static-data-driven-explorer.md` (architecture
decision). The data contract is a DRAFT pending corpus-team ratification.

## State (update this section each session)

- Session 1 (2026-11-07): planning only. Repository `oa-explorer` created
  public by the owner; plan, ADR, data contract draft, licences, AGENTS.md and
  changelog committed to main. No code, no data, no tests. Next step:
  Milestone M1 (see plan §10 for the exact next prompt).
- Session 2 (2026-11-08): Milestone M1 implemented and complete — local
  vertical slice on synthetic data only. Added: contract layer (9 JSON
  Schemas, vocabularies, allowlist, legacy map; v0.1.0 DRAFT), pipeline
  (`contract_lib.py`, validator `export_ledger.py`, allowlist exporter
  `build_public.py` v0.2.0 with approval/permission gating, offline
  `check_links.py`), synthetic seed corpus (64 rows, all
  `data_origin=synthetic`, six required demo cases incl. replaced version,
  unrecovered source, partial dates, conditional clause, two languages,
  reviewed absence vs unknown), stdlib-only static site (ADR 0002) with
  filters/search, record pages, relationships, evidence, chart with
  denominator, about/limitations page, and 88 automated tests (plan §7
  tests 1–10) — all passing, honestly scoped (no browser-level,
  keyboard or screen-reader testing claimed; plan tests 11–14 remain
  open for M3). M1 report, continuation note and handover doc in
  `docs/`. Nothing pushed, published or deployed by the session; the
  owner reviews and pushes. Next step: M2 pilot gate, blocked on U1
  (reviewed Axis 2 export) — see
  `docs/plans/2026-11-08-continuation-note.md` for the exact data
  handoff expected from the corpus project.
- Session 3 (2026-11-08): v0.2 exchange-contract vertical slice,
  synthetic data only, stopped before real ingest. Added: draft v0.2
  exchange schema (`contract/exchange/`, copied verbatim from the
  corpus project's design fixture, not ratified),
  `pipeline/exchange_lib.py` (shape validation beyond schema subset:
  cross-references incl. same-version evidence binding and
  component/cycle checks; duplicate source-hash rules; typed
  date-claim semantics where a cohort threshold never infers a
  general effective date; rights/review-gated reader views with
  independently configurable links/downloads/excerpts),
  `synthetic/exchange_v02.json` (10 versions / 12 manifestations /
  8 provisions / 2 relationships, fictional XA/XB issuers; mirrors
  the internal pilot QC workbook's structural scenarios only — the
  QC workbook itself is never committed), `site/build_exchange.py`
  (deterministic gated reader site, no prevalence/ranking/scores),
  tests 20–23 (63 new; 151 total, all passing) and the slice report
  with the v0.1→v0.2 migration note and 15 open questions for the
  corpus thread (`docs/plans/2026-11-08-exchange-v0.2-slice.md`).
  Nothing pushed, published or deployed; no real data touched.
- Session 4 (2026-11-08): v0.3 exchange-contract draft implementing the
  six owner-reviewed design decisions, synthetic fixtures only. Added:
  draft v0.3 schema attached verbatim (`contract/exchange/`,
  `0.3-draft`, not ratified; v0.2 kept for migration),
  `pipeline/exchange_v03_lib.py` (+ CLI), `synthetic/exchange_v03.json`
  (Colombia Resolution 0777 and UCT 2014/2016/2020 genealogy as
  SYNTHETIC structural regression cases; `public_release_approved:
  false`, no original files/excerpts), tests 24–27 (52 new; 203 total,
  all passing) and `docs/plans/2026-11-08-exchange-v0.3-slice.md` with
  the v0.2→v0.3 migration notes, resolved questions Q1/Q3/Q5/Q6/Q8/Q9/Q14
  and unresolved fields (Q2/Q4/Q7/Q10–Q13/Q15 plus the ten-score
  codebook remain open). Nothing pushed, published or deployed; no real
  data touched; public download/excerpt/score gates closed.

## Non-negotiable rules

1. **No publication without explicit owner authorization.** Do not enable
   GitHub Pages, create releases announcing data, or push to any external
   host. The repo is public for code and docs only; the site stays undeployed
   until M4.
2. **This repository is PUBLIC: never commit the detailed research ledger**
   (full-detail contract files, coder commentary, review notes), which lives
   only in local, gitignored working copies. **No source PDFs, private files,
   unpublished notes or secrets** in any repository or export. Real corpus
   data enters only after the M2 pilot gate and only as approved public
   export.
3. **No fabricated content.** Never invent corpus records, URLs, excerpts,
   dates or counts. Synthetic seed data must be clearly labelled `SYNTHETIC`
   and kept in `synthetic/`.
4. **Respect the data contract's semantics**: unknown vs not applicable vs
   reviewed absence vs zero; adoption vs effective dates; date precision;
   per-manifestation permissions. If a case doesn't fit, raise it as an open
   question for the corpus team; do not resolve it unilaterally.
5. **No automatic analysis** of the corpus, no AI-generated coding of
   policies, no scraping for core operation. Evidence review is human work
   that happens outside the UI.
6. **Do not modify the corpus repository** (`oa-os-policy-collections`); this
   repo consumes its pinned release tags.
7. Keep the corpus's interpretive commitments in all UI text: no prevalence
   claims, no country rankings, no composite scores, denominators and
   limitations stated near every chart.
8. Accessibility target is WCAG 2.2 AA: semantic HTML, keyboard operability,
   visible focus, screen-reader-tested patterns, plain language, and
   international text support.

## Conventions

- Python 3.11+, pinned dependencies in `pipeline/requirements.txt`; offline
  builds; deterministic outputs (byte-identical rebuilds are tested).
- Every milestone ends with updated `CHANGELOG.md` and the State section
  above; tests that are not yet implemented are listed honestly as such.
- Commits to `main` are allowed for planning documents and (from M1)
  site/pipeline code; anything touching real data or publication gates needs
  the owner's explicit instruction.
- Provider-dependent statements (GitHub Pages limits, Zenodo, archive.org)
  carry their verification date and must be re-verified on any provider
  announcement or annually.
