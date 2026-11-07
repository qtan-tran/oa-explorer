#!/usr/bin/env python3
"""check_links.py — link inventory and (opt-in) dead-link report for an export.

Offline by default: collects every live and archived URL in an export with the
version it belongs to, and writes a CSV inventory. With --check it performs
network requests (HEAD, GET fallback) and records the result; use that only
as a deliberate, human-reviewed quarterly maintenance step (plan test 12),
never as part of the build.

Usage:
    python3 pipeline/check_links.py --export exports/public --report links.csv
    python3 pipeline/check_links.py --export exports/public --report links.csv --check
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_lib as cl  # noqa: E402


def collect(export_dir: Path) -> list[dict]:
    # The export contains only the allowlisted columns (a subset of the
    # full schema), so read it tolerantly with the stdlib CSV reader
    # instead of the strict schema reader.
    with open(export_dir / "manifestations.csv", newline="",
              encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    inv = []
    for m in rows:
        for kind in ("live_url", "archived_url"):
            url = m.get(kind, "")
            if url:
                inv.append({"url": url, "kind": kind,
                            "version_id": m.get("version_id", ""),
                            "manifestation_id": m.get("manifestation_id", "")})
    inv.sort(key=lambda r: (r["version_id"], r["kind"], r["url"]))
    return inv


def check(urls: list[dict]) -> None:
    import urllib.request
    for r in urls:
        status = "unknown"
        try:
            req = urllib.request.Request(r["url"], method="HEAD",
                                         headers={"User-Agent": "oa-explorer-linkcheck/0.2"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                status = str(resp.status)
        except Exception as e:  # noqa: BLE001 — report, don't crash
            try:
                req = urllib.request.Request(r["url"], method="GET",
                                             headers={"User-Agent": "oa-explorer-linkcheck/0.2"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    status = str(resp.status)
            except Exception as e2:  # noqa: BLE001
                status = f"ERROR {type(e2).__name__}: {e2}"[:200]
        r["http_result"] = status
        print(f"  {status:<10} {r['url']}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Link inventory / dead-link report for an export.")
    ap.add_argument("--export", required=True, help="export directory (e.g. exports/public)")
    ap.add_argument("--report", required=True, help="output CSV path for the report")
    ap.add_argument("--check", action="store_true",
                    help="perform network requests (offline inventory otherwise)")
    args = ap.parse_args()

    export_dir = Path(args.export)
    if not (export_dir / "manifestations.csv").exists():
        print(f"ERROR: {export_dir / 'manifestations.csv'} not found", file=sys.stderr)
        return 2

    inv = collect(export_dir)
    if args.check:
        print(f"Checking {len(inv)} URL(s) over the network...")
        check(inv)
    for r in inv:
        r.setdefault("http_result", "not_checked")

    with open(args.report, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["url", "kind", "version_id",
                                          "manifestation_id", "http_result"],
                           lineterminator="\n")
        w.writeheader()
        w.writerows(inv)
    print(f"{len(inv)} URL(s) written to {args.report}"
          + ("" if args.check else " (offline inventory; run with --check for HTTP results)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
