# OA/OS Policy Explorer (ROARA)

A durable, free-to-use explorer for the ROARA corpus of open-access /
open-science policies: filter, search, open versioned policy records with
evidence, original-language excerpts and source anchors, follow relationships
across policy versions, and download cautious, transparent exports.

**Current status: M1 complete (2026-11-08) — local vertical slice on clearly
labelled synthetic data.** Nothing is published or deployed; the public site
goes live only by the owner's explicit authorization (milestone M4).

Key documents:

- [`docs/plans/2026-11-07-explorer-plan.md`](docs/plans/2026-11-07-explorer-plan.md) — master plan: milestones, layout, tests, ten-year maintenance
- [`docs/adr/0001-static-data-driven-explorer.md`](docs/adr/0001-static-data-driven-explorer.md) — architecture decision (static site, GitHub Pages with dated limit checks)
- [`docs/adr/0002-stdlib-only-m1-build.md`](docs/adr/0002-stdlib-only-m1-build.md) — stdlib-only toolchain decision (Jinja2 as documented fallback)
- [`docs/plans/2026-11-07-data-contract-v0.1.md`](docs/plans/2026-11-07-data-contract-v0.1.md) — data contract v0.1 DRAFT, pending corpus-team ratification
- [`docs/plans/2026-11-08-m1-implementation-report.md`](docs/plans/2026-11-08-m1-implementation-report.md) — what M1 built, what runs, honest test status
- [`docs/plans/2026-11-08-continuation-note.md`](docs/plans/2026-11-08-continuation-note.md) — next milestone and the exact expected corpus data handoff
- [`docs/handover.md`](docs/handover.md) — cold-start handover for any future maintainer

The research corpus lives in the separate repository
[`oa-os-policy-collections`](https://github.com/qtan-tran/oa-os-policy-collections)
and remains the research ledger of record. The detailed research ledger,
PDF originals and unpublished notes never live in this repository; they stay
in local, gitignored working copies or institutional storage (plan decision
D4).

Core commitments, inherited from the corpus and enforced by the tests:
purposive corpus, never a census (no prevalence claims, no rankings); unknown
≠ not applicable ≠ reviewed absence ≠ zero; partial dates never invent a day;
source documents are never redistributed; the public site carries only
reviewed, explicitly approved fields.

## Quickstart (M1, zero install)

Requires Python ≥ 3.11 and nothing else (ADR 0002: standard library only;
no third-party packages, no network access needed).

```bash
# 1. Validate the synthetic corpus against the data contract
python3 pipeline/export_ledger.py --input synthetic --contract contract

# 2. Build the reviewed-and-approved public export (allowlist-enforced)
python3 pipeline/build_public.py --input synthetic --contract contract \
    --output exports/public

# 3. Build the static site
python3 site/build.py --export exports/public --output _site

# 4. Preview locally, then open http://localhost:8000
python3 -m http.server -d _site 8000

# 5. Run the test suite (see below for the full count)
python3 -m unittest discover -s tests -t . -v

# 6. Offline inventory of source links (use --check for a network run)
python3 pipeline/check_links.py --export exports/public \
    --report link-report.txt
```

## Quickstart (v0.2 exchange slice, zero install)

Demonstrates the draft exchange contract with the synthetic exchange
fixture only (no real data passes through this pipeline):

```bash
# Build the gated reader site (rights/review gates; links on,
# downloads off, excerpts on by default — flip with --no-links,
# --downloads, --no-excerpts)
python3 site/build_exchange.py \
    --input synthetic/exchange_v02.json \
    --schema contract/exchange/roara_contract_v0.2.schema.json \
    --output _exchange

# Preview locally, then open http://localhost:8000
python3 -m http.server -d _exchange 8000

# Full test suite (151 automated checks incl. the exchange tests 20–23)
python3 -m unittest discover -s tests -t . -v
```

`exports/`, `_site/` and `ledger/` are gitignored build products; everything
needed to rebuild them deterministically is committed (code, contract,
synthetic data). The data contract (v0.1.0) is a DRAFT pending corpus-team
ratification; open questions OQ1–OQ8 are listed in the contract document.

## Licensing

- Code (pipeline, site generator, tests): MIT — see `LICENSE-CODE.md`
- Documentation, plans and UI text: CC BY 4.0 — see `LICENSE-DOCS.md`
- Data: synthetic seed data is released with the repository; real corpus
  exports carry their own licence decision at M2+ (per-record, reviewed).
- Source policy documents are never redistributed by this project.

## Maintainer

Quoc-Tan Tran, Institute for Studies of Science, Bielefeld University,
within the ROARA project.
