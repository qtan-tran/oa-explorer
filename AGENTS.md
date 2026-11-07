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
