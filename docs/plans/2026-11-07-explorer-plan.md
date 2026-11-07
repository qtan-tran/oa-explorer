# Explorer master plan (planning session 1)

Status: PLANNING ONLY. No application code exists yet. This document records the
plan, decisions, risks and next milestone for the ROARA OA/OS policy explorer.
Companion documents:

- [`docs/adr/0001-static-data-driven-explorer.md`](../adr/0001-static-data-driven-explorer.md) — architecture decision record (stack, hosting, costs, alternative)
- [`docs/plans/2026-11-07-data-contract-v0.1.md`](2026-11-07-data-contract-v0.1.md) — data contract v0.1 (DRAFT, pending corpus-team ratification)

Session date: 2026-11-07. Author: planning session with Vibe (Mistral), repository owner Quoc-Tan Tran (ROARA project).

---

## 1. Goals and hard constraints

**Product.** A public-facing explorer for ROARA's purposive corpus of open-access / open-science policies when the owner explicitly authorizes publication: filter by country, issuer type, instrument/function, dates, OA/OS scope, funding/APC relevance and source/review status; search titles; open a version record with evidence, original-language excerpts with physical page/article anchors and source links; show relationships across versions; provide cautious, transparent comparisons and downloads. Also support private local development and review.

**Hard constraints (non-negotiable).**

1. The corpus is purposive, not a census. No inference of national prevalence; corpus counts are never represented as country-wide rates. No country ranking or composite score from incompatible or incomplete coding (consistent with the corpus's no-weighted-index commitment).
2. Separate unknown/unreviewed, not applicable, reviewed absence and numeric zero. Adoption and effective dates are distinct. Partial and uncertain dates never invent a day.
3. Original policy documents are not redistributed. Document redistribution rights, attribution and permitted excerpts are independently reviewed per manifestation. PDF originals live outside git repositories; links point to issuer copies plus archival snapshots; private/restricted originals stay separate.
4. The public site contains only reviewed and explicitly approved fields. No source PDFs, private files, unpublished notes or secrets in any public artifact. Code and publishable metadata have separate release decisions and licences.
5. Zero-server static frontend, plain version-controlled machine-readable exports. No paid hosted database, AI API, mandatory login, runtime AI calls, proprietary data formats or fragile scraping for core operation. Research originality, evidence review and data stewardship stay outside the UI.
6. WCAG 2.2 AA target, keyboard and screen-reader usable, responsive, plain language, international text support, deep links, denominators and limitations explained near each chart.
7. Ten-year portability: no provider or dependency is guaranteed for that period. Everything must survive a host, a dependency or a service disappearing.

**Decisions taken this session (by the repository owner).**

- D1. Explorer lives in a **new separate repository** ([`oa-explorer`](https://github.com/qtan-tran/oa-explorer)), decoupled from the research corpus repo `qtan-tran/oa-os-policy-collections` (which remains the research ledger of record and is not modified by this session).
- D2. Plan/ADR saved by **commit directly to main** of the new repo.
- D3. Recommended build stack: **Python + Jinja2 static site generator** (see ADR).
- D4. The new repo `oa-explorer` is **public from creation** (owner decision, 2026-11-07). Consequence: the detailed research ledger, PDFs and unpublished notes are never committed to it; the ledger lives only in local, gitignored working copies (or future institutional storage, see U6/OQ6). Site publication (GitHub Pages enablement) remains a separate explicit decision at M4.

## 2. Inspection record (what was actually inspected, 2026-11-07)

No AGENTS.md existed in any inspected location. The corpus repository `qtan-tran/oa-os-policy-collections` (public, default branch `main`, 1 commit `717f355` 2026-07-14, no releases) was inspected via the GitHub API:

- Root: `README.md`, `CHANGELOG.md`, `CITATION.cff`, `INSTALL_AND_UPDATE.md`, `LICENSE-CODE.md` (MIT), `LICENSE-DATA.md` (CC BY 4.0), `requirements.txt` (pandas, numpy, scipy, scikit-learn), `.gitignore`.
- `schema/`: `data_dictionary.md` (56-column canonical schema), `coding_manual.md` (ten 0–3 dimensions in three families, no weighted index), `country_extension_schema.md` (four context variables), `CHANGELOG.md`.
- `countries/`: `DE` populated; `CA`, `CO`, `ID`, `NL`, `ZA` placeholders; `_COUNTRY_TEMPLATE/`.
- `countries/DE/`: `full/DE_corpus_full_v1.csv` (412 data rows, 56 columns), `policies/` (generated view), `README.md`, `coding_trail/` (scoring manual, reasoning report, `addenda/` 4 files, `audits/` 2 files, `batch_coding/` 7 files, `analytic_dataset.csv`).
- `analysis/`: `validate_schema.py` (column presence/order, 0–3 bounds, vocabularies, ID format), `build_combined.py` (regenerates `policies/` and `combined/`), `reproduce_analysis.py`, `README.md`.
- `combined/`: `ALL_full_latest.csv` (269 KB), `ALL_policies_latest.csv` (207 KB), `README.md`.
- The full DE CSV was downloaded and programmatically inspected (not sampled by hand).

**Verified observations about the DE corpus (basis for the contract's design, not criticism):**

- `coding_status`: Coded 125, Coded_inherited 155, Not_yet_coded 15, No_policy 52, Unclear_to_confirm 65. `has_policy`: Y 295 / N 52 / Unclear 65.
- `adoption_date` is not machine-parseable as one format: 59 pandas timestamps (`2016-09-01 00:00:00`), ≥11 ambiguous strings (`01/12/2005`, `01.03.2011`, `not stated`), 1 bare year, 341 blank. Confirms the need for the contract's date-precision + verbatim design.
- `policy_url` present on 138 records; **`policy_url_archived` on 0 records**, although the data dictionary marks an archived snapshot as required alongside every live link. Archival snapshot capture is therefore pre-publication work for any pilot subset.
- `policy_source` values in the data (`Own (superseded)`, `Own (pending)`, `Own + umbrella`, `Inherited (floor)`, `Inherited (baseline)`, `Own (funder/umbrella)`, …) diverge from the documented vocabulary (`Own / Own_plus_umbrella / Inherited / Inherited_baseline / Unclear`). The validator does not currently catch this. The contract must pin vocabularies in one machine-readable source and document a mapping for legacy values.
- `[verify: …]` review markers appear in legal-context fields on all 412 rows. These are already public in the corpus repo; before any explorer publication, fields carrying open verification markers need a review decision (publish as explicit uncertainty, or exclude until resolved).
- `update_group`/`template_group` are free-text labels (FAU, BMBF, Helmholtz, …) on 20 / 2 rows, not stable IDs. Version relationships need typed edges with stable IDs.
- `nominal_year` is serialized as float strings (`2016.0`).

**Unknowns / external dependencies identified (not invented):**

- U1. "Axis 2" reviewed export: referenced as the pilot-gate input; no file or format was found in the inspected repositories. The pilot gate is defined but blocked on it.
- U2. Corpus-team sign-off process and who besides the owner must ratify the data contract.
- U3. The ratified allowlist of public fields (proposed in the contract, pending approval).
- U4. Where PDF originals are and will be durably stored (institutional storage decision, owner + Bielefeld RDM).
- U5. GitHub plan level (assumed Free), desired custom domain, UI languages beyond English.
- U6. Where the detailed ledger (contract files with comments/notes) durably lives now that the repo is public: local gitignored working copies are the session-1 default; institutional storage is the preferred long-term answer (see OQ6).

## 3. Architecture summary (details in the ADR)

**Chosen:** pre-rendered static site, built by a small Python (Jinja2) generator in this repo, consuming a validated public data export (CSV + JSON) produced from the research ledger. Vanilla JS (one small optional file) for client-side filtering/search over a pre-built JSON index; every record page and list page pre-rendered and fully functional without JavaScript. Charts pre-rendered as accessible SVG at build time with adjacent data tables and denominator/limitation notes.

**Rejected alternative:** server-backed dynamic app (Flask/Datasette + SQLite) — always-on hosting conflicts with the zero-server requirement and adds cost/fragility over ten years; data readability would depend on an app, not on files. Within the static option, a client-side SPA was rejected in favour of pre-rendered HTML (no-JS resilience, simpler accessibility, smaller runtime).

**Hosting:** GitHub Pages, recommended only because its current limits and permissions fit (checked 2026-11-07 against official docs; see ADR): public repo on Free plan, site far below the 1 GB published-site limit, non-commercial research/education use permitted, ≤10 builds/hour soft limit irrelevant for release-driven deploys. Portable alternatives documented (any static host, university web space, local `python -m http.server`). No claim that free tiers remain unchanged.

**Estimated ongoing costs:** €0 hosting. Optional custom domain ≈ €10–15/year. Zenodo DOIs free. Assumptions and cost table in the ADR. The only realistic non-zero costs are a domain and maintainer time (2–4 h/quarter steady state).

## 4. Repository layout (target state, after M1)

```
oa-explorer/  (public repo: code, schemas, synthetic data, docs ONLY)
├── README.md                     # purpose, status, quickstart
├── AGENTS.md                     # working rules for humans and AI sessions
├── CHANGELOG.md                  # Keep a Changelog format, releases
├── LICENSE-CODE.md               # MIT (site generator, exporter, tests)
├── LICENSE-DOCS.md               # CC BY 4.0 (docs, plan, ADR, UI prose)
├── docs/
│   ├── adr/                      # architecture decision records
│   └── plans/                    # this plan, data contract, future gate notes
├── contract/                     # the data contract (schema source of truth)
│   ├── VERSION                   # contract semver, e.g. 0.1.0
│   ├── vocabularies.csv          # ALL controlled vocabularies, machine-readable
│   ├── json-schema/*.json        # one JSON Schema (2020-12) per entity
│   └── data-dictionary.md        # every field, semantics, public/private scope
├── ledger/                       # LOCAL-ONLY, GITIGNORED detailed research
│   │                             # ledger (full-detail contract files). This
│   │                             # repo is PUBLIC: ledger files are NEVER
│   │                             # committed (see D4/U6/OQ6)
│   └── provenance_public.csv     # per-release provenance of PUBLIC exports
│                                 # (corpus tag, exporter, hashes) — publishable
├── pipeline/
│   ├── export_ledger.py          # ledger -> contract validation
│   ├── build_public.py           # ledger -> public export (allowlist + approvals)
│   ├── check_links.py            # offline dead-link report (maintenance tool)
│   └── requirements.txt          # pinned: jinja2, pandas (as needed)
├── site/
│   ├── templates/                # Jinja2 templates (list, record, about)
│   ├── static/                   # CSS, one optional JS file, UI dictionaries
│   └── build.py                  # export -> static HTML (+ SVG charts, index)
├── exports/
│   ├── public/                   # generated; committed only after M4 approval
│   └── review/                   # local-only, gitignored
├── tests/                        # pytest; see §7
└── synthetic/                    # clearly-labelled synthetic seed corpus (M1)
```

The research ledger of record (countries/**/full/*.csv, 56-column schema) stays in the corpus repository, untouched. This repo consumes a **pinned corpus release tag** per export; the tag and exporter version are recorded in `provenance_public.csv` (and, for full ledger detail, in the local ledger). No submodules, no runtime fetching, no scraping.

## 5. Data pipeline and interchange

**Ingestion (research side, unchanged discipline):** new countries/issues are coded into the corpus repo exactly per its existing process (validate → build_combined → release). The explorer never modifies that process; adding countries, issuers, languages or policy types requires no explorer code change, only contract data.

**Export path:** `corpus release tag (pinned) → export_ledger.py (mapping per contract §Mapping-from-v1, runs locally) → contract validation → review in local ledger/ → build_public.py (allowlist + review_state=approved_public + permission filter) → exports/public/ (CSV per entity + JSON + search index) → site/build.py → static HTML`.

- **CSV/JSON interchange:** every entity exists as UTF-8 CSV (RFC 4180, one file per entity, stable column order, ISO dates where complete) and JSON (nested, referencing the same IDs). CSV is the interchange of record; JSON is a generated view + the site's index. Both are validated against the same JSON Schemas (CSV validated row-by-row after a documented header mapping).
- **Determinism:** exports and site builds are pure functions of (ledger, contract version, pinned corpus tag, template version). Two clean builds must produce byte-identical output (tested). Release artifacts are checksummed (SHA-256) and attached to tagged releases.
- **Licences:** code MIT; public metadata/export CC BY 4.0 (matches corpus repo); documents never redistributed; excerpts governed per-manifestation `permission` fields; UI prose CC BY 4.0. The public site carries attribution/licence text and cites the dataset via its Zenodo DOI.
- **Citation/releases/changelog:** Keep-a-Changelog in this repo; corpus data releases keep their own DOI process (CITATION.cff already in the corpus repo, DOI pending first Zenodo release). The site footer links version, DOI, changelog and access date.
- **Security:** no runtime services, no logins, no secrets in the repo (ledger and review exports are gitignored; the public repo holds only code, schemas, synthetic data and docs). GitHub secret scanning enabled; Dependabot on the Python build tooling only. The public site collects nothing (note: GitHub Pages logs visitor IPs for security purposes per GitHub's docs).
- **Archival backups (3-2-1):** (1) git + tags (this repo), (2) Zenodo or equivalent DOI archive of each public data export, (3) offline zip of repo + exports + site build on institutional storage, checksum manifest, refreshed at each release and reviewed annually. PDF originals: durable storage outside git (institutional RDM storage, documented naming manifest); public links point to issuer copies + archival snapshots; restricted originals in a separate access-controlled location. `policy_url_archived` is a **publication prerequisite** for every record with a live link (currently 0/138 in DE — pilot work).
- **Continuity if a service stops or is no longer paid:** the export CSVs/JSON and static HTML are the product; any host serves them (GitHub Pages, university space, any CDN, a zip file on a USB stick). Documented runbook: local preview `python -m http.server`; alternative host steps in the ADR. If Zenodo became unavailable, fall back to another DataCite repository or checksummed GitHub release archives.
- **Reproducible builds:** pinned dependencies (`pipeline/requirements.txt` with exact versions), Python version documented, build script fully offline, release archive contains export snapshot + provenance + output hashes so a third party can rebuild and verify.

## 6. Phased milestones (each independently reviewable)

Every milestone ends with: a review checklist, tests green (or explicitly listed as not-yet-implemented), a rollback note, and no external side effects unless stated. Rollback is always `git revert` + (where applicable) disabling the deploy; the ledger is never overwritten in place (git history + release tags are the version record).

**M0 — Ratification (this session's output).**
Scope: this plan + ADR + data contract v0.1 DRAFT; corpus team reviews the contract, answers open questions OQ1–OQ8 (contract §Ratification), ratifies the public-field allowlist.
Acceptance: contract status DRAFT→RATIFIED (or v0.2 issued with team changes); decisions recorded in this file.
Rollback: docs are docs; revert commits.
No code, no publication.

**M1 — Local vertical slice on synthetic data.**
Scope: repo scaffold (§4 layout), contract JSON Schemas + vocabularies from the contract doc, `export_ledger.py`/`build_public.py`/`site/build.py` minimal versions, synthetic seed corpus (below), 10 minimal tests (§7), local preview. Everything offline; only code, schemas, synthetic data and docs are committed (repo is public).
Acceptance: (a) build produces the site from synthetic data with zero network access; (b) the five required synthetic cases render correctly (replaced version, unrecovered original, partial date, conditional provision, multiple languages); (c) tests 1–10 pass; (d) a keyboard-only walkthrough of list → filter → record → comparison is documented; (e) no real data committed.
Rollback: `git revert`; nothing deployed.
**Synthetic seed corpus (clearly labelled `SYNTHETIC`, no real issuers):** 8 records across 2 fictional countries including: a policy version replaced by a later version (typed `replaces` edge shown on both records); a version whose only known manifestation has `access_status=unrecovered` (record page shows evidence status, no fabricated excerpt); a version with year-only adoption date (rendered "2023", never "2023-01-01"); a conditional provision (e.g., obligation with a condition and an exception, modality/actor/action/object/scope/conditions/exceptions all populated); the same policy family with parallel titles and excerpts in two languages (original + gloss). Synthetic records carry a dedicated `synthetic=true` marker and are never merged with real data.

**M2 — Real-data pilot gate (separate gate; needs your go).**
Scope: export a small reviewed subset (proposed: the 20 DE records with `update_group` chains plus a sample across all coding statuses, ~15 records) from a pinned corpus release into the local ledger; capture archival snapshots for their live links (the dictionary already requires this); resolve or explicitly map the `policy_source` vocabulary drift; corpus team reviews each pilot record's public-field set; site runs locally on the pilot export. Blocked on U1 (Axis 2 reviewed export) if that export supersedes this selection.
Acceptance: pilot export validates; team sign-off recorded per record (`approved_public` + approver + date); discrepancy log written (every mapping judgement from v1 56-column rows to contract entities).
Rollback: delete pilot files; ledger untouched for other records.
Explicitly: **no automatic analysis and no fabricated content**; every pilot field traces to the v1 row or is `unknown`. Pilot ledger files stay in local, gitignored directories; nothing enters this public repo before approval.

**M3 — Accessibility and test hardening.**
Scope: WCAG 2.2 AA self-assessment (axe-core in tests + manual keyboard pass + at least one real screen reader spot-check, NVDA or VoiceOver, documented honestly); chart/denominator implementation; dead-link report run and triaged; full corpus-scale local build (DE) for performance sanity.
Acceptance: documented a11y checklist with results; every chart has an adjacent denominator + limitations note; check_links report attached to the milestone review.
Rollback: `git revert`.

**M4 — Publication (only on your explicit authorization).**
Scope: GitHub Pages enablement per ADR (`.nojekyll`, `gh-pages` branch or Actions deploy; the repo is already public, so no visibility change is needed), optional custom domain, licence/attribution page, announcement text, Zenodo DOI for the export, release tag.
Acceptance: only records with `review_state=approved_public` present (automated test + manual spot-check); an "about/limitations" page explains purposive sampling, denominators, and what the corpus cannot support; archives/links verified.
Rollback: disable Pages or revert + delete the release; site is fully reversible because it is derived.

**M5 — Maintenance mode.** Steady state per §8 checklist; new countries flow through corpus repo releases → M2-style mini-gates → export → release.

## 7. Test plan

Planned test set, honest status: **none of these tests exist yet; nothing has been run.** The minimal first set (M1) is tests 1–10; 11–14 are M2–M4 gates.

1. **Schema:** every ledger/export file validates against its JSON Schema; column order/presence per contract; ID format checks for all ID types.
2. **Referential integrity:** every version references an existing family; every manifestation a version; every provision a version and a manifestation; relationship endpoints exist; no orphan provisions; no duplicate IDs; `replaces` chains acyclic.
3. **Status/null semantics:** for every value column, (value, value_state) pair is legal; `unknown`/`not_applicable`/`reviewed_absent`/`measured` with value 0 are distinct through a CSV→JSON→CSV round-trip.
4. **Date precision:** year-only and year-month dates survive export round-trip without an invented day; `date_verbatim` preserved; adopted vs effective remain separate fields; confidence/basis vocab enforced.
5. **Permission filtering (publication safety):** a seeded private-only marker string in a non-allowlisted ledger field must NOT appear in any file under `exports/public/` or the built site; records without `approved_public` are absent from the export; manifestations with `excerpt_policy=not_permitted` contribute links but no excerpt text.
6. **Version relationships:** a replaced-version pair renders the edge on both records; cycle detection test fails loudly on synthetic cyclic data.
7. **Search/filter/record view:** the pre-built index covers exactly the approved public records; facet counts match the export; a record deep link resolves to the same record page without JavaScript.
8. **Keyboard navigation (smoke):** documented manual pass + automated focus/tab-order assertions where feasible (playwright optional, kept minimal).
9. **Charts/denominators:** for each chart fixture, the denominator equals the stated base (e.g., coded records only), and the adjacent limitations note names the excluded strata (e.g., `special_stratum`, `Not_yet_coded`).
10. **Reproducible release + restore:** two clean builds byte-identical (hash comparison); a restore drill unpacks the last release archive in a fresh directory and rebuilds successfully.
11. **Import/migration:** contract migration scripts produce deterministic outputs and a mapping log; a fixture ledger under schema N-1 migrates to N with zero unmapped fields.
12. **Links:** `check_links.py` report on the public export produces a dated report (manual, quarterly; not part of the build so the build stays offline).
13. **Accessibility:** axe-core scan of list/record/comparison pages returns zero critical violations; manual screen-reader spot-check documented (M3).
14. **Publication gate:** at M4, a test run against the live deployment's export confirms only approved fields are present (mirror of test 5 on the deployed copy).

## 8. Ten-year maintenance checklist

**Quarterly (≈2–4 h total).** Run tests + validator + build; run dead-link report and triage; check GitHub/Pages/Zenodo changelogs for limit or policy changes (re-verify the ADR's provider statements annually or on any announcement); rotate offline backup; review open `[verify]`/`unclear` items with the corpus team; review issues/PRs.

**Annual (≈1 day).** Dependency review (pinned minor versions; upgrade deliberately, one at a time, tests green before commit); accessibility re-check (WCAG 2.2 AA, including one screen-reader pass); schema proposals review; update handover docs; refresh archival copies + checksum manifest; data release + Zenodo DOI if data changed; restore drill.

**Event-driven.** New country onboarding (corpus release → mini M2 gate → export → release); WCAG version updates; provider policy changes (re-run ADR review); maintainer change (use handover runbook below).

**Human work and realistic responsibilities.**
- **Repository owner / maintainer (Tan Tran):** pipeline, releases, hosting, security, ADR updates. Steady state 2–4 h/quarter.
- **Corpus team:** coding, evidence review, per-record publication approvals (data authority). Already their process; the explorer adds the approval column.
- **Accessibility testing:** team self-tests with the documented checklist; one real screen-reader session per year strongly recommended; external audit if ever affordable.
- **Institutional RDM/library (Bielefeld):** durable storage of PDF originals, offline backups and (preferred long-term) the detailed ledger (owner to arrange; U4/U6).
- **Handover runbook (living doc, `docs/handover.md` at M1):** what the project is, where everything lives, how to build/test/release, account/ownership transfer steps, and this checklist.

**Risks (top).** R1 maintainer bus factor → simple stack, handover doc, all decisions recorded. R2 free-tier/policy changes at GitHub or Zenodo → portability, date-checked provider statements, documented alternatives. R3 vocabulary/schema drift (already observed in `policy_source`) → single machine-readable vocabulary source + validator + migration discipline. R4 publication of unapproved content → allowlist + permission-filter tests as hard gates, plus the public-repo discipline: unapproved data never enters git. R5 missing archival snapshots for live links → publication prerequisite rule. R6 date-precision loss (already observed) → contract date block + round-trip tests. R7 link rot → archived-URL requirement + quarterly dead-link reports. R8 accidental commit of ledger/PDFs to the public repo → gitignore rules + a pre-commit hook at M1 + test 5.

## 9. Assumptions (to correct if wrong)

A1. GitHub personal account on the Free plan (public repos get Pages; `oa-explorer` is public, and Pages stays disabled until M4). A2. Traffic stays far below Pages soft limits (100 GB/month). A3. Corpus size stays ≤ ~10k records over ten years (current DE: 412 rows / 269 KB CSV). A4. Zenodo remains free for archival data releases. A5. English-first UI with structured i18n so German (and later others) can be added without refactoring. A6. The corpus repo remains the research ledger of record; the explorer's detailed ledger stays in local, gitignored working copies (or institutional storage once U6 is settled).

## 10. First implementation milestone and next prompt

**Concrete first milestone: M1 vertical slice** (§6), scoped for 2–3 future sessions: scaffold → contract schemas → synthetic corpus → exporter → site (list/filter/record) → tests 1–10 → local preview + handover stub.

**Exact next prompt to use:**

> "Continue the plan in the oa-explorer repository (docs/plans/2026-11-07-explorer-plan.md). Implement Milestone M1 only: scaffold the repository layout from plan §4, write contract/ JSON Schemas and machine-readable vocabularies exactly per docs/plans/2026-11-07-data-contract-v0.1.md (keep the contract DRAFT; do not resolve open questions OQ1–OQ8 unilaterally), generate the synthetic seed corpus with all five required cases from plan §6/M1, implement export_ledger.py, build_public.py and the minimal site with list, filter and record pages, and write tests 1–10 from plan §7. Everything runs offline; nothing is published and no Pages deployment happens; commit only code, schemas, synthetic data and docs — the repository is public, so never commit ledger files, real data or PDFs. Report which tests pass and which are still unimplemented."

**Decisions you must still make (carried from this session):** ratify/amend the data contract (OQ1–OQ8, especially the public-field allowlist OQ3 and the long-term ledger location OQ6); provide or define the Axis 2 reviewed export (U1); choose the pilot record set for M2; institutional storage for PDF originals and the ledger (U4/U6); when to enable Pages (M4); optional custom domain and UI languages (U5).

