"""Shared helpers for the M1 test suite.

Runs the real pipeline CLIs (validate → export → build) once per test run
into a process-wide temporary directory, so tests exercise the same
commands a human would run, not just internal functions.
"""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SYNTHETIC = REPO / "synthetic"
CONTRACT = REPO / "contract"
CANARY = "SYNTHETIC-CANARY-PRIVATE-MARKER-9F2"

# Approved, publicly exportable version IDs in the synthetic corpus.
APPROVED_VERSIONS = ["V-XA-0001", "V-XA-0002", "V-XA-0003",
                     "V-XB-0001", "V-XB-0002"]
WITHHELD_VERSION = "V-XA-0004"  # draft, not approved for publication
WITHHELD_ORG = "O-XA-0003"     # unreviewed organization
UNRECOVERED_MANIFESTATION = "M-XB-0001"
NOT_PERMITTED_PROVISION = "P-XB-0002"


def run_cli(args: list[str]) -> subprocess.CompletedProcess:
    """Run a repo CLI with the same interpreter, from the repo root."""
    return subprocess.run([sys.executable, *args], cwd=REPO,
                          capture_output=True, text=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def read_csv_by_id(path: Path, key: str) -> dict[str, dict[str, str]]:
    return {r[key]: r for r in read_csv(path)}


def tree_hashes(root: Path) -> dict[str, str]:
    """Relative path -> sha256 for every file under root (deterministic)."""
    import hashlib
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.sha256(
                p.read_bytes()).hexdigest()
    return out


def scan_tree_for(root: Path, needle: str) -> list[str]:
    """Relative paths of files under root whose bytes contain needle."""
    hits = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and needle.encode() in p.read_bytes():
            hits.append(str(p.relative_to(root)))
    return hits


class _Fixture:
    """One validate→export→build run, shared by all tests in the process."""

    def __init__(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="oa-explorer-test-"))
        self.export_dir = self.tmp / "exports" / "public"
        self.site_dir = self.tmp / "_site"
        self.validate = run_cli([
            "pipeline/export_ledger.py", "--input", str(SYNTHETIC),
            "--contract", str(CONTRACT)])
        if self.validate.returncode != 0:
            raise RuntimeError("synthetic corpus failed validation:\n"
                               + self.validate.stdout + self.validate.stderr)
        self.export = run_cli([
            "pipeline/build_public.py", "--input", str(SYNTHETIC),
            "--contract", str(CONTRACT),
            "--output", str(self.export_dir)])
        if self.export.returncode != 0:
            raise RuntimeError("export failed:\n"
                               + self.export.stdout + self.export.stderr)
        self.build = run_cli([
            "site/build.py", "--export", str(self.export_dir),
            "--output", str(self.site_dir)])
        if self.build.returncode != 0:
            raise RuntimeError("site build failed:\n"
                               + self.build.stdout + self.build.stderr)

    def cleanup(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)


_FIXTURE: _Fixture | None = None


def fixture() -> _Fixture:
    global _FIXTURE
    if _FIXTURE is None:
        _FIXTURE = _Fixture()
    return _FIXTURE


def site_page(name: str) -> str:
    return (fixture().site_dir / name).read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# Exchange-contract v0.2 fixture (Session 3 vertical slice)
# --------------------------------------------------------------------------

EXCHANGE_INPUT = SYNTHETIC / "exchange_v02.json"
EXCHANGE_SCHEMA = CONTRACT / "exchange" / "roara_contract_v0.2.schema.json"

# Versions that pass the public gate in the synthetic exchange fixture.
EXCHANGE_PUBLIC_VERSIONS = [
    "V-MAR-OA-2011", "V-ARC-GRANT-2020", "V-BOR-TRI-2026",
    "V-BOR-BNRA-012-2023", "V-BOR-REPO-2016", "V-ARC-ANN-2020",
]
# Versions withheld from public views (review gate not passed).
EXCHANGE_HIDDEN_VERSIONS = [
    "V-BOR-TRI-2015",      # attested but unrecovered, unreviewed
    "V-BNRA-018-2022",    # repealed predecessor, unreviewed
    "V-BOR-NOS-2022",     # provisionally reviewed only
    "V-ARC-APC-2021",     # unreviewed
]
# Manifestations withheld even for some public versions (rights gate).
EXCHANGE_HIDDEN_MANIFESTATIONS = ["M-BOR-NOS-RES", "M-BOR-NOS-ANNEX",
                                   "M-ARC-APC-2021-PDF",
                                   "M-BOR-TRI-2015-LEAD",
                                   "M-BNRA-018-2022-LEAD"]
EXCHANGE_DOWNLOADABLE = "M-BOR-BNRA-2023-PDF"  # only redistribution-approved
EXCHANGE_INTERNAL_EXCERPT_PROVISION = "P-MAR-2011-2"


class _ExchangeFixture:
    """One validate→gate→build run of the exchange CLI, shared per process."""

    def __init__(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="oa-exchange-test-"))
        self.site_dir = self.tmp / "_exchange"
        self.build = run_cli([
            "site/build_exchange.py", "--input", str(EXCHANGE_INPUT),
            "--schema", str(EXCHANGE_SCHEMA),
            "--output", str(self.site_dir)])
        if self.build.returncode != 0:
            raise RuntimeError("exchange build failed:\n"
                               + self.build.stdout + self.build.stderr)
        self.index_html = (self.site_dir / "index.html").read_text(
            encoding="utf-8")
        self.views = json.loads(
            (self.site_dir / "public_views.json").read_text(encoding="utf-8"))

    def build_variant(self, *extra_args: str) -> tuple[subprocess
                                                      .CompletedProcess, Path]:
        """Build a copy with extra CLI flags into a fresh subdir."""
        out = self.tmp / ("variant-" + "_".join(
            a.lstrip("-").replace("-", "_") for a in extra_args or "def"))
        cp = run_cli([
            "site/build_exchange.py", "--input", str(EXCHANGE_INPUT),
            "--schema", str(EXCHANGE_SCHEMA), "--output", str(out),
            *extra_args])
        return cp, out

    def cleanup(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)


_EXCHANGE: _ExchangeFixture | None = None


def exchange_fixture() -> _ExchangeFixture:
    global _EXCHANGE
    if _EXCHANGE is None:
        _EXCHANGE = _ExchangeFixture()
    return _EXCHANGE


def load_exchange_doc() -> dict:
    """Deep copy of the synthetic exchange document for mutation tests."""
    return json.loads(EXCHANGE_INPUT.read_text(encoding="utf-8"))


def load_exchange_schema() -> dict:
    return json.loads(EXCHANGE_SCHEMA.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Exchange-contract v0.3 fixture (Session 4: six design decisions)
# --------------------------------------------------------------------------

EXCHANGE_V03_INPUT = SYNTHETIC / "exchange_v03.json"
EXCHANGE_V03_SCHEMA = CONTRACT / "exchange" / "roara_contract_v0.3.schema.json"


def load_exchange_v03_doc() -> dict:
    """Deep copy of the synthetic v0.3 exchange document for mutation tests."""
    return json.loads(EXCHANGE_V03_INPUT.read_text(encoding="utf-8"))


def load_exchange_v03_schema() -> dict:
    return json.loads(EXCHANGE_V03_SCHEMA.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Exchange-contract v0.3.1 fixture (Session 5: published/promulgated events,
# archive-link gates, unknown-start cohorts, UPTC unrecovered lead)
# --------------------------------------------------------------------------

EXCHANGE_V031_INPUT = SYNTHETIC / "exchange_v031.json"
EXCHANGE_V031_SCHEMA = CONTRACT / "exchange" / "roara_contract_v0.3.1.schema.json"


def load_exchange_v031_doc() -> dict:
    return json.loads(EXCHANGE_V031_INPUT.read_text(encoding="utf-8"))


def load_exchange_v031_schema() -> dict:
    return json.loads(EXCHANGE_V031_SCHEMA.read_text(encoding="utf-8"))
