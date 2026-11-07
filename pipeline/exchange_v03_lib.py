#!/usr/bin/env python3
"""exchange_v03_lib.py — ROARA exchange contract v0.3 (draft) layer.

Builds on the v0.2 shape validator (`exchange_lib.validate_shape`) and
implements the six corpus-team design decisions resolved on 2026-11-08:

1. Score observations (`score_observations[]`) are stored separately from
   provisions. Each carries version, dimension, scale/codebook, nullable
   value, status, source scope, review extent, basis provision IDs and a
   comparability note. No dimension labels are hardcoded here and NO
   country composite is calculated: the authoritative ten-score codebook
   has not been supplied, so this layer only validates referential
   integrity. Score observations are never exported to public views.
2. Issuer `source_url`, optional `archived_url` and verified
   `archive_snapshots[]` metadata are kept separate. A mutable HTML
   page's live URL is not a time-stable original: an `archived_url` must
   be corroborated by a snapshot entry, and HTML captures without any
   snapshot raise a warning.
3. Cohort triggers are typed: `applies_to.event_type` (call_opened,
   award_made, grant_period_started, publication_date, submission_date,
   other, unreviewed). Cohort start/end dateClaims bind to that event
   type only and NEVER infer a general effective date.
4. `manifestation.retrieved_at` is the only retrieval event. Legacy
   `dateClaim.type=retrieved` is rejected in v0.3 data. Gazette
   publication (`published`), signature (`adopted`) and attachment-update
   (`other`) stay distinct claim types.
5. Identical SHA-256 duplicates may be linked by an explicit
   `duplicate_of_manifestation_id` alias only when bytes match (equal,
   non-null hashes), both records cross-reference the same version, and
   the target is not a translation. Aliases collapse to ONE underlying
   policy manifestation in counts; conflicting version assignments fail
   validation.
6. Every provision declares `cohort_applicability_status` and
   `cohort_ids`. `subset` must cite existing cohorts of its own version;
   `all_covered`, `unknown` and `not_applicable` must carry an empty
   array. `unknown` is never displayed as "all cohorts".

Design-fixture scope only: validated documents are synthetic. No real
corpus ingest happens here; public download/excerpt gates stay closed.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import exchange_lib as v02  # noqa: E402

# ---------------------------------------------------------------------------
# Decision 1: score observations — statuses that may/must carry a value.
# ---------------------------------------------------------------------------

VALUE_STATUSES = {"provisional_value", "reviewed_value"}
NULL_VALUE_STATUSES = {"unreviewed", "unknown", "reviewed_absence",
                       "not_applicable", "conflicted"}

# ---------------------------------------------------------------------------
# Decision 3/6: typed cohort triggers and cohort applicability display.
# ---------------------------------------------------------------------------

COHORT_EVENT_TYPES = {
    "call_opened", "award_made", "grant_period_started", "publication_date",
    "submission_date", "other", "unreviewed",
}

# Display strings. "unknown" deliberately does NOT render as "All cohorts".
COHORT_APPLICABILITY_DISPLAY = {
    "all_covered": "All cohorts",
    "unknown": "Unknown",
    "not_applicable": "Not applicable",
}

# ---------------------------------------------------------------------------
# Decision 4: retrieval lives only on manifestation.retrieved_at.
# ---------------------------------------------------------------------------

LEGACY_RETRIEVED_TYPE = "retrieved"

# Decision (v0.3.1): "published" and "promulgated" are DIFFERENT source
# events; neither automatically implies an effective date. The original's
# explicit trigger selects which event the effective date derives from.
LINKED_EFFECTIVE_CLAIM_TYPES = {
    "publication_linked": ("published",),
    "promulgation_linked": ("promulgated",),
    "approval_linked": ("approved",),
}
LINKED_EFFECTIVE_LABEL = {
    "publication_linked": "in force on publication",
    "promulgation_linked": "in force on promulgation",
    "approval_linked": "linked to approval date",
}
# Legacy v0.3-draft documents: promulgation linkage could still derive from
# a gazette "published" claim; v0.3.1 separates the two events.
LINKED_EFFECTIVE_CLAIM_TYPES_V03_LEGACY = {
    "promulgation_linked": ("promulgated", "published"),
    "approval_linked": ("approved",),
}

# Event types that are distinct source events whose dates must not be
# conflated (published vs promulgated).
EVENT_CLAIM_TYPES = ("published", "promulgated")


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_doc(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_schema(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Semantic validation
# ---------------------------------------------------------------------------

def _check_unique(values: list, what: str, errors: list[str]) -> None:
    seen: set = set()
    for v in values:
        if v in seen:
            errors.append(f"duplicate {what}: {v}")
        seen.add(v)


def validate_v03_scores(doc: dict, errors: list[str],
                        warnings: list[str]) -> None:
    """Decision 1: score definitions/observations are separate from
    provisions; referential integrity only — no labels hardcoded, no
    composite computed."""
    defs = doc.get("score_definitions", [])
    _check_unique([d["id"] for d in defs], "score definition id", errors)
    def_by_id = {d["id"]: d for d in defs}
    version_ids = {v["id"] for v in doc["versions"]}
    prov_by_id = {p["id"]: p for p in doc["provisions"]}
    obs_ids = [o["id"] for o in doc.get("score_observations", [])]
    _check_unique(obs_ids, "score observation id", errors)
    for o in doc.get("score_observations", []):
        oid = o["id"]
        if o["version_id"] not in version_ids:
            errors.append(f"score observation {oid}: unknown version "
                          f"{o['version_id']}")
        dim = def_by_id.get(o["dimension_id"])
        if dim is None:
            errors.append(f"score observation {oid}: unknown dimension_id "
                          f"{o['dimension_id']} (dimensions must come from "
                          f"score_definitions; the authoritative ten-score "
                          f"codebook has not been supplied)")
        elif o["scale_id"] != dim["scale_id"]:
            errors.append(
                f"score observation {oid}: scale_id {o['scale_id']} does "
                f"not match the scale of dimension {dim['id']} "
                f"({dim['scale_id']})")
        if o["status"] in VALUE_STATUSES and o["value"] is None:
            errors.append(f"score observation {oid}: status "
                          f"{o['status']} requires a value")
        if o["status"] in NULL_VALUE_STATUSES and o["value"] is not None:
            errors.append(f"score observation {oid}: status "
                          f"{o['status']} must leave value null, got "
                          f"{o['value']!r}")
        for pid in o.get("basis_provision_ids", []):
            p = prov_by_id.get(pid)
            if p is None:
                errors.append(f"score observation {oid}: unknown basis "
                              f"provision {pid}")
            elif p["version_id"] != o["version_id"]:
                errors.append(
                    f"score observation {oid}: basis provision {pid} "
                    f"belongs to version {p['version_id']}, not "
                    f"{o['version_id']}")
        # v0.3.1: actor/action are the POLICY actor and the evaluated
        # action, not the analyst; null when the clause mixes actors or
        # actions, with source_scope and basis provisions retaining the
        # detail. A valued observation naming an actor/action without any
        # basis provision loses its evidence trail.
        if o["status"] in VALUE_STATUSES and \
                (o.get("actor") is not None or o.get("action") is not None) \
                and not o.get("basis_provision_ids"):
            warnings.append(
                f"score observation {oid}: actor/action set but no basis "
                f"provision ids; retain source_scope and basis provisions "
                f"for mixed clauses (actor/action must then be null)")


def validate_v03_sources(doc: dict, errors: list[str],
                         warnings: list[str]) -> None:
    """Decision 2: issuer URL, archived_url and verified snapshots are
    separate; a live mutable URL is never treated as a time-stable
    original."""
    for m in doc["manifestations"]:
        mid = m["id"]
        snaps = m.get("archive_snapshots", [])
        snap_urls = {s["url"] for s in snaps}
        archived = m.get("archived_url")
        if archived is not None:
            matching = [s for s in snaps if s["url"] == archived]
            if not matching:
                errors.append(
                    f"manifestation {mid}: archived_url {archived} has no "
                    f"archive_snapshots entry at all; do not infer an "
                    f"archived URL from the live source_url")
            elif not any(s["capture_status"] in ("verified_bytes",
                                                 "issuer_attested")
                         for s in matching):
                # url_only / unreviewed snapshots: internal only, never a
                # public archive link
                warnings.append(
                    f"manifestation {mid}: archived_url {archived} is "
                    f"corroborated only by a non-verified snapshot "
                    f"({sorted(s['capture_status'] for s in matching)}); "
                    f"stays internal, never a public archive link")
        if m["role"] == "issuer_html_capture":
            if archived is None and not snaps:
                warnings.append(
                    f"manifestation {mid}: mutable issuer HTML capture "
                    f"has neither archived_url nor archive_snapshots; "
                    f"its live source_url is not a time-stable original")
        if m["role"] == "unrecovered_lead" and m.get("source_url") and \
                m.get("sha256"):
            warnings.append(
                f"manifestation {mid}: unrecovered lead carries both a "
                f"URL and a hash; verify before relying on either")


def validate_v03_duplicates(doc: dict, errors: list[str],
                            notes: list[str]) -> None:
    """Decision 5: explicit duplicate_of aliases only after matching
    bytes and cross-references; one underlying manifestation is counted;
    conflicting version assignments fail."""
    man_by_id = {m["id"]: m for m in doc["manifestations"]}
    for m in doc["manifestations"]:
        alias = m.get("duplicate_of_manifestation_id")
        if alias is None:
            continue
        mid = m["id"]
        tgt = man_by_id.get(alias)
        if tgt is None:
            errors.append(f"manifestation {mid}: duplicate_of target "
                          f"{alias} does not exist")
            continue
        if m.get("sha256") is None or tgt.get("sha256") is None:
            errors.append(f"manifestation {mid}: duplicate_of alias "
                          f"requires non-null sha256 on both records")
        elif m["sha256"] != tgt["sha256"]:
            errors.append(
                f"manifestation {mid}: duplicate_of {alias} but sha256 "
                f"differs ({m['sha256'][:12]}… vs "
                f"{tgt['sha256'][:12]}…); an alias is only allowed after "
                f"matching bytes")
        if m.get("version_id") != tgt.get("version_id"):
            errors.append(
                f"manifestation {mid}: duplicate_of {alias} assigns a "
                f"conflicting version ({m.get('version_id')} vs "
                f"{tgt.get('version_id')}); conflicting version "
                f"assignments fail review")
        if tgt["role"] == "translation" or m["role"] == "translation":
            errors.append(f"manifestation {mid}: duplicate_of alias on a "
                          f"translation; a translation must differ in bytes")
        if alias == mid:
            errors.append(f"manifestation {mid}: duplicate_of itself")
    # same-hash groups without an explicit alias
    by_hash: dict[str, list[dict]] = {}
    for m in doc["manifestations"]:
        if m.get("sha256"):
            by_hash.setdefault(m["sha256"], []).append(m)
    aliased = {m["duplicate_of_manifestation_id"]
               for m in doc["manifestations"]
               if m.get("duplicate_of_manifestation_id")}
    for h, ms in sorted(by_hash.items()):
        if len(ms) < 2:
            continue
        vids = {m.get("version_id") for m in ms}
        if len(vids) > 1:
            errors.append(
                f"duplicate source sha256 {h[:12]}… across versions "
                f"{sorted(str(v) for v in vids)}: the same bytes cannot "
                f"evidence different versions; conflicting version "
                f"assignments fail review")
        elif not any(m["id"] in aliased or
                     m.get("duplicate_of_manifestation_id")
                     for m in ms):
            notes.append(
                f"sha256 {h[:12]}… shared by {len(ms)} manifestations of "
                f"version {ms[0].get('version_id')} without an explicit "
                f"duplicate_of alias; counted as one underlying "
                f"manifestation, alias recommended for review")


def validate_v03_cohorts_and_provisions(doc: dict,
                                        errors: list[str]) -> None:
    """Decisions 3 and 6: typed cohort triggers bound to their event
    type; every provision declares cohort applicability and a subset must
    cite valid cohorts of its version."""
    for v in doc["versions"]:
        vid = v["id"]
        cohort_ids = {c["id"] for c in v.get("cohorts", [])}
        for co in v.get("cohorts", []):
            if co["applies_to"]["event_type"] not in COHORT_EVENT_TYPES:
                errors.append(f"version {vid}: cohort {co['id']} has "
                              f"untyped event_type "
                              f"{co['applies_to']['event_type']!r}")
            if co["start"]["type"] != "cohort_start":
                errors.append(f"version {vid}: cohort {co['id']} start "
                              f"claim must have type 'cohort_start' (the "
                              f"bound applies to the cohort event, not to "
                              f"a general effective date)")
            if co["end"]["type"] != "cohort_end":
                errors.append(f"version {vid}: cohort {co['id']} end "
                              f"claim must have type 'cohort_end'")
    for p in doc["provisions"]:
        pid = p["id"]
        status = p["cohort_applicability_status"]
        cids = p.get("cohort_ids", [])
        version = next((v for v in doc["versions"]
                        if v["id"] == p["version_id"]), None)
        valid = {c["id"] for c in version.get("cohorts", [])} \
            if version else set()
        if status == "subset":
            if not cids:
                errors.append(f"provision {pid}: cohort_applicability_"
                              f"status 'subset' requires at least one "
                              f"cohort id")
            for cid in cids:
                if cid not in valid:
                    errors.append(
                        f"provision {pid}: cohort id {cid} is not a "
                        f"cohort of version {p['version_id']}")
        else:
            if cids:
                errors.append(
                    f"provision {pid}: cohort_ids must be empty unless "
                    f"status is 'subset' (status is {status!r})")


def validate_v03_dates(doc: dict, errors: list[str]) -> None:
    """Decision 4: reject legacy retrieved dateClaims; keep signature,
    gazette publication and attachment-update distinct."""
    for v in doc["versions"]:
        for c in v.get("dates", []):
            if c["type"] == LEGACY_RETRIEVED_TYPE:
                errors.append(
                    f"version {v['id']}: legacy dateClaim type "
                    f"'retrieved' is rejected in v0.3; retrieval is "
                    f"recorded only as manifestation.retrieved_at")


def _linked_types(doc: dict, interp: str) -> tuple[str, ...]:
    legacy = doc.get("schema_version") == "0.3-draft"
    table = (LINKED_EFFECTIVE_CLAIM_TYPES_V03_LEGACY if legacy
             else LINKED_EFFECTIVE_CLAIM_TYPES)
    return table.get(interp, ())


def validate_v03_date_semantics(doc: dict, errors: list[str],
                                warnings: list[str],
                                notes: list[str] | None = None) -> None:
    """v0.3.1 date-claim invariants: published and promulgated are
    distinct source events; if both are valued and disagree, both are
    preserved and the effective date may only derive from the original's
    explicit trigger (conflict if that trigger is unclear). Cohort
    thresholds never leak into the general effective date; unknown-start
    cohorts are not negative-infinity starts."""
    if notes is None:
        notes = []
    for v in doc["versions"]:
        vid = v["id"]
        valued_effective: list[dict] = []
        claims_by_type: dict[str, list[dict]] = {}
        for c in v.get("dates", []):
            val, prec = c.get("value"), c.get("precision")
            claims_by_type.setdefault(c["type"], []).append(c)
            if prec == "unknown" and val is not None:
                errors.append(f"{vid}: date claim {c['type']} has "
                              f"precision unknown but a value {val!r}")
            if val is not None and prec != "unknown":
                if not v02.PRECISION_RE[prec].fullmatch(val):
                    errors.append(f"{vid}: date claim {c['type']} value "
                                  f"{val!r} does not match precision "
                                  f"{prec}")
            if c["type"] == "effective" and val is not None:
                valued_effective.append(c)
            if val is not None and c.get("status") == "unreviewed":
                warnings.append(f"{vid}: date claim {c['type']} has a "
                                f"value but status 'unreviewed'")
        if len(valued_effective) > 1:
            errors.append(f"{vid}: {len(valued_effective)} valued "
                          f"effective claims; at most one is unambiguous")
        interp = v.get("effective_date_interpretation")
        if interp == "explicit" and not valued_effective:
            errors.append(f"{vid}: effective_date_interpretation "
                          f"'explicit' but no valued effective claim")
        linked = _linked_types(doc, interp) if interp else ()
        if linked:
            if valued_effective:
                errors.append(
                    f"{vid}: effective_date_interpretation {interp!r} "
                    f"conflicts with an explicit valued effective claim; "
                    f"use 'explicit'")
            if not any(c.get("value")
                       for ct in linked
                       for c in claims_by_type.get(ct, [])):
                errors.append(f"{vid}: interpretation {interp!r} but no "
                              f"valued claim of type "
                              f"{' or '.join(linked)} to derive from")
        # distinct source events: published vs promulgated
        event_vals = {et: [c.get("value") for c in claims_by_type.get(et, [])
                           if c.get("value")] for et in EVENT_CLAIM_TYPES}
        if event_vals["published"] and event_vals["promulgated"] and \
                set(event_vals["published"]) != set(event_vals["promulgated"]):
            if interp in ("publication_linked", "promulgation_linked",
                          "explicit"):
                notes.append(
                    f"{vid}: published {event_vals['published']} and "
                    f"promulgated {event_vals['promulgated']} disagree; "
                    f"both preserved; effective derived only from the "
                    f"explicit trigger {interp!r}")
            else:
                errors.append(
                    f"{vid}: published {event_vals['published']} and "
                    f"promulgated {event_vals['promulgated']} disagree but "
                    f"the explicit trigger is unclear "
                    f"(effective_date_interpretation={interp!r}); declare "
                    f"'publication_linked'/'promulgation_linked' or mark "
                    f"'conflicted'")
        if interp == "cohort_only":
            if valued_effective:
                errors.append(
                    f"{vid}: effective_date_interpretation 'cohort_only' "
                    f"but an explicit valued effective claim exists; a "
                    f"cohort threshold is not a general effective date")
            if not v.get("cohorts"):
                errors.append(f"{vid}: interpretation 'cohort_only' but "
                              f"the version has no cohorts")
        for co in v.get("cohorts", []):
            start = co["start"]
            if not start.get("value"):
                if start.get("status") not in ("unknown", "unreviewed"):
                    errors.append(
                        f"{vid}: cohort {co['id']} has neither a start "
                        f"value nor an unknown/unreviewed status; an "
                        f"unknown start is not a negative-infinity start")
                if start.get("precision") != "unknown":
                    errors.append(
                        f"{vid}: cohort {co['id']} start without value "
                        f"must have precision 'unknown'")
            end = co["end"]
            if end.get("value") is None:
                # supported unbounded end (status not_applicable) vs
                # unknown end (status unknown/unreviewed)
                if end.get("status") == "not_applicable":
                    notes.append(
                        f"{vid}: cohort {co['id']} has a supported "
                        f"unbounded end (explicitly no upper bound)")
                elif end.get("status") in ("unknown", "unreviewed"):
                    notes.append(
                        f"{vid}: cohort {co['id']} end is UNKNOWN, not "
                        f"unbounded; excluded from definite date-filtered "
                        f"claims")
                else:
                    errors.append(
                        f"{vid}: cohort {co['id']} end has no value but "
                        f"status {end.get('status')!r}; use "
                        f"not_applicable (supported unbounded) or "
                        f"unknown/unreviewed")
        if not valued_effective and interp is None and v.get("cohorts"):
            warnings.append(f"{vid}: has cohorts but neither an effective "
                            f"claim nor an effective_date_interpretation")


def validate_v03(doc: dict, schema: dict) -> tuple[list[str], list[str],
                                                   list[str]]:
    """Full v0.3/v0.3.1 validation: v0.2 shape+cross-refs, then the six
    decisions plus the v0.3.1 event/cohort refinements. Returns
    (errors, warnings, notes)."""
    errors: list[str] = []
    validate_v032_legacy_enums(doc, errors)
    shape_errors = v02.validate_shape(doc, schema)
    errors.extend(shape_errors)
    if shape_errors:
        return errors, [], []
    warnings: list[str] = []
    notes: list[str] = []
    v02.validate_cross_references(doc, errors)
    hash_errors, _hash_notes = v02.check_duplicate_hashes(doc)
    # cross-version and translation duplicate hashes stay hard errors;
    # same-version duplicates additionally need an explicit alias, which
    # validate_v03_duplicates checks below.
    errors.extend(hash_errors)
    validate_v03_date_semantics(doc, errors, warnings, notes)
    validate_v03_dates(doc, errors)
    validate_v03_scores(doc, errors, warnings)
    validate_v03_sources(doc, errors, warnings)
    validate_v03_duplicates(doc, errors, notes)
    validate_v03_cohorts_and_provisions(doc, errors)
    validate_v032_semantics(doc, errors, warnings, notes)
    return errors, warnings, notes


# ---------------------------------------------------------------------------
# Decision 5: one underlying manifestation per alias group
# ---------------------------------------------------------------------------

def distinct_manifestations(doc: dict) -> list[dict]:
    """Underlying policy manifestations: records carrying a
    duplicate_of_manifestation_id alias are collapsed into their target
    and not counted separately."""
    return [m for m in doc["manifestations"]
            if not m.get("duplicate_of_manifestation_id")]


# ---------------------------------------------------------------------------
# Decision 3/4: effective-date resolution (cohorts never consulted)
# ---------------------------------------------------------------------------

@dataclass
class Effective:
    value: str | None
    precision: str
    status: str
    basis: str
    note: str = ""


def resolve_effective_v03(version: dict,
                          schema_version: str = "0.3.1-draft") -> Effective:
    """General effective date of a version. Only an explicit valued
    effective claim or a declared linked interpretation produces a date;
    cohort boundaries are NEVER consulted. In v0.3.1, publication_linked
    derives from the 'published' event and promulgation_linked from the
    'promulgated' event — they are different source events. (Legacy
    0.3-draft documents allowed promulgation linkage to derive from a
    gazette 'published' claim.)"""
    eff = [c for c in version.get("dates", [])
           if c["type"] == "effective" and c.get("value")]
    if eff:
        c = eff[0]
        return Effective(c["value"], c["precision"], c["status"],
                         "explicit effective date claim",
                         c.get("note") or "")
    interp = version.get("effective_date_interpretation")
    legacy = schema_version == "0.3-draft"
    table = (LINKED_EFFECTIVE_CLAIM_TYPES_V03_LEGACY if legacy
             else LINKED_EFFECTIVE_CLAIM_TYPES)
    if interp in table:
        for claim_type in table[interp]:
            c = next((x for x in version.get("dates", [])
                      if x["type"] == claim_type and x.get("value")), None)
            if c:
                return Effective(c["value"], c["precision"], c["status"],
                                 LINKED_EFFECTIVE_LABEL[interp],
                                 c.get("note") or "")
    return Effective(None, "unknown", "unknown", "",
                     next((c.get("note") for c in version.get("dates", [])
                           if c["type"] == "effective"), ""))


# ---------------------------------------------------------------------------
# v0.3.1: cohort start/end semantics — unknown start is not negative
# infinity; supported unbounded end is distinct from an unknown end.
# ---------------------------------------------------------------------------

def cohort_definite_start(co: dict) -> bool:
    """True only when the cohort has a valued start bound; an
    unknown/unreviewed start must not be treated as valid from negative
    infinity or included in definite date-filtered compliance claims."""
    return bool(co["start"].get("value"))


def cohorts_with_definite_start(version: dict) -> list[dict]:
    return [c for c in version.get("cohorts", []) if cohort_definite_start(c)]


def cohort_end_kind(co: dict) -> str:
    """'bounded' (valued end), 'unbounded_supported' (null end with
    status not_applicable — the original explicitly has no upper bound),
    or 'unknown' (null end with status unknown/unreviewed)."""
    end = co["end"]
    if end.get("value") is not None:
        return "bounded"
    if end.get("status") == "not_applicable":
        return "unbounded_supported"
    return "unknown"


# ---------------------------------------------------------------------------
# v0.3.1: a PUBLIC archive link requires verified snapshot contents/date
# plus the separate link-rights and review gates. A bare archived_url or
# a url_only snapshot stays internal.
# ---------------------------------------------------------------------------

def verified_snapshot_for(m: dict, url: str) -> dict | None:
    """The verified-bytes snapshot entry corroborating url, if any."""
    for s in m.get("archive_snapshots", []):
        if s["url"] == url and s["capture_status"] == "verified_bytes":
            return s
    return None


def public_archive_link(m: dict) -> str | None:
    """Archived URL that may appear in a PUBLIC view: requires a
    verified-bytes snapshot (contents/date verified), link-level rights
    and a passed review gate. Bare archived_url or url_only snapshots
    return None (internal only)."""
    url = m.get("archived_url")
    if not url:
        return None
    if verified_snapshot_for(m, url) is None:
        return None
    if m["rights_status"] not in v02.PUBLIC_RIGHTS:
        return None
    if m["review"]["state"] not in v02.PASS_REVIEW_STATES:
        return None
    return url


# ---------------------------------------------------------------------------
# v0.3.1: attested-but-unrecovered leads (e.g. an issuer news item dating
# adoption) must not enter main-version comparison or public views.
# ---------------------------------------------------------------------------

def comparison_eligible_versions(doc: dict) -> list[dict]:
    """Versions eligible for comparison views: passed the review gate and
    are not attested-but-unrecovered leads."""
    return [v for v in doc["versions"]
            if v["review"]["state"] in v02.PASS_REVIEW_STATES
            and v["source_status"] != "attested_unrecovered"]


def effective_display_v03(eff: Effective) -> str:
    if eff.value is None:
        return v02.UNKNOWN_EFFECTIVE_DISPLAY
    if eff.basis == "explicit effective date claim":
        return eff.value
    return f"{eff.value} ({eff.basis})"


# ---------------------------------------------------------------------------
# Decision 6: cohort applicability display — unknown is never "all"
# ---------------------------------------------------------------------------

def cohort_applicability_display(provision: dict) -> str:
    status = provision["cohort_applicability_status"]
    if status == "subset":
        return "Subset of cohorts: " + ", ".join(
            provision.get("cohort_ids", []))
    return COHORT_APPLICABILITY_DISPLAY[status]


# ---------------------------------------------------------------------------
# Public reader views — score observations and unapproved excerpts stay
# closed even when the release flag is on.
# ---------------------------------------------------------------------------

@dataclass
class PublicConfigV03:
    document_links: bool = True
    downloads: bool = False
    excerpts: bool = True


def build_public_views_v03(doc: dict, cfg: PublicConfigV03,
                           qc_holds: set[str] | None = None) -> dict:
    """Gated reader views for a v0.3 document. Extends the v0.2 gating:
    provisions additionally expose their cohort-applicability display, and
    score observations are ALWAYS withheld (no authoritative codebook,
    no composite) with the withheld count stated. Q2: internal QC holds
    (qc_holds, from a local-only workbook) withhold their versions even
    when release.public_release_approved=true; the hold itself is never
    exported."""
    base = v02.build_public_views(doc, v02.PublicConfig(
        document_links=cfg.document_links,
        downloads=cfg.downloads,
        excerpts=cfg.excerpts))
    if qc_holds:
        held = [r for r in base.get("records", []) if r["id"] in qc_holds]
        if held:
            base["records"] = [r for r in base["records"]
                               if r["id"] not in qc_holds]
            base["withheld_count"] = base.get("withheld_count", 0) + \
                len(held)
    base["score_observations"] = {
        "shown": 0,
        "withheld_count": len(doc.get("score_observations", [])),
        "note": ("Score observations are withheld: the authoritative "
                 "ten-score codebook has not been supplied and no country "
                 "composite is calculated."),
    }
    # Rebuild each public record's provision views so the cohort
    # applicability display (decision 6) is attached by provision id,
    # not matched by anchor text.
    pub_man_ids = {m["id"] for m in doc["manifestations"]
                   if v02._manifestation_is_public(m)}
    provs_by_version: dict[str, list[dict]] = {}
    for p in doc["provisions"]:
        provs_by_version.setdefault(p["version_id"], []).append(p)
    mans_by_version: dict[str, list[dict]] = {}
    for m in doc["manifestations"]:
        if m.get("version_id"):
            mans_by_version.setdefault(m["version_id"], []).append(m)
    ver_by_id = {v["id"]: v for v in doc["versions"]}
    sv = doc.get("schema_version", "0.3.1-draft")
    for record in base.get("records", []):
        # recompute effective with v0.3.1 semantics (publication_linked
        # derives from 'published', promulgation_linked from 'promulgated')
        v = ver_by_id[record["id"]]
        eff = resolve_effective_v03(v, schema_version=sv)
        record["effective"] = {
            "display": effective_display_v03(eff),
            "value": eff.value,
            "basis": eff.basis,
            "status": eff.status,
            "note": eff.note or None,
        }
        # base provision views are sorted by provision id and were built
        # from the same id-sorted, gate-filtered list, so zip positionally
        visible = [p for p in sorted(provs_by_version.get(record["id"], []),
                                     key=lambda x: x["id"])
                   if p["manifestation_id"] in pub_man_ids]
        for p, pv in zip(visible, record["provisions"]):
            pv["cohort_applicability"] = cohort_applicability_display(p)
        # v0.3.1: a public archive link appears only with a verified-bytes
        # snapshot plus link-rights and review gates (bare archived_url /
        # url_only snapshots stay internal)
        if cfg.document_links:
            vis_mans = [m for m in sorted(mans_by_version.get(record["id"],
                                                              []),
                                          key=lambda x: x["id"])
                        if v02._manifestation_is_public(m)]
            for m, sv in zip(vis_mans, record["sources"]):
                sv["archived_url"] = public_archive_link(m)
        else:
            for sv in record["sources"]:
                sv["archived_url"] = None
    return base


# ---------------------------------------------------------------------------
# v0.3.2 semantic layer (schema_version "0.3.2-draft") — the eight resolved
# questions Q2/Q4/Q7/Q10–Q13/Q15 as semantic checks on top of shape.
# ---------------------------------------------------------------------------

V032 = "0.3.2-draft"

# Removed enum values: migration is allowed ONLY with evidence, never by
# string mapping alone. The validator rejects them with guidance.
LEGACY_ENUM_RULES = {
    ("version", "authority_status", "announcement_attested"):
        "removed in v0.3.2: migrate to authority_status=approved + "
        "source_status=attested_unrecovered ONLY with authority evidence; "
        "never by string mapping alone",
    ("version", "source_status", "draft_only"):
        "removed in v0.3.2: a recovered draft is authority_status=draft + "
        "source_status=original_recovered; migrate only after checking "
        "evidence",
    ("organization", "issuer_type", "unreviewed"):
        "removed in v0.3.2: use issuer_type=null with "
        "identity_review.state=unreviewed; review state is not a type",
}


def validate_v032_legacy_enums(doc: dict, errors: list[str]) -> None:
    """Reject removed v0.3.1 enum values with evidence-based migration
    guidance instead of silently re-mapping strings."""
    if doc.get("schema_version") != V032:
        return
    for v in doc.get("versions", []):
        for field, value in (("authority_status", v.get("authority_status")),
                             ("source_status", v.get("source_status"))):
            rule = LEGACY_ENUM_RULES.get(("version", field, value))
            if rule:
                errors.append(f"version {v['id']}: {field}={value!r} — {rule}")
    for o in doc.get("organizations", []):
        rule = LEGACY_ENUM_RULES.get(("organization", "issuer_type",
                                      o.get("issuer_type")))
        if rule:
            errors.append(f"organization {o['id']}: issuer_type="
                          f"{o.get('issuer_type')!r} — {rule}")


def validate_v032_semantics(doc: dict, errors: list[str],
                            warnings: list[str], notes: list[str]) -> None:
    """v0.3.2 rules, applied only to 0.3.2-draft documents."""
    if doc.get("schema_version") != V032:
        return
    family_ids = {f["id"] for f in doc.get("families", [])}
    version_ids = {v["id"] for v in doc.get("versions", [])}
    man_by_id = {m["id"]: m for m in doc.get("manifestations", [])}
    mans_by_version: dict[str, list[dict]] = {}
    for m in doc.get("manifestations", []):
        if m.get("version_id"):
            mans_by_version.setdefault(m["version_id"], []).append(m)

    for m in doc.get("manifestations", []):
        mid = m["id"]
        # Q15: version_id=null is permitted ONLY for a family-bound
        # unrecovered lead; every other role requires a version binding
        if m.get("version_id") is None:
            if m["role"] != "unrecovered_lead":
                errors.append(
                    f"manifestation {mid}: version_id null is allowed only "
                    f"for role=unrecovered_lead (Q15); role {m['role']!r} "
                    f"requires a version binding")
            elif not m.get("family_id"):
                errors.append(
                    f"manifestation {mid}: null version_id requires "
                    f"family_id (family-bound unrecovered lead)")
            elif m["family_id"] not in family_ids:
                errors.append(f"manifestation {mid}: unknown family_id "
                              f"{m['family_id']}")
        # Q7: captured issuer HTML defaults to unreviewed rights; a public
        # URL permits at most a reviewed link-only route, never
        # redistribution of captured HTML
        if m["role"] == "issuer_html_capture":
            if m["rights_status"] == "public_redistribution_approved":
                errors.append(
                    f"manifestation {mid}: captured issuer HTML can never "
                    f"be public_redistribution_approved; link-only after "
                    f"URL and link-rights review at most (Q7)")
            elif m["rights_status"] == "link_only_approved" and \
                    m["review"]["state"] not in v02.PASS_REVIEW_STATES:
                warnings.append(
                    f"manifestation {mid}: link_only_approved is an "
                    f"affirmative decision; review state "
                    f"{m['review']['state']!r} does not yet support it")
        # Q11: physical_pages is a leaf COUNT, null for HTML
        if m["format"] == "html" and m.get("physical_pages") is not None:
            warnings.append(f"manifestation {mid}: physical_pages must be "
                            f"null for HTML (count of physical PDF leaves)")

    for v in doc.get("versions", []):
        vid = v["id"]
        # Q4: authority standing and source recovery are orthogonal
        if v["authority_status"] in ("issued", "approved") and \
                v["source_status"] == "attested_unrecovered" and \
                not (v["review"].get("note")):
            warnings.append(
                f"version {vid}: approved/issued + attested_unrecovered "
                f"needs a provenance/review caveat note (no operative "
                f"bytes recovered)")
        # Q4: a true contradiction between evidence claims is a QC
        # conflict, never silently overwritten
        if v["authority_status"] in ("issued", "approved"):
            for m in mans_by_version.get(vid, []):
                ev = (m.get("authority_evidence") or "").lower()
                if "draft" in ev:
                    errors.append(
                        f"version {vid}: authority contradiction — "
                        f"authority_status={v['authority_status']!r} but "
                        f"manifestation {m['id']} evidence says draft; "
                        f"routed to QC conflict (review.state=conflicted), "
                        f"never silently overwritten")
        # Q10: languages arrays; manifestation languages should be a subset
        vlangs = set(v.get("languages", []))
        if not vlangs:
            notes.append(f"version {vid}: languages empty = language "
                         f"unreviewed")
        for m in mans_by_version.get(vid, []):
            extra = set(m.get("languages", [])) - vlangs
            if extra:
                warnings.append(
                    f"manifestation {m['id']}: languages {sorted(extra)} "
                    f"not present in version {vid} languages "
                    f"{sorted(vlangs)}")

    for o in doc.get("organizations", []):
        # Q12: null issuer type carries review state in identity_review
        if o.get("issuer_type") is None and \
                o.get("identity_review", {}).get("state") != "unreviewed":
            warnings.append(
                f"organization {o['id']}: issuer_type null should pair with "
                f"identity_review.state=unreviewed")

    for p in doc.get("provisions", []):
        # Q11: anchor starts with the physical page and preserves the
        # printed label when different
        anchor = p.get("anchor", "")
        if "printed p." in anchor and "physical p." not in anchor:
            warnings.append(
                f"provision {p['id']}: anchor cites a printed page label "
                f"without the physical page; anchors start with physical "
                f"page (e.g. 'physical p.56; printed p.53')")

    rel = doc.get("release", {})
    # Q13: as_of is the content/review cutoff, published_at the separate
    # publication timestamp; a later publication never moves as_of
    as_of, published_at = rel.get("as_of"), rel.get("published_at")
    if as_of and published_at and str(as_of) > published_at[:10]:
        errors.append(
            f"release: as_of {as_of} is after published_at "
            f"{published_at}; contents cannot be described through a date "
            f"after the release's own publication")


def load_internal_qc_holds(path: Path) -> set[str]:
    """Read a LOCAL-ONLY internal QC workbook column
    (version_id, public_import_status) and return the held version ids.
    Q2: the hold is internal and independent of release approval/rights;
    the workbook itself is never committed to this public repository."""
    import csv
    holds: set[str] = set()
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if (row.get("public_import_status") or "").strip() == "hold":
                holds.add(row["version_id"].strip())
    return holds


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Validate a ROARA exchange document against the "
                    "draft v0.3 contract (shape + six design decisions).")
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--schema", required=True, type=Path)
    ap.add_argument("--json", action="store_true",
                    help="print the full report as JSON")
    args = ap.parse_args(argv)
    doc = load_doc(args.input)
    schema = load_schema(args.schema)
    errors, warnings, notes = validate_v03(doc, schema)
    report = {
        "input": str(args.input),
        "schema_version": doc.get("schema_version"),
        "errors": errors,
        "warnings": warnings,
        "notes": notes,
        "distinct_manifestation_count": len(distinct_manifestations(doc)),
        "score_observation_count": len(doc.get("score_observations", [])),
    }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{args.input} (schema_version={report['schema_version']})")
        print(f"  errors: {len(errors)}  warnings: {len(warnings)}  "
              f"notes: {len(notes)}")
        for e in errors:
            print(f"  ERROR   {e}")
        for w in warnings:
            print(f"  WARNING {w}")
        for n in notes:
            print(f"  note    {n}")
        print(f"  distinct underlying manifestations: "
              f"{report['distinct_manifestation_count']} "
              f"(of {len(doc['manifestations'])})")
        print(f"  score observations: "
              f"{report['score_observation_count']} (never composited)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
