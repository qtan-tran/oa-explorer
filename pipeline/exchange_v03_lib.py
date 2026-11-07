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

# Decision 4 companion: promulgation-linked effectiveness may derive from a
# gazette publication claim ("published") as well as an explicit
# "promulgated" claim — e.g. "in force upon publication in the official
# gazette".
LINKED_EFFECTIVE_CLAIM_TYPES = {
    "promulgation_linked": ("promulgated", "published"),
    "approval_linked": ("approved",),
}
LINKED_EFFECTIVE_LABEL = {
    "promulgation_linked": "in force on promulgation / gazette publication",
    "approval_linked": "linked to approval date",
}


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


def validate_v03_scores(doc: dict, errors: list[str]) -> None:
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
            corroborated = any(
                s["url"] == archived
                and s["capture_status"] in ("verified_bytes",
                                            "issuer_attested")
                for s in snaps)
            if not corroborated:
                errors.append(
                    f"manifestation {mid}: archived_url {archived} is not "
                    f"corroborated by a verified/issuer-attested "
                    f"archive_snapshots entry; do not infer an archived "
                    f"URL from the live source_url")
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


def validate_v03_date_semantics(doc: dict, errors: list[str],
                                warnings: list[str]) -> None:
    """v0.3 date-claim invariants: like v0.2, but promulgation linkage
    may derive from a gazette 'published' claim as well as 'promulgated',
    and cohort thresholds never leak into the general effective date."""
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
        if interp in LINKED_EFFECTIVE_CLAIM_TYPES:
            if valued_effective:
                errors.append(
                    f"{vid}: effective_date_interpretation {interp!r} "
                    f"conflicts with an explicit valued effective claim; "
                    f"use 'explicit'")
            if not any(c.get("value")
                       for ct in LINKED_EFFECTIVE_CLAIM_TYPES[interp]
                       for c in claims_by_type.get(ct, [])):
                errors.append(f"{vid}: interpretation {interp!r} but no "
                              f"valued claim of type "
                              f"{' or '.join(LINKED_EFFECTIVE_CLAIM_TYPES[interp])} "
                              f"to derive from")
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
            if not co["start"].get("value") and \
                    co["start"].get("status") not in ("unknown", "unreviewed"):
                errors.append(f"{vid}: cohort {co['id']} has neither a "
                              f"start value nor an unknown/unreviewed "
                              f"status; a cohort must begin somewhere or "
                              f"be declared unknown")
        if not valued_effective and interp is None and v.get("cohorts"):
            warnings.append(f"{vid}: has cohorts but neither an effective "
                            f"claim nor an effective_date_interpretation")


def validate_v03(doc: dict, schema: dict) -> tuple[list[str], list[str],
                                                   list[str]]:
    """Full v0.3 validation: v0.2 shape+cross-refs, then the six
    decisions. Returns (errors, warnings, notes)."""
    errors = v02.validate_shape(doc, schema)
    if errors:
        return errors, [], []
    errors: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []
    v02.validate_cross_references(doc, errors)
    hash_errors, _hash_notes = v02.check_duplicate_hashes(doc)
    # cross-version and translation duplicate hashes stay hard errors;
    # same-version duplicates additionally need an explicit alias, which
    # validate_v03_duplicates checks below.
    errors.extend(hash_errors)
    validate_v03_date_semantics(doc, errors, warnings)
    validate_v03_dates(doc, errors)
    validate_v03_scores(doc, errors)
    validate_v03_sources(doc, errors, warnings)
    validate_v03_duplicates(doc, errors, notes)
    validate_v03_cohorts_and_provisions(doc, errors)
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


def resolve_effective_v03(version: dict) -> Effective:
    """General effective date of a version. Only an explicit valued
    effective claim or a declared linked interpretation produces a date;
    cohort boundaries are NEVER consulted. Promulgation linkage may
    derive from a gazette 'published' claim as well as 'promulgated'."""
    eff = [c for c in version.get("dates", [])
           if c["type"] == "effective" and c.get("value")]
    if eff:
        c = eff[0]
        return Effective(c["value"], c["precision"], c["status"],
                         "explicit effective date claim",
                         c.get("note") or "")
    interp = version.get("effective_date_interpretation")
    if interp in LINKED_EFFECTIVE_CLAIM_TYPES:
        for claim_type in LINKED_EFFECTIVE_CLAIM_TYPES[interp]:
            c = next((x for x in version.get("dates", [])
                      if x["type"] == claim_type and x.get("value")), None)
            if c:
                return Effective(c["value"], c["precision"], c["status"],
                                 LINKED_EFFECTIVE_LABEL[interp],
                                 c.get("note") or "")
    return Effective(None, "unknown", "unknown", "",
                     next((c.get("note") for c in version.get("dates", [])
                           if c["type"] == "effective"), ""))


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


def build_public_views_v03(doc: dict, cfg: PublicConfigV03) -> dict:
    """Gated reader views for a v0.3 document. Extends the v0.2 gating:
    provisions additionally expose their cohort-applicability display, and
    score observations are ALWAYS withheld (no authoritative codebook,
    no composite) with the withheld count stated."""
    base = v02.build_public_views(doc, v02.PublicConfig(
        document_links=cfg.document_links,
        downloads=cfg.downloads,
        excerpts=cfg.excerpts))
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
    for record in base.get("records", []):
        # base provision views are sorted by provision id and were built
        # from the same id-sorted, gate-filtered list, so zip positionally
        visible = [p for p in sorted(provs_by_version.get(record["id"], []),
                                     key=lambda x: x["id"])
                   if p["manifestation_id"] in pub_man_ids]
        for p, pv in zip(visible, record["provisions"]):
            pv["cohort_applicability"] = cohort_applicability_display(p)
    return base


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
