"""Shared contract library: loading, validation and interchange for the OA/OS
Policy Explorer data contract (v0.1 DRAFT).

Standard library only (see ADR 0002). This module is the single place that
knows the contract's rules; export_ledger.py and build_public.py both use it.
"""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

CONTRACT_VERSION_FILE = "VERSION"
VOCABULARIES_FILE = "vocabularies.csv"
SCHEMA_DIR = "json-schema"
ALLOWLIST_FILE = "public_allowlist.csv"

ENTITY_FILES = {
    "country": "countries.csv",
    "organization": "organizations.csv",
    "policy_family": "policy_families.csv",
    "policy_version": "policy_versions.csv",
    "manifestation": "manifestations.csv",
    "provision": "provisions.csv",
    "version_relationship": "version_relationships.csv",
    "text": "texts.csv",
    "version_function": "version_functions.csv",
}

SCORE_DIMENSIONS = [
    "ms_mandate_strength", "rl_rights_licensing", "comp_compliance",
    "inf_infrastructure", "fund_funding", "repo_repository",
    "eval_evaluation", "mon_monitoring", "gov_governance", "osb_os_breadth",
]

# (value column, value_state column) pairs governed by the null/status rules.
VALUE_STATE_PAIRS = {
    "country": [
        ("legal_relationship", "legal_relationship_value_state"),
        ("constitutional_freedom_protection", "constitutional_freedom_protection_value_state"),
        ("funder_mandate_present", "funder_mandate_present_value_state"),
    ],
    "organization": [("has_policy", "has_policy_value_state")],
    "manifestation": [("live_url", "live_url_value_state"),
                      ("archived_url", "archived_url_value_state")],
    "provision": [("conditions", "conditions_value_state"),
                  ("exceptions", "exceptions_value_state"),
                  ("excerpt_text", "excerpt_value_state")],
}
VALUE_STATE_PAIRS["policy_version"] = [
    (f"score_{d}", f"score_{d}_value_state") for d in SCORE_DIMENSIONS
]

# entity.field -> vocabulary name in vocabularies.csv (single source of truth).
FIELD_VOCAB = {
    "country": {"corpus_status": "corpus_status",
                "legal_relationship": "legal_relationship",
                "constitutional_freedom_protection": "constitutional_freedom_protection",
                "funder_mandate_present": "funder_mandate_present"},
    "organization": {"institution_category": "institution_category", "tier": "tier",
                      "has_policy": "has_policy_v1", "coding_status": "coding_status_v1"},
    "policy_family": {"authority_level": "authority_level",
                      "instrument_function": "instrument_function",
                      "policy_area": "policy_area"},
    "policy_version": {"status": "version_status", "evidence_confidence": "evidence_confidence"},
    "manifestation": {"form": "form", "access_status": "access_status",
                      "rights_status": "rights_status", "redistribution": "redistribution",
                      "attribution_required": "attribution_required",
                      "excerpt_policy": "excerpt_policy"},
    "provision": {"modality": "modality", "review_extent": "review_extent"},
    "version_relationship": {"type": "relationship_type"},
    "text": {"language_status": "language_status"},
    "version_function": {"function": "function_name"},
}
_DATE_FIELD_VOCAB = {"date_precision": "date_precision", "date_basis": "date_basis",
                     "date_confidence": "date_confidence"}
for _p in ("adopted", "effective"):
    for _f, _v in _DATE_FIELD_VOCAB.items():
        FIELD_VOCAB["policy_version"][f"{_p}_{_f}"] = _v
for _e in FIELD_VOCAB:
    FIELD_VOCAB[_e]["review_state"] = "review_state"
    FIELD_VOCAB[_e]["data_origin"] = "data_origin"
    for _col, _vs in VALUE_STATE_PAIRS.get(_e, []):
        FIELD_VOCAB[_e][_vs] = "value_state"

DATE_ISO_RE = {
    "year": re.compile(r"^\d{4}$"),
    "month": re.compile(r"^\d{4}-\d{2}$"),
    "day": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
}


class ContractError(Exception):
    """Accumulated validation errors, raised by validate_dataset()."""


# ---------------------------------------------------------------- loading

def load_contract_version(contract_dir: Path) -> str:
    return (contract_dir / CONTRACT_VERSION_FILE).read_text(encoding="utf-8").strip()


def load_vocabularies(contract_dir: Path) -> dict[str, set[str]]:
    path = contract_dir / VOCABULARIES_FILE
    vocabs: dict[str, set[str]] = {}
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            vocabs.setdefault(r["vocabulary"], set()).add(r["value"])
    return vocabs


def load_schemas(contract_dir: Path) -> dict[str, dict]:
    schemas = {}
    sdir = contract_dir / SCHEMA_DIR
    for entity in ENTITY_FILES:
        p = sdir / f"{entity}.schema.json"
        schemas[entity] = json.loads(p.read_text(encoding="utf-8"))
    return schemas


def load_allowlist(contract_dir: Path) -> dict[str, set[str]]:
    """entity -> set of column names allowed in the public export."""
    path = contract_dir / ALLOWLIST_FILE
    allowed: dict[str, set[str]] = {e: set() for e in ENTITY_FILES}
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            allowed[r["entity"]].add(r["field"])
    return allowed


def read_table(path: Path, schema: dict) -> tuple[list[dict], list[str]]:
    """Read one entity CSV, enforcing the canonical column order."""
    errors: list[str] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return [], [f"{path.name}: file is empty"]
        expected = schema["x-column-order"]
        if header != expected:
            errors.append(
                f"{path.name}: header mismatch\n  expected: {','.join(expected)}\n"
                f"  found:    {','.join(header)}")
            return [], errors
        rows = []
        for i, raw in enumerate(reader, start=2):
            if len(raw) != len(expected):
                errors.append(f"{path.name} row {i}: {len(raw)} cells, expected {len(expected)}")
                continue
            rows.append(dict(zip(expected, raw)))
    return rows, errors


def load_dataset(data_dir: Path, schemas: dict) -> tuple[dict[str, list[dict]], list[str]]:
    data: dict[str, list[dict]] = {}
    errors: list[str] = []
    for entity, fname in ENTITY_FILES.items():
        p = data_dir / fname
        if not p.exists():
            errors.append(f"{fname}: missing")
            data[entity] = []
            continue
        rows, errs = read_table(p, schemas[entity])
        data[entity] = rows
        errors.extend(errs)
    return data, errors


# ------------------------------------------------------------- validation

def _check_required(row: dict, schema: dict, where: str, errors: list) -> None:
    for col in schema["required"]:
        if not row.get(col, "").strip():
            errors.append(f"{where}: required column '{col}' is empty")


def _check_vocab(row: dict, entity: str, where: str, vocabs: dict, errors: list) -> None:
    for col, vocab_name in FIELD_VOCAB[entity].items():
        val = row.get(col, "")
        if val == "":
            continue
        allowed = vocabs.get(vocab_name)
        if allowed is None:
            errors.append(f"{where}: unknown vocabulary '{vocab_name}' (config error)")
        elif val not in allowed:
            errors.append(f"{where}: '{col}' value '{val}' not in vocabulary '{vocab_name}'")


def _check_pattern(row: dict, schema: dict, where: str, errors: list) -> None:
    props = schema["properties"]
    for col, spec in props.items():
        val = row.get(col, "")
        if val == "":
            continue
        pat = spec.get("pattern")
        if pat and not re.fullmatch(pat, val):
            errors.append(f"{where}: '{col}' value '{val}' does not match pattern {pat}")
        if spec.get("type") == "boolean" and val not in ("true", "false"):
            errors.append(f"{where}: '{col}' must be 'true' or 'false', found '{val}'")


def _check_value_state_pairs(row: dict, entity: str, where: str, errors: list) -> None:
    """value present => measured; value empty => unknown/not_applicable/reviewed_absent."""
    for vcol, scol in VALUE_STATE_PAIRS.get(entity, []):
        val, state = row.get(vcol, ""), row.get(scol, "")
        if val != "" and state != "measured":
            errors.append(
                f"{where}: '{vcol}' has a value but '{scol}' is "
                f"'{state or 'empty'}' (a present value must be 'measured')")
        if val == "" and state == "measured":
            errors.append(f"{where}: '{scol}' is 'measured' but '{vcol}' is empty")


def _check_date_block(row: dict, prefix: str, where: str, errors: list) -> None:
    iso = row.get(f"{prefix}_date_iso", "")
    prec = row.get(f"{prefix}_date_precision", "")
    basis = row.get(f"{prefix}_date_basis", "")
    conf = row.get(f"{prefix}_date_confidence", "")
    if iso == "":
        if prec != "":
            errors.append(f"{where}: {prefix}_date_precision set but {prefix}_date_iso is empty")
        if basis not in ("", "unknown"):
            errors.append(f"{where}: {prefix}_date_basis '{basis}' set but no date is known")
    else:
        if prec == "":
            errors.append(f"{where}: {prefix}_date_iso present but {prefix}_date_precision empty")
        elif not DATE_ISO_RE[prec].fullmatch(iso):
            errors.append(
                f"{where}: {prefix}_date_iso '{iso}' does not match precision '{prec}' "
                f"(a partial date must never invent a day)")
        if basis == "":
            errors.append(f"{where}: {prefix}_date_iso present but {prefix}_date_basis empty")
        if conf == "":
            errors.append(f"{where}: {prefix}_date_iso present but {prefix}_date_confidence empty")


def _check_review(row: dict, where: str, errors: list) -> None:
    state = row.get("review_state", "")
    visible = row.get("public_visible", "")
    approved_by = row.get("approved_by", "")
    approved_date = row.get("approved_date", "")
    withhold = row.get("withhold_reason", "")
    if visible == "true" and state != "approved_public":
        errors.append(f"{where}: public_visible=true but review_state is '{state}'")
    if visible != "true" and state == "approved_public":
        errors.append(f"{where}: review_state=approved_public but public_visible is not 'true'")
    if state == "approved_public":
        if not approved_by or not approved_date:
            errors.append(f"{where}: approved_public requires approved_by and approved_date")
        if withhold:
            errors.append(f"{where}: approved_public record must not carry withhold_reason")
    else:
        if approved_by or approved_date:
            errors.append(f"{where}: approved_by/approved_date set but review_state is '{state}'")


def _derived_expected(row: dict) -> tuple[str | None, str | None, str | None, str | None]:
    """Per-family derived values expected from the scores, following the corpus
    data dictionary: family means are computed when that family's dimensions are
    measured; composite_0_30 only when all ten are measured. None = must be empty."""
    vals: dict[str, int | None] = {}
    for d in SCORE_DIMENSIONS:
        v = row.get(f"score_{d}", "")
        if v == "" or row.get(f"score_{d}_value_state", "") != "measured":
            vals[d] = None
        else:
            vals[d] = int(v)

    def mean(dims: list[str]) -> str | None:
        if any(vals[d] is None for d in dims):
            return None
        return f"{sum(vals[d] for d in dims) / len(dims):.2f}"

    composite = None
    if all(vals[d] is not None for d in SCORE_DIMENSIONS):
        composite = str(sum(vals[d] for d in SCORE_DIMENSIONS))
    return (mean(["ms_mandate_strength", "rl_rights_licensing", "comp_compliance"]),
            mean(["inf_infrastructure", "fund_funding", "repo_repository", "eval_evaluation"]),
            mean(["mon_monitoring", "gov_governance", "osb_os_breadth"]),
            composite)


def _check_derived(row: dict, where: str, errors: list) -> None:
    expected = _derived_expected(row)
    got = (row.get("derived_family_normative_force", ""), row.get("derived_family_apparatus", ""),
           row.get("derived_family_gov_scope", ""), row.get("derived_composite_0_30", ""))
    for name, exp, act in zip(("derived_family_normative_force", "derived_family_apparatus",
                               "derived_family_gov_scope", "derived_composite_0_30"),
                              expected, got):
        if exp is None and act != "":
            errors.append(f"{where}: '{name}' is set but its input scores are not all measured")
        elif exp is not None and act != exp:
            errors.append(f"{where}: '{name}' is '{act}' but the scores compute to '{exp}'")


def validate_dataset(data: dict[str, list[dict]], contract_dir: Path,
                     label: str = "dataset") -> list[str]:
    """Full validation: schema, vocabularies, semantics, integrity. Returns errors."""
    vocabs = load_vocabularies(contract_dir)
    schemas = load_schemas(contract_dir)
    errors: list[str] = []

    for entity, rows in data.items():
        schema = schemas[entity]
        idcol = schema["x-column-order"][0]
        # Entities with composite keys: uniqueness is over the composite key.
        if entity == "text":
            key_cols = ["entity_id", "field", "lang"]
        elif entity == "version_function":
            key_cols = ["version_id", "function"]
        else:
            key_cols = [idcol]
        seen: dict[str, int] = {}
        for i, row in enumerate(rows, start=2):
            where = f"[{label}] {ENTITY_FILES[entity]} row {i}"
            _check_required(row, schema, where, errors)
            _check_vocab(row, entity, where, vocabs, errors)
            _check_pattern(row, schema, where, errors)
            _check_value_state_pairs(row, entity, where, errors)
            _check_review(row, where, errors)
            if entity == "policy_version":
                _check_date_block(row, "adopted", where, errors)
                _check_date_block(row, "effective", where, errors)
                _check_derived(row, where, errors)
            key = "|".join(row.get(c, "") for c in key_cols)
            if any(row.get(c, "") for c in key_cols):
                if key in seen:
                    errors.append(f"{where}: duplicate {'+'.join(key_cols)} key "
                                  f"'{key}' (first seen at row {seen[key]})")
                seen[key] = i

    # Referential integrity -------------------------------------------------
    def ids(entity: str) -> set[str]:
        idcol = schemas[entity]["x-column-order"][0]
        return {r.get(idcol, "") for r in data[entity]}

    def fk(row: dict, col: str, target: set[str], where: str) -> None:
        v = row.get(col, "")
        if v and v not in target:
            errors.append(f"{where}: '{col}' references unknown id '{v}'")

    for i, r in enumerate(data["organization"], start=2):
        fk(r, "country_id", ids("country"), f"organizations.csv row {i}")
    for i, r in enumerate(data["policy_family"], start=2):
        fk(r, "issuer_org_id", ids("organization"), f"policy_families.csv row {i}")
    for i, r in enumerate(data["policy_version"], start=2):
        fk(r, "family_id", ids("policy_family"), f"policy_versions.csv row {i}")
    for i, r in enumerate(data["manifestation"], start=2):
        fk(r, "version_id", ids("policy_version"), f"manifestations.csv row {i}")
    for i, r in enumerate(data["provision"], start=2):
        w = f"provisions.csv row {i}"
        fk(r, "version_id", ids("policy_version"), w)
        fk(r, "manifestation_id", ids("manifestation"), w)
    for i, r in enumerate(data["version_relationship"], start=2):
        w = f"version_relationships.csv row {i}"
        fk(r, "from_version_id", ids("policy_version"), w)
        fk(r, "to_version_id", ids("policy_version"), w)
    for i, r in enumerate(data["version_function"], start=2):
        fk(r, "version_id", ids("policy_version"), f"version_functions.csv row {i}")
        try:
            json.loads(r.get("payload", ""))
        except json.JSONDecodeError as e:
            errors.append(f"version_functions.csv row {i}: payload is not valid JSON ({e})")

    all_ids = set().union(*(ids(e) for e in ENTITY_FILES if e != "text"))
    for i, r in enumerate(data["text"], start=2):
        v = r.get("entity_id", "")
        if v and v not in all_ids:
            errors.append(f"texts.csv row {i}: entity_id references unknown id '{v}'")

    # Relationship acyclicity (all edge types) ------------------------------
    edges = {}
    for r in data["version_relationship"]:
        a, b = r.get("from_version_id", ""), r.get("to_version_id", "")
        if a and b:
            edges.setdefault(a, set()).add(b)
    color: dict[str, int] = {}

    def visit(node: str, stack: list[str]) -> None:
        color[node] = 1
        for nxt in sorted(edges.get(node, ())):
            if color.get(nxt) == 1:
                errors.append(
                    f"version_relationships.csv: cycle detected: "
                    f"{' -> '.join(stack + [node, nxt])}")
            elif color.get(nxt, 0) == 0:
                visit(nxt, stack + [node])
        color[node] = 2

    for node in sorted(edges):
        if color.get(node, 0) == 0:
            visit(node, [])

    return errors


# ------------------------------------------------------------ interchange

def dataset_to_json(data: dict[str, list[dict]], schemas: dict) -> str:
    """JSON view of a dataset.

    Entities with a single primary key are serialized as
    ``{id: {col: value}}``. Entities with a composite key (text,
    version_function) are serialized as a list of full row objects,
    because their ID column alone does not identify a row (for example,
    one entity can carry the same field in several languages).
    """
    out = {}
    for entity, rows in data.items():
        schema = schemas[entity]
        idcol = schema["x-column-order"][0]
        if entity in ("text", "version_function"):
            out[entity] = [{**row} for row in rows]
            continue
        table = {}
        for row in rows:
            table[row[idcol]] = {k: v for k, v in row.items() if k != idcol}
        out[entity] = table
    return json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True)


def dataset_from_json(text: str, schemas: dict) -> dict[str, list[dict]]:
    """Inverse of dataset_to_json: reconstruct tables in canonical column
    order. Accepts both shapes (by-id object for primary-key entities,
    row list for composite-key entities)."""
    obj = json.loads(text)
    data = {}
    for entity, payload in obj.items():
        cols = schemas[entity]["x-column-order"]
        idcol = cols[0]
        rows = []
        if isinstance(payload, list):  # composite-key entity
            for src in payload:
                row = {c: src.get(c, "") for c in cols}
                rows.append(row)
        else:  # primary-key entity
            for rid in payload:
                row = {c: payload[rid].get(c, "") for c in cols}
                row[idcol] = rid
                rows.append(row)
        data[entity] = rows
    return data


def write_table(path: Path, entity: str, rows: list[dict], schemas: dict,
                cols: list[str] | None = None) -> None:
    """Write rows in canonical column order. `cols` restricts the output to
    a subset (used by the public exporter to enforce its allowlist); the
    subset must stay in canonical schema order."""
    all_cols = schemas[entity]["x-column-order"]
    if cols is None:
        cols = all_cols
    else:
        unknown = [c for c in cols if c not in all_cols]
        if unknown:
            raise ContractError(
                f"write_table({entity}): unknown columns {unknown}")
        cols = [c for c in all_cols if c in set(cols)]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()
