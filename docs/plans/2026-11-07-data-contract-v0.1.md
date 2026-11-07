# Data contract v0.1 — DRAFT (pending corpus-team ratification)

Status: **DRAFT for discussion.** Nothing in this document is mandatory until the
corpus team ratifies it (see "Ratification"). Companion: the master plan
(`2026-11-07-explorer-plan.md`) and ADR 0001. The 56-column schema in the corpus
repo (`schema/data_dictionary.md`) remains the research ledger of record; this
contract is the explorer's interchange model with a documented migration from it.
Because the `oa-explorer` repository is public, full-detail ledger files under
this contract live only in local, gitignored working copies (plan decision D4);
the repository carries the contract definitions, never the ledger data.

Design rules that override everything else: no invented data; no composite
ranking; unknown ≠ not applicable ≠ reviewed absence ≠ numeric zero; adoption
and effective dates are distinct; partial dates never invent a day; original
language text is first-class; every public fact is separately approved; source
documents are never redistributed without per-item permission review.

---

## 1. Entities and stable IDs

One CSV file per entity (plus a language table), mirrored as JSON. IDs are
opaque, immutable, never reused or renumbered; sequence carries no meaning.

| Entity | File | ID pattern | Notes |
|---|---|---|---|
| Country | `countries.csv` | ISO 3166-1 alpha-2 (`DE`) | names via texts table |
| Organization | `organizations.csv` | `O-{ISO}-{NNNN}` | dedupes v1 rows; carries ror/openalex |
| Policy family | `policy_families.csv` | `F-{ISO}-{NNNN}` | the continuing instrument of one issuer |
| Policy version | `policy_versions.csv` | `V-{ISO}-{NNNN}` | dated version of a family; carries the ten ROARA scores |
| Source manifestation | `manifestations.csv` | `M-{ISO}-{NNNN}` | one concrete source artifact of a version |
| Provision | `provisions.csv` | `P-{ISO}-{NNNN}` | one coded statement with evidence anchor |
| Version relationship | `version_relationships.csv` | `R-{NNNN}` | typed edge between two versions |
| Language layer | `texts.csv` | composite key | entity_id, field, lang, text |
| Function payloads | `version_functions.csv` | composite key | optional policy-function-specific JSON |

**Countries** carry corpus status (active/planned) and the country-level context
defaults from v1's extension variables (`legal_relationship`,
`constitutional_freedom_protection`, `funder_mandate_*`), each with its own
`value_state` and evidence/citation fields. Per-organization overrides live on
the organization (e.g., private institutions, contract-research institutes).

**Organizations** carry: country, tier (`RPO`/`RFO`), institution type raw +
controlled category, ROR, OpenAlex, screening fields (`has_policy` with
value_state semantics — reviewed absence is `measured` + `N`), and
`legacy_refs` (the v1 `document_id` list). A source-inventory row is not
necessarily a policy version (OQ2).

**Policy families** carry: issuer organization, `authority_level`
(`institutional`/`funder`/`national`/`institutional_within_national`, migrates
v1 `governance_level`), `instrument_function` (controlled vocabulary below),
`policy_area` (OA/Mixed/OS), and a scope note.

**Policy versions** carry: family, title (texts), version label, the adopted
date block and the effective date block (independent), status
(`in_force`/`superseded`/`withdrawn`/`repealed`/`unknown`), official languages,
the ten ROARA scores (each with `value_state`), derived family means and
`composite_0_30` (descriptive only, never ranking), `evidence_confidence`,
`special_stratum`, and `legacy_ref`.

**Manifestations** carry: version, form (html/pdf/doc/print/other), language,
verbatim title, live URL, archived URL + archive date + archive service,
retrieved date, `access_status`
(`open_public`/`open_login`/`restricted`/`removed`/`unrecovered`), optional
size/checksum, offline `storage_ref` (a manifest path in durable storage
outside git, never a repo path), and the **permission block** (below).

**Provisions** carry: version, evidence manifestation, `modality`, actor,
action, object, scope, conditions, exceptions, excerpt text + excerpt
language, `anchor` (physical page/article/section/paragraph) + optional URL
fragment, `review_extent` (`full_text`/`selected_sections`/`summary_document`),
and an uncertainty note.

**Relationships** carry: from/to version IDs, `type`
(`replaces`/`amended_by`/`implements`/`inherits_floor_from`/`template_of`/`related`),
evidence anchor, and review state. `replaces` chains must be acyclic (tested).
v1 mapping: `update_group` → replaces chain; `policy_source=Inherited*` +
`governing_umbrella` → `inherits_floor_from`; `template_group` → `template_of`.

**Texts table:** `(entity_id, field, lang, text, language_status)` with BCP 47
language codes and `language_status` = `original`/`translation`/`gloss`.
Original-language excerpts are also stored inline in provisions with their
language code, because excerpt language is evidentiary, not presentational.

**Version functions (optional, policy-function-specific data):** keyed
`(version_id, function)`; `function` ∈ the instrument-function vocabulary; value
is a JSON payload whose per-function sub-shape is documented in the data
dictionary. Initial functions migrate v1's qualitative fields where they can be
structured: `apc_eligibility`, `embargo_terms`, `rights_retention`,
`repository_rules`, `monitoring`, `assessment_link`, plus a generic
`descriptive_notes` for fields that resist structuring (OQ7).

## 2. Controlled vocabularies

All vocabularies live in one machine-readable file, `contract/vocabularies.csv`
(`vocabulary, value, definition, status`), which the validator reads. Extending
a vocabulary is a MINOR contract change (additive, versioned). The v1
`policy_source` drift observed in the DE data (`Own (pending)`,
`Inherited (floor)`, …) is handled by a documented legacy-value mapping file,
`contract/legacy_map_v1.csv`, not by silent acceptance.

Key vocabularies: `instrument_function` (national assessment/subsidy rules;
funder grant terms; institutional OA/OS policy; repository rules; APC
eligibility; implementation guidance; announcement); `modality` (obligation;
expectation; recommendation; permission; prohibition; incentive; exemption;
commitment; description); `value_state`; `review_state`; `date_basis`;
`date_precision`; `access_status`; `rights_status`; relationship types; the
v1-inherited enums (tier, institution_category, coding_status-equivalents,
evidence_confidence).

## 3. Null and status semantics

Every factual value column is paired with a `value_state`:

| value_state | Meaning | Value column |
|---|---|---|
| `measured` | reviewed; value present (including numeric 0 — a real zero) | required |
| `measured` + `0` | reviewed numeric zero | 0 |
| `reviewed_absent` | reviewed; confirmed absence (presence-type questions only) | empty |
| `not_applicable` | the question does not apply to this record | empty |
| `unknown` | not yet reviewed or not determinable from available sources | empty |

Invariants (validated): a value present with `unknown`/`not_applicable` is
invalid; a blank with `measured` is invalid; `reviewed_absent` is only legal on
fields whose vocabulary is presence-typed. The four required distinctions are
therefore always machine-checkable, and survive CSV→JSON→CSV round-trips.

Record-level publication gating is separate: every row carries `review_state`
(`draft`/`unreviewed`/`in_review`/`reviewed`/`approved_public`),
`public_visible` (true only with `approved_public`), `approved_by`,
`approved_date`, and optional `withhold_reason`. Approval is per record, so a
country, an organization or a single version can be published partially.

## 4. Dates

Two independent blocks per version, `adopted_*` and `effective_*`, each with:
`date_iso` (truncated: `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` — never a padded fake
day), `date_precision` (year/month/day), `date_basis`
(adopted/effective/published/inferred/unknown), `date_confidence`
(stated/inferred/uncertain), and `date_verbatim` (the original string exactly
as found in the source: `01.12.2005`, `Wintersemester 2019/20`, `not stated`).
The DE corpus's mixed `adoption_date` formats (pandas timestamps, D/M/YYYY,
D.M.YYYY, bare years, free text) migrate with verbatim preserved and precision
derived conservatively; anything ambiguous becomes `unknown` + verbatim, not a
guess. `nominal_year` (v1) maps to `adopted_date_iso` at year precision with
its `year_basis`.

## 5. Permissions (per manifestation, independently reviewed)

| Field | Vocabulary |
|---|---|
| `rights_status` | `public_domain` / `open_license` / `copyright_all_rights` / `mixed` / `unknown` |
| `redistribution` | `permitted` / `not_permitted` / `unknown` |
| `attribution_required` | `yes` / `no` / `unknown` |
| `excerpt_policy` | `quotation_exception` / `permitted` / `not_permitted` / `unknown` |
| `permission_evidence` | free text: the basis for the classification, with citation |
| `permission_reviewed_by` / `permission_reviewed_date` | reviewer + date |

Rules: public accessibility is never taken as permission to redistribute. PDFs
are never committed to any repo; the explorer links to issuer copies and
archival snapshots. An excerpt may be exported publicly only if
`excerpt_policy` permits (or a documented quotation exception applies) AND the
provision carrying it is approved; otherwise the record page shows the anchor
and links only. `policy_url_archived` is a publication prerequisite for every
record with a live link (currently 0/138 in DE).

## 6. Provenance

Every row carries: `legacy_ref` (v1 document_id(s) it derives from),
`created_by`, `created_date`, `last_reviewed_by`, `last_reviewed_date`, and
`change_note` (one line, what changed and why, replacing in-place edits). The
local ledger additionally holds free-text coder commentary (including v1
`comment`, audit flags, addenda corrections), which are **never public**.
Exports record their inputs: corpus repo release tag, exporter version,
contract version, run date, and output SHA-256 in the ledger's provenance file
(its public subset, `ledger/provenance_public.csv`, is publishable).

## 7. Public export vs research ledger

- **Ledger** (local, gitignored; never in this public repo): full contract
  files with commentary, review markers, permission evidence, uncertainty
  notes. The research-ledger-of-record remains the corpus repo; the explorer
  ledger holds the contract-shaped view derived from pinned corpus releases.
- **Public export** (`exports/public/`, generated, never hand-edited,
  committed only after M4 approval): includes ONLY fields on the ratified
  **public allowlist** from records with `review_state=approved_public`, and
  only manifestations with `access_status=open_public` links; excludes
  commentary, coder notes, permission-evidence text, `[verify]` markers,
  restricted/unrecovered originals (their existence may be summarized as a
  count), and anything non-approved.
- **Proposed initial allowlist (ratification item OQ3):** country/organization
  identifiers, names (original language + gloss), categories, tier; family
  metadata (issuer, authority level, instrument function, policy area);
  version metadata (title, dates, status, languages, scores + value_states,
  derived values, evidence_confidence); relationship edges; provision
  modality/actor/action/object/scope/conditions/exceptions + approved
  excerpts + anchors; live and archived URLs of public manifestations; review
  metadata (review_state, review_extent, approved_date — approver identity to
  be decided); schema version and export provenance.

## 8. Schema versioning, validation, migration

- `contract/VERSION` holds the contract semver: MAJOR = breaking (removals,
  renames, semantic changes), MINOR = additive, PATCH = clarifications. Every
  file's JSON Schema declares the version in `$id`.
- **Validation** (extends the corpus repo's `validate_schema.py` patterns):
  column presence/order; ID format and uniqueness; vocabulary membership from
  `vocabularies.csv`; value_state invariants; date-precision logic; referential
  integrity (see plan test 2); relationship acyclicity; allowlist enforcement
  on exports (nothing outside the allowlist may appear in `exports/public/`).
- **Migration:** numbered scripts (`contract/migrations/001_*.py`), one per
  version bump, deterministic, each writing a dated backup + changelog entry +
  mapping log. Additive changes default to null/`unknown`. Renames go through
  an explicit mapping table and keep a one-release alias. The v1→contract
  migration itself is such a script, run per country, and produces a
  discrepancy log for human review — never a silent transform.
- Old schema support: the previous MINOR version stays importable for at least
  one release, so pipeline consumers can upgrade on their own schedule.

## 9. Mapping from the v1 56-column schema (summary)

One v1 row decomposes into: organization (dedup by name/ROR across rows),
its screening fields, and — for rows with a coded policy — a policy family +
version + manifestation(s) + scores. `nominal_year`/`year_basis`/`adoption_date`
→ date blocks; extension variables → country defaults + org overrides;
`policy_source` + `governing_umbrella` + `update_group` + `template_group` →
typed relationships; qualitative free-text fields → version_functions payloads
or provisions; `comment` → private ledger commentary. Multi-version
institutions (v1: `update_group`) become separate versions joined by `replaces`
edges. Detailed per-column mapping is part of M2, reviewed per pilot record.

## 10. Ratification (open questions for the corpus team — DO NOT assume)

- **OQ1.** Are the nine entities the right decomposition, or does the team
  need finer/coarser splits (e.g., should policy families also exist for
  funder records, given v1's tier concept)?
- **OQ2.** Confirm: a screening row without a policy maps to organization +
  screening status only (no family/version), preserving the real denominators.
- **OQ3.** Ratify or amend the public-field allowlist (§7), including whether
  approver identities are public.
- **OQ4.** Country-level context defaults vs per-organization overrides: is
  the proposed split faithful to the extension schema's intent?
- **OQ5.** How should existing `[verify: …]` markers be handled at
  publication (publish as explicit uncertainty vs exclude until resolved)?
  They are currently public in the corpus repo.
- **OQ6.** Where does the private ledger durably live now that the explorer
  repo is public (local working copies are the session-1 default; institutional
  storage is the preferred long-term answer), and who else needs access?
- **OQ7.** Which of the qualitative v1 fields should become structured
  `version_functions` payloads vs remain descriptive text?
- **OQ8.** Relationship-type list sufficient? (e.g., is a `partially_implements`
  or `responds_to` edge needed for national-funder institutional policies?)

Until ratification, this contract is a proposal; the M1 slice builds it as
software but no real data passes through it.

