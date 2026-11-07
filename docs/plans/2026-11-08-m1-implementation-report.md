# M1 implementation report (2026-11-08)

Milestone M1 of `docs/plans/2026-11-07-explorer-plan.md` §6: a local
vertical slice on clearly labelled synthetic data. This report records
what was implemented, what runs, what does not, the exact commands and
versions, and how synthetic data will be replaced by the reviewed Axis 2
pilot export in M2.

## Pre-implementation review (required by the session brief)

Reread before coding: `AGENTS.md`, the master plan (esp. §6 M1, §7 tests),
ADR 0001, the data contract v0.1 DRAFT, and the repository state (planning
docs only; no code, no data).

**Blockers found: none.** Three documented deviations, all recorded:

- **Deviation A — stdlib-only build and unittest** instead of Jinja2 +
  pytest (ADR 0001's default): the session environment cannot install
  third-party packages. Recorded as [ADR 0002](../adr/0002-stdlib-only-m1-build.md),
  with Jinja2 kept as the documented fallback. No functional loss for M1.
- **Deviation B — synthetic countries use ISO 3166-1 user-assigned codes
  `XA` (Republic of Arcadia) and `XB` (Kingdom of Borealia)** with
  reserved `example.org` / `example-archive.org` URLs, so no real
  issuer, domain or document is referenced even accidentally.
- **Deviation C — the "unrecovered source" record page** renders a
  contract-compliant summary ("1 known manifestation(s), none publicly
  accessible…") instead of a source block, because non-public
  manifestations are withheld from the export by design; the version
  carries the derived summary columns.

Missing decisions that remain open (by design, not blocking M1): the
public-field allowlist and vocabulary details are status
`draft_pending_OQ3` pending corpus-team ratification (OQ1–OQ8); M1
implements them as written and every test that depends on them is
labelled accordingly.

## What was implemented

### Contract layer (`contract/`, version 0.1.0)

- 9 JSON Schemas (draft 2020-12 + `x-column-order`): country,
  organization, policy_family, policy_version (57 columns incl. 4 export
  `derived_*`), manifestation, provision, version_relationship, text,
  version_function.
- `vocabularies.csv` (all controlled vocabularies, incl.
  `data_origin synthetic/corpus` as an M1-proposed addition pending
  ratification), `public_allowlist.csv` (per-entity public fields),
  `legacy_map_v1.csv` (v1 56-column → contract mapping with
  needs_human_review flags).
- Semantics implemented per contract: `value_state` pairs (unknown /
  not_applicable / reviewed_absent / measured), date blocks with
  precision/basis/confidence/verbatim, per-manifestation permissions,
  review/provenance columns on every entity.

### Pipeline (`pipeline/`)

- `contract_lib.py`: schema + vocabulary + pattern validation, value-state
  invariants, date-block checks, FK integrity, composite-key uniqueness
  (text: entity_id+field+lang; version_function: version_id+function),
  relationship cycle detection, derived-value rules (family means only
  when all family dimensions measured; composite 0–30 only when all ten
  measured; else empty), CSV↔JSON round trip, canonical table writer
  (subset-aware), sha256.
- `export_ledger.py` (validator CLI), `build_public.py` (public exporter
  v0.2.0: approved_public + public_visible rows only; allowlisted columns
  only — enforced at write time; non-public manifestations excluded with
  derived counts + `derived_source_status_summary` on the version;
  provisions bound to excluded manifestations excluded; excerpts blanked
  with `excerpt_value_state=not_applicable` when permission is not
  `permitted`/`quotation_exception`; deterministic output;
  `manifest.json` with counts, per-file sha256, synthetic flag).
- `check_links.py` (offline inventory; `--check` for opt-in network run).

### Synthetic seed corpus (`synthetic/`, 64 rows / 9 files)

All rows `data_origin=synthetic`; IDs use user-assigned codes XA/XB. The
six required cases, all verified in the built site:

| Case | Record | How it shows |
|---|---|---|
| Two versions of the same policy | V-XA-0001 → V-XA-0002 | typed `replaces` edge rendered on both record pages with evidence |
| Partial date | V-XA-0001 | adopted `2020` precision `year` + verbatim "Tag nicht angegeben"; never "2020-01-01"; also V-XB-0001 month precision `2023-03` |
| Unrecovered source | V-XB-0001 / M-XB-0001 | no source block, no link, only the derived summary; provisions withheld with it |
| Conditional clause | P-XA-0003 | modality/actor/action/object/scope/conditions/exceptions fully populated; separate reviewed-absence ("none (reviewed: unconditional)") encodings on P-XA-0002 |
| Two languages | V-XA-0002 | parallel de/en titles, excerpts and verbatim quotes, `lang` attributes on the record page; orgs and countries bilingual too |
| Reviewed absence + unknown | O-XB-0002 (`has_policy=N`, measured) vs O-XA-0003 (unknown, unreviewed, excluded from export) | screening table renders "no policy (reviewed absence)"; numeric zero shown by V-XA-0001 `score_comp_compliance=0` |

### Site (`site/`)

Stdlib `string.Template` generator producing: index (h1, intro, purposive
sampling statement, SVG chart with title/desc + denominator note naming
the excluded strata, organization screening table, full no-JS version
table with `data-*` filter attributes, JS filter/search mount with
labels + `aria-live` count), one record page per approved version
(metadata, dates with precision and verbatim, relationships both
directions, manifestations with rights/excerpt status, coded provisions
with original-language excerpts + physical anchors, policy-function
payloads, ten-dimension profile with per-dimension value states,
citation note), about/limitations page (purposive sampling, the four
null-semantics, dates, permissions, relationships, privacy), and the
data downloads (9 CSVs + manifest.json). Root-relative links on record
pages; skip link, landmarks, focus-visible styles, `lang` attributes.

## What runs, exactly

Environment used: Python 3.12.14 (stdlib only; Node 22.20.0 available but
only used for a one-off `node --check` syntax check of `explorer.js`,
which is not part of the test suite). Commands: see
[docs/handover.md](../handover.md) or README "Quickstart".

**Test status: all 88 automated tests pass** (10 modules, plan §7 tests
1–10):

1. `test_01_schema` — schema structure, ID patterns, enum↔vocabulary
   consistency, allowlist fields exist in schemas.
2. `test_02_integrity` — FKs (3 directions), duplicate primary and
   composite keys, relationship cycles, self-reference; synthetic corpus
   validates clean via CLI.
3. `test_03_semantics` — value-state invariants, zero vs unknown vs
   not_applicable, composite-only-when-complete (enforced), vocabulary
   enforcement, lossless CSV→JSON→CSV round trip.
4. `test_04_dates` — year/month precision survives export without an
   invented day, verbatim preserved, adopted unknown vs effective known,
   day-precision-requires-full-date, no fake day in site JSON or record
   page.
5. `test_05_permissions` — canary marker absent from export and site;
   draft version and unreviewed org excluded; unrecovered manifestation
   excluded but summarized; not-permitted excerpt blanked while its
   manifestation stays public; every exported column allowlisted; every
   exported row approved_public + public_visible; manifest counts.
6. `test_06_relationships` — replaces edge in data and on both endpoint
   pages with direction and evidence; related edge XB; all intra-site
   links resolve; isolated version states absence.
7. `test_07_site` — index.json covers exactly the 5 approved versions;
   deep-link pages exist; table `data-*` attributes agree with
   index.json; no-JS content complete; bilingual titles; synthetic
   labels and purposive note on every page; citation and anchors; data
   files published.
8. `test_08_accessibility` — automated structural checks: lang, skip
   link first focusable, landmarks, heading order (no skipped levels),
   no positive tabindex, focus CSS, svg role/title/desc, table
   captions + th scopes, JS filter labels, link text quality.
9. `test_09_charts` — denominator equals exported versions, chart counts
   match data, title/desc present, excluded strata named, no ranking
   language, composite absent from index.
10. `test_10_reproducible` — two clean export+build runs byte-identical;
    manifest sha256 verifies; versions pinned.

Bugs the new tests caught and that were fixed before sign-off (kept as
a note for the reviewer):

- `dataset_to_json/from_json` collapsed composite-key rows (bilingual
  texts 25→17); now lists preserve text and version_function rows.
- `write_table` wrote all schema columns, filling disallowed ones with
  empty strings, so disallowed **columns** entered the public export;
  the exporter now writes exactly the allowlisted subset.
- `vocabularies.csv` still carried the legacy `Unclear` term although
  the schema enum excludes it (v1 mapping handles it); removed.
- Record pages had root-relative header/footer/style links that broke
  from `record/`; now root-prefixed per page.
- `index.html` had no `h1`; added.
- `manifest.json` did not record per-file checksums; now `sha256` map.

## What does NOT run / is NOT claimed

- Plan §7 tests 11–14 are **not implemented**: browser-level filter
  interaction test, keyboard-only walkthrough, screen-reader pass,
  dead-link network check (`check_links.py --check` exists but was not
  run with network in this session).
- **No manual accessibility audit was performed.** The automated checks
  cover structure only; WCAG 2.2 AA conformance is not claimed. M3 owns
  the axe-core + keyboard + screen-reader passes.
- No real corpus data was touched, imported or assumed. No ROARA corpus
  has been supplied to this implementation; everything runs on
  `synthetic/`.
- Nothing was published, pushed, deployed or made public; no remote
  resources were created or contacted. GitHub repo state is untouched by
  this session (the owner pushes; see the continuation note).

## How synthetic data will be replaced (M2 pilot gate)

1. The corpus project delivers the reviewed Axis 2 export (see
   continuation note for the exact handoff) into a **local, gitignored**
   `ledger/` directory (never `synthetic/`, never committed).
2. `python3 pipeline/export_ledger.py --input ledger --contract contract`
   must pass; discrepancies go to the discrepancy log, not silent fixes.
3. `python3 pipeline/build_public.py --input ledger --contract contract
   --output exports/pilot` exports only `review_state=approved_public` +
   `public_visible=true` rows, allowlisted fields only.
4. `python3 site/build.py --export exports/pilot --output _site_pilot`
   builds the pilot site locally; the synthetic banner disappears
   automatically when the manifest's synthetic flag is false, but each
   pilot record must be human-reviewed before any publication step.
5. Rollback is deleting the local `ledger/` and pilot outputs; the
   synthetic path keeps working unchanged.
6. The v1 56-column rows map through `contract/legacy_map_v1.csv`; every
   mapping judgement is a `needs_human_review` candidate for the pilot
   discrepancy log. **No automatic analysis, no fabricated content.**

## Limitations (honest list)

- Filters/search are client-side only over 5 records; corpus-scale
  behaviour (hundreds of versions) is untested (M3 does the DE-scale
  build).
- The chart is build-time SVG; fine at this scale.
- `string.Template` has no autoescaping; escaping is manual and
  disciplined (`esc()` everywhere); a future Jinja2 migration (ADR 0002)
  would reduce that risk class.
- The permission-filter tests use a planted canary string in
  non-public ledger fields; the canary is synthetic-only content and
  must never appear in real ledger data (it would trip the same tests,
  which is the point).
- Contract 0.1.0 is DRAFT; schema/vocabulary/allowlist changes from
  corpus-team ratification may require a 0.2.0 and a migration note
  (contract §Versioning).
