# Changelog

All notable changes to this repository. Format: Keep a Changelog; versioning:
the repository follows the plan's milestones, contract semver is separate.

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
