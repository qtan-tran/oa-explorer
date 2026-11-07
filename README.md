# OA/OS Policy Explorer (ROARA)

A durable, free-to-use explorer for the ROARA corpus of open-access /
open-science policies: filter, search, open versioned policy records with
evidence, original-language excerpts and source anchors, follow relationships
across policy versions, and download cautious, transparent exports.

**Current status: PLANNING ONLY.** This repository contains no application
code and no data yet. Session 1 (2026-11-07) produced:

- [`docs/plans/2026-11-07-explorer-plan.md`](docs/plans/2026-11-07-explorer-plan.md) — master plan: milestones, repository layout, tests, maintenance
- [`docs/adr/0001-static-data-driven-explorer.md`](docs/adr/0001-static-data-driven-explorer.md) — architecture decision record (static site, Python + Jinja2, GitHub Pages with dated limit checks)
- [`docs/plans/2026-11-07-data-contract-v0.1.md`](docs/plans/2026-11-07-data-contract-v0.1.md) — data contract v0.1 DRAFT, pending corpus-team ratification

The research corpus lives in the separate repository
[`oa-os-policy-collections`](https://github.com/qtan-tran/oa-os-policy-collections)
and remains the research ledger of record. This repository is public, but the
detailed research ledger, PDF originals and unpublished notes never live in it
(plan §1, decision D4); they stay in local, gitignored working copies or
institutional storage. The public site (GitHub Pages) goes live only by the
owner's explicit authorization, at milestone M4 of the plan.

Core commitments, inherited from the corpus and enforced by the plan's tests:
purposive corpus, never a census (no prevalence claims, no rankings); unknown
≠ not applicable ≠ reviewed absence ≠ zero; partial dates never invent a day;
source documents are never redistributed; the public site carries only
reviewed, explicitly approved fields.

## Licensing

- Code (when it exists): MIT — see `LICENSE-CODE.md`
- Documentation and plans: CC BY 4.0 — see `LICENSE-DOCS.md`

## Maintainer

Quoc-Tan Tran, Institute for Studies of Science, Bielefeld University,
within the ROARA project.
