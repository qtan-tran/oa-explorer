#!/usr/bin/env python3
"""export_ledger.py — validate a ledger-shaped dataset against the contract.

Usage:
    python3 pipeline/export_ledger.py --input synthetic --contract contract
    python3 pipeline/export_ledger.py --input ledger --contract contract --report report.txt

Exit code 0 = valid; 1 = validation errors; 2 = usage/IO error.
Works offline. No data is modified; this is a read-only check.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_lib as cl  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", required=True, help="dataset directory "
                    "(synthetic/ for the demo corpus, ledger/ for the local research ledger)")
    ap.add_argument("--contract", default="contract", help="contract directory (default: contract)")
    ap.add_argument("--report", help="optional path for a human-readable report file")
    args = ap.parse_args()

    in_dir = Path(args.input)
    contract_dir = Path(args.contract)
    if not in_dir.is_dir():
        print(f"ERROR: input directory not found: {in_dir}", file=sys.stderr)
        return 2
    if not contract_dir.is_dir():
        print(f"ERROR: contract directory not found: {contract_dir}", file=sys.stderr)
        return 2

    schemas = cl.load_schemas(contract_dir)
    data, load_errors = cl.load_dataset(in_dir, schemas)
    errors = list(load_errors)
    errors.extend(cl.validate_dataset(data, contract_dir, label=str(in_dir)))

    version = cl.load_contract_version(contract_dir)
    lines = [f"Contract validation report — contract v{version}",
             f"Input: {in_dir}", ""]
    for entity, fname in cl.ENTITY_FILES.items():
        lines.append(f"  {fname:<28} {len(data[entity]):>4} rows")
    lines.append("")
    if errors:
        lines.append(f"INVALID — {len(errors)} error(s):")
        lines.extend(f"  - {e}" for e in errors)
    else:
        lines.append("VALID — no errors.")
    report = "\n".join(lines) + "\n"
    print(report, end="")
    if args.report:
        Path(args.report).write_text(report, encoding="utf-8")
        print(f"Report written to {args.report}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
