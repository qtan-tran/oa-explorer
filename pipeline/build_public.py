#!/usr/bin/env python3
"""build_public.py — produce the public export from a validated dataset.

Rules enforced here (the publication-safety gate, plan tests 5 and 14):
  1. Only rows with review_state=approved_public AND public_visible=true are exported.
  2. Only allowlisted columns (contract/public_allowlist.csv) are exported.
  3. Manifestations with access_status != open_public are NOT exported; the
     version row instead carries derived summary columns (counts + a
     human-readable source status summary).
  4. Provisions whose manifestation is not exported are not exported either
     (summarized as a count), because their anchors point at non-public sources.
  5. Excerpt text is blanked (excerpt_value_state -> not_applicable) whenever
     the manifestation's excerpt_policy is not 'permitted' or
     'quotation_exception'.

The output is deterministic: no timestamps, sorted rows, fixed column order.
Every output file's SHA-256 is recorded in manifest.json.

Usage:
    python3 pipeline/build_public.py --input synthetic --contract contract \
        --output exports/public
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_lib as cl  # noqa: E402

EXPORTER_VERSION = "0.2.0"


def public_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows
            if r.get("review_state") == "approved_public"
            and r.get("public_visible") == "true"]


def project(row: dict, allowed: set[str], entity: str, schemas: dict) -> dict:
    """Keep only allowlisted columns, in canonical schema order."""
    cols = schemas[entity]["x-column-order"]
    return {c: row.get(c, "") for c in cols if c in allowed}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the public export (allowlist + approval gate).")
    ap.add_argument("--input", required=True, help="validated dataset directory (synthetic/ or ledger/)")
    ap.add_argument("--contract", default="contract")
    ap.add_argument("--output", required=True, help="output directory (e.g. exports/public)")
    args = ap.parse_args()

    in_dir, contract_dir, out_dir = Path(args.input), Path(args.contract), Path(args.output)
    for d, what in ((in_dir, "input"), (contract_dir, "contract")):
        if not d.is_dir():
            print(f"ERROR: {what} directory not found: {d}", file=sys.stderr)
            return 2

    schemas = cl.load_schemas(contract_dir)
    data, load_errors = cl.load_dataset(in_dir, schemas)
    errors = list(load_errors)
    errors.extend(cl.validate_dataset(data, contract_dir, label=str(in_dir)))
    if errors:
        print(f"ERROR: dataset does not validate; refusing to export.", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    allowed = cl.load_allowlist(contract_dir)
    contract_version = cl.load_contract_version(contract_dir)

    pub = {e: public_rows(data[e]) for e in cl.ENTITY_FILES}

    # Manifestation-level gating and derived version summaries --------------
    pub_manifestations = [m for m in pub["manifestation"]
                          if m.get("access_status") == "open_public"]
    pub_manifest_ids = {m["manifestation_id"] for m in pub_manifestations}
    pub_provisions = [p for p in pub["provision"]
                      if p.get("manifestation_id") in pub_manifest_ids]

    # Blank excerpts where permission does not allow them.
    m_by_id = {m["manifestation_id"]: m for m in pub_manifestations}
    for p in pub_provisions:
        m = m_by_id.get(p.get("manifestation_id", ""))
        if m is not None and m.get("excerpt_policy", "unknown") not in ("permitted", "quotation_exception"):
            p["excerpt_text"] = ""
            p["excerpt_value_state"] = "not_applicable"

    # Version summaries (contract §7: existence may be summarized as a count).
    versions = {v["version_id"]: v for v in pub["policy_version"]}
    manifests_by_version: dict[str, list[dict]] = {}
    for m in data["manifestation"]:
        manifests_by_version.setdefault(m["version_id"], []).append(m)
    for vid, v in versions.items():
        all_m = manifests_by_version.get(vid, [])
        public_m = [m for m in all_m if m.get("access_status") == "open_public"]
        v["derived_manifestation_count"] = str(len(all_m))
        v["derived_manifestation_public_count"] = str(len(public_m))
        v["derived_provision_public_count"] = str(
            sum(1 for p in pub_provisions if p.get("version_id") == vid))
        if len(all_m) == 0:
            summary = "No source manifestation recorded."
        elif not public_m:
            kinds = ", ".join(sorted({m.get("access_status", "unknown") for m in all_m}))
            summary = (f"{len(all_m)} known manifestation(s), none publicly accessible "
                       f"({kinds}); sources withheld from the export; no excerpts available.")
        else:
            summary = (f"{len(public_m)} publicly accessible source(s) linked; "
                       f"{len(all_m) - len(public_m)} further manifestation(s) withheld "
                       f"from the export.")
        v["derived_source_status_summary"] = summary

    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    hashes = {}
    for entity, rows in pub.items():
        if entity == "manifestation":
            rows = pub_manifestations
        elif entity == "provision":
            rows = pub_provisions
        rows_out = [project(r, allowed[entity], entity, schemas) for r in rows]
        rows_out.sort(key=lambda r: list(r.values())[0])
        path = out_dir / cl.ENTITY_FILES[entity]
        export_cols = [c for c in schemas[entity]["x-column-order"]
                       if c in allowed[entity]]
        cl.write_table(path, entity, rows_out, schemas, cols=export_cols)
        counts[entity] = len(rows_out)
        hashes[path.name] = cl.sha256_file(path)

    any_synthetic = any(r.get("data_origin") == "synthetic"
                        for rows in pub.values() for r in rows)
    manifest = {
        "contract_version": contract_version,
        "exporter_version": EXPORTER_VERSION,
        "input": in_dir.name,
        "contains_synthetic_records": any_synthetic,
        "record_counts": counts,
        "files": sorted(hashes),
        "sha256": hashes,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")

    print(f"Public export written to {out_dir}")
    for entity in cl.ENTITY_FILES:
        print(f"  {cl.ENTITY_FILES[entity]:<28} {counts[entity]:>4} public rows")
    if any_synthetic:
        print("  NOTE: export contains SYNTHETIC demonstration records.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
