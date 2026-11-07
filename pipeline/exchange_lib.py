#!/usr/bin/env python3
"""exchange_lib.py — ROARA exchange contract v0.2 (draft) layer.

Loads and validates exchange documents against the draft v0.2 JSON Schema
(shape), then goes beyond shape checking with:

- cross-reference validation (FK integrity, composite evidence binding,
  component chains, relationship acyclicity),
- duplicate source-hash validation (mirrors are legal; cross-version or
  translation duplicates are errors),
- typed date-claim semantics: adoption/approval, publication,
  promulgation, effective, retrieval (webpage modification) and cohort
  boundaries stay distinct; a cohort threshold NEVER infers a general
  effective date,
- rights/review-gated public reader views that hide records whose gates
  have not passed, with independently configurable display of document
  links, downloads and excerpts, and that never expose technical
  collection columns (source hashes, reviewer identity, internal
  evidence pointers).

Design-fixture scope only: the synthetic exchange document contains
fictional records. No real corpus ingest happens here.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

UNKNOWN_EFFECTIVE_DISPLAY = "Unknown / not established"

PRECISION_RE = {
    "year": re.compile(r"^\d{4}$"),
    "month": re.compile(r"^\d{4}-\d{2}$"),
    "day": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
}

# Review states that pass the public gate. Everything else
# (unreviewed, provisionally_reviewed, conflicted) is withheld.
PASS_REVIEW_STATES = {"analyst_checked", "independently_reviewed"}
# Manifestation rights that permit a public appearance at all.
PUBLIC_RIGHTS = {"public_redistribution_approved", "link_only_approved"}
# Rights that additionally permit a download affordance.
DOWNLOAD_RIGHTS = {"public_redistribution_approved"}
# Provision excerpt rights that permit public excerpt display.
EXCERPT_PUBLIC = {"approved_for_public_export"}

DATE_TYPE_LABELS = {
    "adopted": "Adopted",
    "approved": "Approved",
    "published": "Published",
    "effective": "Effective",
    "promulgated": "Promulgated",
    "retrieved": "Retrieved",
    "review_due": "Review due",
    "other": "Other date",
    "cohort_start": "Cohort start",
    "cohort_end": "Cohort end",
}

FUNCTION_LABELS = {
    "institutional_oa_os": "Institutional OA/OS policy",
    "funder_grant_term": "Funder grant terms",
    "national_os_strategy": "National strategy target",
    "national_assessment_subsidy": "National assessment / subsidy rule",
    "repository_operation": "Repository rules",
    "apc_funding_criteria": "APC eligibility",
    "research_data_governance": "Research data governance",
    "announcement": "Announcement",
    "other": "Other",
    "unreviewed": "Unreviewed",
}

# Interpretation types that derive a general effective date from another
# claim instead of an explicit effective claim.
LINKED_EFFECTIVE = {
    "promulgation_linked": ("promulgated", "in force on promulgation"),
    "approval_linked": ("approved", "linked to approval date"),
}


# --------------------------------------------------------------------------
# Shape validation — JSON Schema subset (draft 2020-12 constructs used by
# the v0.2 schema: type incl. unions with null, const, enum, pattern,
# minLength, minItems, uniqueItems, minimum, required, properties,
# additionalProperties:false, items, $ref to #/$defs, format as annotation
# with light date/uri checks).
# --------------------------------------------------------------------------

def _resolve_ref(ref: str, root: dict) -> dict:
    if not ref.startswith("#/"):
        raise ValueError(f"only root-relative $ref supported, got {ref}")
    node: object = root
    for part in ref[2:].split("/"):
        node = node[part]  # type: ignore[index]
    return node  # type: ignore[return-value]


def _type_ok(inst: object, ty: str) -> bool:
    if ty == "object":
        return isinstance(inst, dict)
    if ty == "array":
        return isinstance(inst, list)
    if ty == "string":
        return isinstance(inst, str)
    if ty == "integer":
        return isinstance(inst, int) and not isinstance(inst, bool)
    if ty == "number":
        return isinstance(inst, (int, float)) and not isinstance(inst, bool)
    if ty == "boolean":
        return isinstance(inst, bool)
    if ty == "null":
        return inst is None
    return False


def _check_format(inst: str, fmt: str, path: str, errors: list[str]) -> None:
    """Draft 2020-12 treats format as annotation; we do light checks."""
    if fmt == "date" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", inst):
        errors.append(f"{path}: not a valid date (YYYY-MM-DD): {inst!r}")
    elif fmt == "date-time" and not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})", inst):
        errors.append(f"{path}: not a valid date-time: {inst!r}")
    elif fmt == "uri" and not re.match(r"^[a-z][a-z0-9+.-]*://", inst):
        errors.append(f"{path}: not an absolute URI: {inst!r}")


def validate_shape(inst: object, schema: dict, root: dict | None = None,
                   path: str = "$", errors: list[str] | None = None,
                   ) -> list[str]:
    """Validate inst against a schema fragment. Returns the error list."""
    if errors is None:
        errors = []
    if root is None:
        root = schema
    if "$ref" in schema:
        return validate_shape(inst, _resolve_ref(schema["$ref"], root),
                              root, path, errors)
    ty = schema.get("type")
    if ty is not None:
        types = ty if isinstance(ty, list) else [ty]
        if not any(_type_ok(inst, t) for t in types):
            errors.append(f"{path}: expected type {types}, "
                          f"got {type(inst).__name__}")
            return errors
    if "const" in schema and inst != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}, "
                      f"got {inst!r}")
    if "enum" in schema and inst not in schema["enum"]:
        errors.append(f"{path}: {inst!r} not in enum {schema['enum']}")
    if isinstance(inst, str):
        if "pattern" in schema and not re.search(schema["pattern"], inst):
            errors.append(f"{path}: {inst!r} does not match "
                          f"pattern {schema['pattern']!r}")
        if "minLength" in schema and len(inst) < schema["minLength"]:
            errors.append(f"{path}: shorter than minLength "
                          f"{schema['minLength']}")
        if "format" in schema:
            _check_format(inst, schema["format"], path, errors)
    if isinstance(inst, (int, float)) and not isinstance(inst, bool):
        if "minimum" in schema and inst < schema["minimum"]:
            errors.append(f"{path}: below minimum "
                          f"{schema['minimum']}")
    if isinstance(inst, list):
        if "minItems" in schema and len(inst) < schema["minItems"]:
            errors.append(f"{path}: fewer than minItems {schema['minItems']}")
        if schema.get("uniqueItems") and len(inst) != len(
                {json.dumps(i, sort_keys=True) for i in inst}):
            errors.append(f"{path}: items are not unique")
        if "items" in schema:
            for i, item in enumerate(inst):
                validate_shape(item, schema["items"], root,
                               f"{path}[{i}]", errors)
    if isinstance(inst, dict):
        for req in schema.get("required", []):
            if req not in inst:
                errors.append(f"{path}: required property {req!r} missing")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in inst:
                if key not in props:
                    errors.append(f"{path}: additional property "
                                  f"{key!r} not allowed")
        for key, val in inst.items():
            if key in props:
                validate_shape(val, props[key], root,
                               f"{path}.{key}", errors)
    return errors


# --------------------------------------------------------------------------
# Loading and semantic validation
# --------------------------------------------------------------------------

def load_exchange(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_schema(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _check_unique(values: list, what: str, errors: list[str],
                  label_fn=None) -> None:
    seen: set = set()
    for v in values:
        key = v if not callable(label_fn) else label_fn(v)
        if key in seen:
            errors.append(f"duplicate {what}: {key}")
        seen.add(key)


def validate_cross_references(doc: dict, errors: list[str]) -> None:
    """Beyond shape: FK integrity, evidence binding, component chains,
    relationship acyclicity."""
    country_codes = [c["code"] for c in doc["countries"]]
    _check_unique(country_codes, "country code", errors)
    org_ids = [o["id"] for o in doc["organizations"]]
    _check_unique(org_ids, "organization id", errors)
    org_set = set(org_ids)
    for o in doc["organizations"]:
        if o["country_code"] not in country_codes:
            errors.append(f"organization {o['id']}: unknown country_code "
                          f"{o['country_code']}")
    family_ids = [f["id"] for f in doc["families"]]
    _check_unique(family_ids, "family id", errors)
    for f in doc["families"]:
        if f["issuer_id"] not in org_set:
            errors.append(f"family {f['id']}: unknown issuer "
                          f"{f['issuer_id']}")
    version_ids = [v["id"] for v in doc["versions"]]
    _check_unique(version_ids, "version id", errors)
    version_set = set(version_ids)
    for v in doc["versions"]:
        if v["family_id"] not in family_ids:
            errors.append(f"version {v['id']}: unknown family "
                          f"{v['family_id']}")
        for oid in v["issuer_ids"]:
            if oid not in org_set:
                errors.append(f"version {v['id']}: unknown issuer {oid}")
        seen_cohort_ids: set[str] = set()
        for c in v.get("cohorts", []):
            if c["id"] in seen_cohort_ids:
                errors.append(f"version {v['id']}: duplicate cohort id "
                              f"{c['id']}")
            seen_cohort_ids.add(c["id"])

    man_ids = [m["id"] for m in doc["manifestations"]]
    _check_unique(man_ids, "manifestation id", errors)
    man_set = set(man_ids)
    man_by_id = {m["id"]: m for m in doc["manifestations"]}
    for m in doc["manifestations"]:
        vid = m.get("version_id")
        if vid is not None and vid not in version_set:
            errors.append(f"manifestation {m['id']}: unknown version {vid}")
    # component chains: resolve, no self-reference, no cycles
    for m in doc["manifestations"]:
        comp = m.get("component_of_manifestation_id")
        if comp is None:
            continue
        if comp not in man_set:
            errors.append(f"manifestation {m['id']}: component_of "
                          f"{comp} does not exist")
        elif comp == m["id"]:
            errors.append(f"manifestation {m['id']}: component_of itself")
    for m in doc["manifestations"]:
        chain, node = {m["id"]}, m
        while node.get("component_of_manifestation_id"):
            nxt = node["component_of_manifestation_id"]
            if nxt not in man_set:
                break
            if nxt in chain:
                errors.append(f"manifestation {m['id']}: "
                              f"component_of cycle")
                break
            chain.add(nxt)
            node = man_by_id[nxt]

    prov_ids = [p["id"] for p in doc["provisions"]]
    _check_unique(prov_ids, "provision id", errors)
    for p in doc["provisions"]:
        if p["version_id"] not in version_set:
            errors.append(f"provision {p['id']}: unknown version "
                          f"{p['version_id']}")
        if p["manifestation_id"] not in man_set:
            errors.append(f"provision {p['id']}: unknown manifestation "
                          f"{p['manifestation_id']}")
        else:
            m = man_by_id[p["manifestation_id"]]
            if m.get("version_id") is None:
                errors.append(f"provision {p['id']}: bound to "
                              f"manifestation {m['id']} which has no "
                              f"version")
            elif m["version_id"] != p["version_id"]:
                errors.append(
                    f"provision {p['id']}: bound to manifestation "
                    f"{m['id']} of version {m['version_id']}, not of "
                    f"{p['version_id']} (evidence must come from a "
                    f"manifestation of the same version)")

    rel_ids = [r["id"] for r in doc["relationships"]]
    _check_unique(rel_ids, "relationship id", errors)
    edges: dict[str, list[str]] = {vid: [] for vid in version_ids}
    for r in doc["relationships"]:
        for end in ("earlier_version_id", "later_version_id"):
            if r[end] not in version_set:
                errors.append(f"relationship {r['id']}: unknown "
                              f"{end} {r[end]}")
        if r["earlier_version_id"] == r["later_version_id"]:
            errors.append(f"relationship {r['id']}: relates a version "
                          f"to itself")
        if r.get("evidence_manifestation_id") not in (None,) and \
                r["evidence_manifestation_id"] not in man_set:
            errors.append(f"relationship {r['id']}: unknown evidence "
                          f"manifestation {r['evidence_manifestation_id']}")
        if r["earlier_version_id"] in version_set and \
                r["later_version_id"] in version_set:
            edges[r["earlier_version_id"]].append(r["later_version_id"])
    # cycle detection over earlier->later edges
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {vid: WHITE for vid in version_ids}

    def visit(vid: str) -> None:
        colour[vid] = GREY
        for nxt in edges[vid]:
            if colour.get(nxt, BLACK) == GREY:
                errors.append(f"relationship cycle through version {nxt}")
            elif colour.get(nxt, BLACK) == WHITE:
                visit(nxt)
        colour[vid] = BLACK

    for vid in version_ids:
        if colour[vid] == WHITE:
            visit(vid)

    # date-claim evidence pointers
    for v in doc["versions"]:
        for c in v.get("dates", []):
            em = c.get("evidence_manifestation_id")
            if em is not None and em not in man_set:
                errors.append(f"version {v['id']}: date claim "
                              f"{c['type']} cites unknown manifestation "
                              f"{em}")


def check_duplicate_hashes(doc: dict) -> tuple[list[str], list[str]]:
    """Duplicate source hashes: legal only as mirror/alternate copies of
    the same version's document. Cross-version duplicates and duplicates
    involving a translation are errors. Everything else is recorded as a
    note for the review report."""
    errors: list[str] = []
    notes: list[str] = []
    by_hash: dict[str, list[dict]] = {}
    for m in doc["manifestations"]:
        h = m.get("sha256")
        if h:
            by_hash.setdefault(h, []).append(m)
    for h, ms in sorted(by_hash.items()):
        if len(ms) < 2:
            continue
        vids = {m.get("version_id") for m in ms}
        roles = sorted({m.get("role") for m in ms})
        if len(vids) > 1:
            errors.append(
                f"duplicate source sha256 {h[:12]}… across versions "
                f"{sorted(str(v) for v in vids)}: the same file content "
                f"cannot evidence different versions")
        elif "translation" in roles:
            errors.append(
                f"duplicate source sha256 {h[:12]}… on a translation "
                f"manifestation: a translation must differ from its "
                f"original")
        else:
            notes.append(
                f"sha256 {h[:12]}… shared by {len(ms)} manifestations of "
                f"version {ms[0].get('version_id')} (roles {roles}); "
                f"treated as mirror/alternate copies of one document")
    return errors, notes


def validate_date_semantics(doc: dict, errors: list[str],
                            warnings: list[str]) -> None:
    """Date-claim invariants and the cohort/effective separation rules."""
    for v in doc["versions"]:
        vid = v["id"]
        valued_effective: list[dict] = []
        claims_by_type: dict[str, list[dict]] = {}
        for c in v.get("dates", []):
            val, prec = c.get("value"), c.get("precision")
            claims_by_type.setdefault(c["type"], []).append(c)
            # precision/value consistency
            if prec == "unknown" and val is not None:
                errors.append(f"{vid}: date claim {c['type']} has "
                              f"precision unknown but a value {val!r}; "
                              f"unknown precision must leave the value "
                              f"null")
            if val is not None and prec != "unknown":
                if not PRECISION_RE[prec].fullmatch(val):
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
        if interp in LINKED_EFFECTIVE:
            if valued_effective:
                errors.append(
                    f"{vid}: effective_date_interpretation {interp!r} "
                    f"conflicts with an explicit valued effective claim; "
                    f"use 'explicit'")
            claim_type = LINKED_EFFECTIVE[interp][0]
            if not any(c.get("value") for c in claims_by_type
                       .get(claim_type, [])):
                errors.append(f"{vid}: interpretation {interp!r} but no "
                              f"valued {claim_type} claim to derive from")
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
            if not co["start"].get("value"):
                errors.append(f"{vid}: cohort {co['id']} has no start "
                              f"value; a cohort must begin somewhere")
            if co["start"].get("type") != "cohort_start":
                warnings.append(f"{vid}: cohort {co['id']} start claim "
                                 f"type is {co['start'].get('type')!r}, "
                                 f"expected 'cohort_start'")
            if co["end"].get("value") is None and \
                    co["end"].get("precision") != "unknown":
                errors.append(f"{vid}: cohort {co['id']} has no end "
                              f"value but end precision is "
                              f"{co['end'].get('precision')!r}; open "
                              f"ended cohorts must declare precision "
                              f"'unknown'")
        if not valued_effective and interp is None and v.get("cohorts"):
            warnings.append(f"{vid}: has cohorts but neither an effective "
                            f"claim nor an "
                            f"effective_date_interpretation; consider "
                            f"declaring 'cohort_only' or 'unknown'")


def validate_exchange(doc: dict, schema: dict) -> tuple[list[str],
                                                        list[str]]:
    """Full validation: shape first; semantics only when shape passes.
    Returns (errors, warnings)."""
    errors = validate_shape(doc, schema)
    if errors:
        return errors, []
    warnings: list[str] = []
    validate_cross_references(doc, errors)
    hash_errors, hash_notes = check_duplicate_hashes(doc)
    errors.extend(hash_errors)
    warnings.extend(hash_notes)
    validate_date_semantics(doc, errors, warnings)
    return errors, warnings


# --------------------------------------------------------------------------
# Effective-date resolution (cohort thresholds never leak in)
# --------------------------------------------------------------------------

@dataclass
class Effective:
    value: str | None
    precision: str
    status: str
    basis: str
    note: str = ""


def resolve_effective(version: dict) -> Effective:
    """Resolve the general effective date of a version. Only explicit
    effective claims or a declared linked interpretation can produce a
    date; cohort boundaries are NEVER consulted here."""
    eff = [c for c in version.get("dates", [])
            if c["type"] == "effective" and c.get("value")]
    if eff:
        c = eff[0]
        return Effective(c["value"], c["precision"], c["status"],
                         "explicit effective date claim",
                         c.get("note") or "")
    interp = version.get("effective_date_interpretation")
    if interp in LINKED_EFFECTIVE:
        claim_type, basis = LINKED_EFFECTIVE[interp]
        c = next((x for x in version.get("dates", [])
                  if x["type"] == claim_type and x.get("value")), None)
        if c:
            return Effective(c["value"], c["precision"], c["status"],
                             basis, c.get("note") or "")
    return Effective(None, "unknown", "unknown", "",
                     next((c.get("note") for c in version.get("dates", [])
                           if c["type"] == "effective"), ""))


def effective_display(eff: Effective) -> str:
    if eff.value is None:
        return UNKNOWN_EFFECTIVE_DISPLAY
    if eff.basis == "explicit effective date claim":
        return eff.value
    return f"{eff.value} ({eff.basis})"


# --------------------------------------------------------------------------
# Public reader views (rights/review gates, configurable display)
# --------------------------------------------------------------------------

@dataclass
class PublicConfig:
    document_links: bool = True
    downloads: bool = False
    excerpts: bool = True


def _claim_view(c: dict) -> dict:
    return {
        "type": c["type"],
        "label": DATE_TYPE_LABELS.get(c["type"], c["type"]),
        "value": c.get("value"),
        "precision": c.get("precision"),
        "status": c.get("status"),
        "note": c.get("note") or None,
        "physical_anchor": c.get("physical_anchor") or None,
    }


def _cohort_view(co: dict) -> dict:
    end_val = co["end"].get("value")
    return {
        "id": co["id"],
        "applies_to": co["applies_to"],
        "start": co["start"].get("value"),
        "start_precision": co["start"].get("precision"),
        "end": end_val,
        "end_precision": co["end"].get("precision"),
        "bounded": end_val is not None,
        "exceptions": co.get("exceptions") or None,
        "review_state": co["review"]["state"],
    }


def version_is_public(version: dict) -> bool:
    return version["review"]["state"] in PASS_REVIEW_STATES


def _manifestation_is_public(m: dict) -> bool:
    return (m["rights_status"] in PUBLIC_RIGHTS
            and m["review"]["state"] in PASS_REVIEW_STATES)


def build_public_views(doc: dict, cfg: PublicConfig) -> dict:
    """Gated reader views. Hides versions whose review gate has not
    passed, manifestations whose rights gate has not passed, and all
    technical collection columns (source hashes, reviewer identity,
    review extent, internal evidence pointers). Link, download and
    excerpt display are independently configurable."""
    total = len(doc["versions"])
    if not doc["release"]["public_release_approved"]:
        return {
            "release_approved": False,
            "release_id": doc["release"]["release_id"],
            "records": [],
            "withheld_count": total,
            "note": ("Release not approved for public view; every "
                     "record is withheld."),
        }
    orgs = {o["id"]: o for o in doc["organizations"]}
    fams = {f["id"]: f for f in doc["families"]}
    mans_by_version: dict[str, list[dict]] = {}
    for m in doc["manifestations"]:
        if m.get("version_id"):
            mans_by_version.setdefault(m["version_id"], []).append(m)
    provs_by_version: dict[str, list[dict]] = {}
    for p in doc["provisions"]:
        provs_by_version.setdefault(p["version_id"], []).append(p)
    man_by_id = {m["id"]: m for m in doc["manifestations"]}
    public_version_ids = {v["id"] for v in doc["versions"]
                          if version_is_public(v)}

    records = []
    for v in doc["versions"]:
        if not version_is_public(v):
            continue
        # sources (manifestations that pass both gates)
        sources = []
        for m in sorted(mans_by_version.get(v["id"], []),
                        key=lambda x: x["id"]):
            if not _manifestation_is_public(m):
                continue
            link = cfg.document_links and bool(m.get("source_url"))
            download = (cfg.downloads
                        and m["rights_status"] in DOWNLOAD_RIGHTS
                        and bool(m.get("source_url")))
            sources.append({
                "kind": m["role"],
                "format": m["format"],
                "language": m.get("language"),
                "languages": m.get("languages"),
                "url": m.get("source_url") if link else None,
                "download_url": m.get("source_url") if download else None,
                "rights": m["rights_status"],
                "captured": m.get("retrieved_at"),
                "mutable": m["role"] == "issuer_html_capture",
            })
        # provisions (bound to public manifestations only)
        provisions = []
        for p in sorted(provs_by_version.get(v["id"], []),
                        key=lambda x: x["id"]):
            m = man_by_id.get(p["manifestation_id"])
            if m is None or not _manifestation_is_public(m):
                continue
            rights_ok = p["excerpt_rights_status"] in EXCERPT_PUBLIC
            show = rights_ok and cfg.excerpts
            provisions.append({
                "anchor": p["anchor"],
                "actor": p.get("actor"),
                "action": p.get("action"),
                "object": p.get("object"),
                "scope": p.get("scope"),
                "modality": p.get("modality"),
                "condition": p.get("condition"),
                "exception": p.get("exception"),
                "original_excerpt": p["original_excerpt"] if show else None,
                "translation_english": p.get("translation_english")
                if show else None,
                "excerpt_withheld_reason":
                    None if show else (
                        "excerpts_disabled" if rights_ok
                        else "rights_not_approved"),
                "function_relation": p.get("function_relation"),
                "code_status": p.get("code_status"),
            })
        # relationships (other endpoint identified only if it is public)
        rels = []
        for r in sorted(doc["relationships"], key=lambda x: x["id"]):
            if v["id"] not in (r["earlier_version_id"],
                               r["later_version_id"]):
                continue
            other = (r["later_version_id"]
                     if r["earlier_version_id"] == v["id"]
                     else r["earlier_version_id"])
            rels.append({
                "type": r["type"],
                "direction": "later" if r["earlier_version_id"] == v["id"]
                             else "earlier",
                "other_version": other if other in public_version_ids
                                 else None,
                "other_withheld": other not in public_version_ids,
                "anchor": r.get("anchor"),
            })
        eff = resolve_effective(v)
        records.append({
            "id": v["id"],
            "title_original": v["title_original"],
            "title_english": v.get("title_english"),
            "language": v.get("language"),
            "languages": v.get("languages"),
            "function": v["instrument_function"],
            "function_label": FUNCTION_LABELS.get(v["instrument_function"],
                                                  v["instrument_function"]),
            "family_label": fams.get(v.get("family_id", ""),
                                     {}).get("family_label", ""),
            "issuers": [orgs[oid]["name"] for oid in v["issuer_ids"]
                        if oid in orgs],
            "authority_status": v["authority_status"],
            "source_status": v["source_status"],
            "review_state": v["review"]["state"],
            "review_note": v["review"].get("note") or None,
            "scope_note": v.get("scope_note") or None,
            "dates": [_claim_view(c) for c in v.get("dates", [])],
            "effective": {
                "display": effective_display(eff),
                "value": eff.value,
                "basis": eff.basis,
                "status": eff.status,
                "note": eff.note or None,
            },
            "cohorts": [_cohort_view(co) for co in v.get("cohorts", [])],
            "provisions": provisions,
            "sources": sources,
            "relationships": rels,
        })
    records.sort(key=lambda r: r["id"])
    return {
        "release_approved": True,
        "release_id": doc["release"]["release_id"],
        "records": records,
        "withheld_count": total - len(records),
        "note": (f"{total - len(records)} of {total} records are "
                 f"withheld from this view pending review and rights "
                 f"gates." if total - len(records) else
                 "All records in this exchange are shown."),
    }
