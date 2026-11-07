#!/usr/bin/env python3
"""site/build_exchange.py — render the gated exchange reader site.

Reads a v0.2 exchange document (e.g. the SYNTHETIC demonstration fixture),
validates it against the draft schema plus cross-reference, duplicate-hash
and date-semantics rules, builds rights/review-gated public views, and
writes a fully static reader site:

- index.html  : one section per function stratum (no cross-stratum
                aggregation, no prevalence, no ranking, no scores),
- public_views.json : the gated reader model that produced the page.

Display of document links, downloads and excerpts is independently
configurable (--links/--downloads/--excerpts). Withheld records are
counted, never listed. Technical collection columns (source hashes,
reviewer identity, internal evidence pointers) are not rendered.

Deterministic: no timestamps, stable ordering, byte-identical rebuilds.
Standard library only (ADR 0002).

Usage:
    python3 site/build_exchange.py \
        --input synthetic/exchange_v02.json \
        --schema contract/exchange/roara_contract_v0.2.schema.json \
        --output _exchange
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import sys
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent
REPO_DIR = SITE_DIR.parent
sys.path.insert(0, str(REPO_DIR / "pipeline"))

import exchange_lib as xl  # noqa: E402

STRATUM_ORDER = [
    "institutional_oa_os",
    "funder_grant_term",
    "national_os_strategy",
    "national_assessment_subsidy",
    "repository_operation",
    "apc_funding_criteria",
    "research_data_governance",
    "announcement",
    "other",
    "unreviewed",
]

RIGHTS_LABELS = {
    "public_redistribution_approved": "redistribution approved",
    "link_only_approved": "link-only",
}

ROLE_LABELS = {
    "controlling_original": "Controlling original",
    "issuer_html_capture": "Issuer page capture",
    "mirror": "Archive mirror",
    "translation": "Translation",
    "alternate_manifestation": "Alternate manifestation",
    "ancillary": "Ancillary document",
    "unrecovered_lead": "Unrecovered lead",
}

REL_VERBS = {
    "explicit_replacement": "explicitly replaces",
    "amendment": "amends",
    "prospective_cohort_change": "changes its cohort coverage "
                                 "prospectively relative to",
    "issuer_claimed_renewal": "is claimed by its issuer to renew",
    "possible_relation": "may relate to",
    "other": "relates to",
}


def esc(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def unknown_span() -> str:
    return '<span class="unknown">Unknown / not established</span>'


def claim_value_html(c: dict) -> str:
    if c["value"] is None:
        return unknown_span() if c["type"] == "effective" \
            else '<span class="unknown">not stated</span>'
    return f"{esc(c['value'])} <small>({esc(c['precision'])} precision, " \
           f"status: {esc(c['status'])})</small>"


def dates_html(record: dict) -> str:
    if not record["dates"]:
        return ""
    rows = []
    for c in record["dates"]:
        note = ""
        if c["note"]:
            note = f' <small class="note">{esc(c["note"])}</small>'
        anchor = ""
        if c["physical_anchor"]:
            anchor = f' <small class="anchor">anchor: ' \
                     f'{esc(c["physical_anchor"])}</small>'
        rows.append(
            f"<dt>{esc(c['label'])}</dt>"
            f"<dd>{claim_value_html(c)}{note}{anchor}</dd>"
        )
    return "<h4>Key dates</h4><dl class=\"claims\">" + \
        "".join(rows) + "</dl>"


def effective_html(record: dict) -> str:
    eff = record["effective"]
    if eff["value"] is None:
        val = unknown_span()
    else:
        val = esc(eff["display"])
    basis = ""
    if eff["basis"]:
        basis = f' <small class="note">basis: {esc(eff["basis"])}</small>'
    note = ""
    if eff["note"]:
        note = f' <small class="note">{esc(eff["note"])}</small>'
    return f'<p class="effective"><strong>General effective date:</strong> ' \
           f'{val}{basis}{note}</p>'


def cohorts_html(record: dict) -> str:
    if not record["cohorts"]:
        return ""
    items = []
    for co in record["cohorts"]:
        start = esc(co["start"] or "unknown")
        if co["bounded"]:
            span = f"{start} through {esc(co['end'])} (bounded cohort)"
        else:
            span = f"{start} onwards (open-ended cohort, no end stated)"
        exc = ""
        if co["exceptions"]:
            exc = f' <small class="note">exceptions: ' \
                  f'{esc(co["exceptions"])}</small>'
        items.append(
            f"<dt>{esc(co['id'])}</dt>"
            f"<dd>Applies to {esc(co['applies_to'])}.<br>"
            f"Coverage: {span}.{exc}</dd>"
        )
    return "<h4>Covered cohorts</h4><dl class=\"cohorts\">" + \
        "".join(items) + "</dl>"


def clause_grid(p: dict) -> str:
    pairs = [
        ("Actor", p["actor"]),
        ("Action", p["action"]),
        ("Object", p["object"]),
        ("Scope", p["scope"]),
        ("Modality", p["modality"]),
        ("Condition", p["condition"]),
        ("Exception", p["exception"]),
    ]
    rows = []
    for label, val in pairs:
        if val is None:
            continue
        rows.append(f"<dt>{label}</dt><dd>{esc(val)}</dd>")
    return '<dl class="clause">' + "".join(rows) + "</dl>"


def provisions_html(record: dict) -> str:
    if not record["provisions"]:
        return ""
    out = ["<h4>Provisions</h4>"]
    for p in record["provisions"]:
        out.append(f'<div class="provision" data-anchor="{esc(p["anchor"])}">')
        out.append(f'<p class="anchor">Anchor: {esc(p["anchor"])}</p>')
        out.append(clause_grid(p))
        if p["original_excerpt"]:
            out.append(f"<blockquote><p>{esc(p['original_excerpt'])}</p></blockquote>")
            if p["translation_english"]:
                out.append(f'<p class="translation">English translation: '
                           f'{esc(p["translation_english"])}</p>')
        elif p["excerpt_withheld_reason"] == "rights_not_approved":
            out.append('<p class="withheld">Clause excerpt withheld: '
                       'public excerpt rights not approved. The anchor '
                       'and clause analysis above remain visible.</p>')
        else:
            out.append('<p class="withheld">Clause excerpt not shown in '
                       'this build (excerpts disabled by configuration). '
                       'The anchor and clause analysis above remain '
                       'visible.</p>')
        out.append("</div>")
    return "".join(out)


def sources_html(record: dict) -> str:
    if not record["sources"]:
        return ""
    out = ["<h4>Sources</h4>", '<ul class="sources">']
    for s in record["sources"]:
        rights = RIGHTS_LABELS.get(s["rights"], s["rights"])
        bits = [f"{esc(ROLE_LABELS.get(s['kind'], s['kind']))} "
                f"({esc(s['format'])}"
                + (f", {esc(s['language'])}" if s["language"] else "")
                + f", {rights})"]
        if s["url"]:
            bits.append(f'<a href="{esc(s["url"])}" rel="noopener">view '
                         f"document link</a>")
        if s["download_url"]:
            bits.append(f'<a href="{esc(s["download_url"])}" '
                         f'download>download</a>')
        if s["mutable"]:
            bits.append('<span class="marker">mutable issuer page '
                        "(content can change; capture date below)</span>")
        if s["captured"]:
            bits.append(f"captured {esc(s['captured'])}")
        out.append("<li>" + "; ".join(bits) + "</li>")
    out.append("</ul>")
    return "".join(out)


def relationships_html(record: dict) -> str:
    if not record["relationships"]:
        return ""
    out = ["<h4>Related versions</h4>", '<ul class="relationships">']
    for r in record["relationships"]:
        verb = REL_VERBS.get(r["type"], "relates to")
        if r["direction"] == "earlier":
            # the other version is EARLIER than this record
            lead = f"This version {verb} an earlier version"
        else:
            # the other version is LATER than this record
            lead = f"A later version {verb} this one"
        if r["other_version"]:
            other = f'<a href="#{esc(r["other_version"])}">' \
                    f"{esc(r['other_version'])}</a>"
        else:
            other = "a version that is not shown here " \
                    "(withheld pending review and rights gates)"
        anchor = ""
        if r["anchor"]:
            anchor = f' <small class="anchor">anchor: {esc(r["anchor"])}</small>'
        out.append(f"<li>{lead}: {other}{anchor}</li>")
    out.append("</ul>")
    return "".join(out)


def record_html(record: dict) -> str:
    title = esc(record["title_original"])
    if record["title_english"]:
        title += f' <span class="translation">({esc(record["title_english"])})</span>'
    meta = [
        f"Function: {esc(record['function_label'])}",
        f"Issuers: {esc(', '.join(record['issuers']))}",
        f"Language: {esc(record['language'])}",
        f"Authority: {esc(record['authority_status'])}",
        f"Source recovery: {esc(record['source_status'])}",
        f"Review: {esc(record['review_state'])}",
    ]
    body = [
        f'<article class="record" id="{esc(record["id"])}">',
        f"<h3>{title}</h3>",
        f'<p class="meta">{" · ".join(meta)}</p>',
        effective_html(record),
    ]
    if record["scope_note"]:
        body.append(f'<p class="scope">{esc(record["scope_note"])}</p>')
    body.append(dates_html(record))
    body.append(cohorts_html(record))
    body.append(provisions_html(record))
    body.append(sources_html(record))
    body.append(relationships_html(record))
    body.append("</article>")
    return "".join(body)


def index_html(views: dict) -> str:
    records = views["records"]
    by_stratum: dict[str, list[dict]] = {}
    for r in records:
        by_stratum.setdefault(r["function"], []).append(r)
    nav = []
    sections = []
    for fn in STRATUM_ORDER:
        if fn not in by_stratum:
            continue
        slug = "stratum-" + fn.replace("_", "-")
        label = xl.FUNCTION_LABELS[fn]
        nav.append(f'<a href="#{slug}">{esc(label)}</a>')
        arts = [record_html(r) for r in by_stratum[fn]]
        sections.append(
            f'<section id="{slug}" class="stratum" '
            f'aria-labelledby="{slug}-h">'
            f'<h2 id="{slug}-h">{esc(label)} '
            f'<small>({len(by_stratum[fn])} '
            f'{"record" if len(by_stratum[fn]) == 1 else "records"})'
            f"</small></h2>" + "".join(arts) + "</section>"
        )
    nav_html = " · ".join(nav) if nav else "<p>No public records.</p>"
    withheld = esc(views["note"]) if views["note"] else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ROARA exchange reader — synthetic demonstration</title>
<link rel="stylesheet" href="static/style.css">
</head>
<body>
<a class="skip-link" href="#main">Skip to main content</a>
<header role="banner">
<h1>ROARA exchange reader</h1>
<p class="banner">SYNTHETIC DEMONSTRATION DATA — every record on this page
is invented to exercise the draft v0.2 exchange contract. No real policy
document, issuer or excerpt is shown. This is not approved public data.</p>
</header>
<nav role="navigation" aria-label="Function strata">
<p><strong>Function strata:</strong> {nav_html}</p>
</nav>
<main role="main" id="main">
<p class="withheld-note">{withheld}</p>
<p class="scope-note">Records are grouped by function stratum only.
Strata are kept separate on purpose: a national strategy target, a funder
grant term, an institutional policy, a repository rule, APC eligibility
and an announcement are different kinds of instrument and are never
aggregated. This view deliberately computes no country prevalence, no
ranking and no composite score.</p>
{''.join(sections) if sections else '<p>No public records in this release.</p>'}
</main>
<footer role="contentinfo">
<p>Synthetic demonstration build of the ROARA exchange reader (contract
v0.2 draft). Source hashes, reviewer identity and internal evidence
pointers are never shown to readers. Generated by
<code>site/build_exchange.py</code>.</p>
</footer>
</body>
</html>
"""


def build(input_path: Path, schema_path: Path, out_dir: Path,
          cfg: xl.PublicConfig) -> tuple[int, list[str]]:
    doc = xl.load_exchange(input_path)
    schema = xl.load_schema(schema_path)
    errors, warnings = xl.validate_exchange(doc, schema)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        return 1, warnings
    for w in warnings:
        print(f"note: {w}", file=sys.stderr)
    views = xl.build_public_views(doc, cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    static_src = SITE_DIR / "static" / "style.css"
    static_dst = out_dir / "static" / "style.css"
    static_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(static_src, static_dst)
    (out_dir / "index.html").write_text(index_html(views),
                                        encoding="utf-8")
    (out_dir / "public_views.json").write_text(
        json.dumps(views, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    return 0, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", type=Path, required=True,
                    help="exchange document (JSON, v0.2 draft)")
    ap.add_argument("--schema", type=Path, required=True,
                    help="exchange schema (JSON Schema, draft 2020-12)")
    ap.add_argument("--output", type=Path, default=Path("_exchange"),
                    help="output directory (default: _exchange)")
    ap.add_argument("--links", action=argparse.BooleanOptionalAction,
                    default=True,
                    help="show public document links (default: on)")
    ap.add_argument("--downloads", action=argparse.BooleanOptionalAction,
                    default=False,
                    help="show download affordances for redistribution-"
                         "approved documents (default: off)")
    ap.add_argument("--excerpts", action=argparse.BooleanOptionalAction,
                    default=True,
                    help="show public excerpt text (default: on)")
    args = ap.parse_args()
    cfg = xl.PublicConfig(document_links=args.links, downloads=args.downloads,
                          excerpts=args.excerpts)
    rc, _ = build(args.input, args.schema, args.output, cfg)
    if rc == 0:
        print(f"built {args.output}/ from {args.input.name} "
              f"(links={'on' if cfg.document_links else 'off'}, "
              f"downloads={'on' if cfg.downloads else 'off'}, "
              f"excerpts={'on' if cfg.excerpts else 'off'})")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
