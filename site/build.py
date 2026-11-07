#!/usr/bin/env python3
"""site/build.py — render the static explorer site from a public export.

Reads the already-filtered public export (exports/public) — never the ledger —
and writes a fully static site: an index with the version list, one record
page per policy version (deep linkable, works without JavaScript), an about
page, a pre-built search/filter index (index.json) consumed by the one
optional JS file, and a copy of the export CSVs under data/.

Deterministic: no timestamps, stable ordering, byte-identical rebuilds.
Standard library only (ADR 0002).

Usage:
    python3 site/build.py --export exports/public --output _site
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import shutil
import sys
from pathlib import Path
from string import Template

SITE_DIR = Path(__file__).resolve().parent
EXPORT_FILES = {
    "countries": "countries.csv",
    "organizations": "organizations.csv",
    "policy_families": "policy_families.csv",
    "policy_versions": "policy_versions.csv",
    "manifestations": "manifestations.csv",
    "provisions": "provisions.csv",
    "version_relationships": "version_relationships.csv",
    "texts": "texts.csv",
    "version_functions": "version_functions.csv",
}

SCORE_LABELS = {
    "ms_mandate_strength": "Mandate strength",
    "rl_rights_licensing": "Rights and licensing",
    "comp_compliance": "Compliance",
    "inf_infrastructure": "Infrastructure",
    "fund_funding": "Funding",
    "repo_repository": "Repository",
    "eval_evaluation": "Evaluation",
    "mon_monitoring": "Monitoring",
    "gov_governance": "Governance",
    "osb_os_breadth": "Open-science breadth",
}

STATUS_LABELS = {"in_force": "in force", "superseded": "superseded",
                "withdrawn": "withdrawn", "repealed": "repealed",
                "unknown": "status unknown"}

FUNC_LABELS = {
    "national_assessment_subsidy_rules": "national assessment/subsidy rules",
    "funder_grant_terms": "funder grant terms",
    "institutional_oa_os_policy": "institutional OA/OS policy",
    "repository_rules": "repository rules",
    "apc_eligibility": "APC eligibility",
    "implementation_guidance": "implementation guidance",
    "announcement": "announcement",
}


def esc(v: str) -> str:
    return html.escape(v or "", quote=True)


def read_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def by_id(rows: list[dict], key: str) -> dict[str, dict]:
    return {r[key]: r for r in rows}


# ------------------------------------------------------------------ dates

def date_display(iso: str, precision: str) -> str:
    """Show exactly what is known; a partial date never gains a day."""
    if not iso:
        return "unknown"
    return iso  # 2020 / 2023-03 / 2024-06-15 are each honest displays.


def date_line(row: dict, prefix: str, label: str) -> str:
    iso = row.get(f"{prefix}_date_iso", "")
    prec = row.get(f"{prefix}_date_precision", "")
    basis = row.get(f"{prefix}_date_basis", "")
    conf = row.get(f"{prefix}_date_confidence", "")
    verb = row.get(f"{prefix}_date_verbatim", "")
    parts = [f"<strong>{esc(label)}:</strong> {esc(date_display(iso, prec))}"]
    if prec:
        parts.append(f"precision: {esc(prec)}")
    if basis:
        parts.append(f"basis: {esc(basis)}")
    if conf:
        parts.append(f"confidence: {esc(conf)}")
    line = ", ".join(parts)
    if verb:
        line += f' <span class="verbatim">(as stated in the source: “{esc(verb)}”)</span>'
    return f"<li>{line}</li>"


# ------------------------------------------------------------------ texts

def texts_map(text_rows: list[dict]) -> dict[str, dict[str, list[dict]]]:
    """entity_id -> field -> list of {lang, language_status, text}."""
    out: dict[str, dict[str, list[dict]]] = {}
    for t in text_rows:
        out.setdefault(t["entity_id"], {}).setdefault(t["field"], []).append(
            {"lang": t["lang"], "language_status": t["language_status"],
             "text": t["text"]})
    for eid in out:
        for field in out[eid]:
            out[eid][field].sort(key=lambda x: (x["language_status"] != "original", x["lang"]))
    return out


def title_html(texts: dict, eid: str, fallback: str = "") -> str:
    """Original-language title first, glosses after, each with lang attr."""
    entries = texts.get(eid, {}).get("title", [])
    if not entries:
        return esc(fallback)
    out = []
    for t in entries:
        cls = ' class="gloss"' if t["language_status"] != "original" else ""
        out.append(f'<span lang="{esc(t["lang"])}"{cls}>{esc(t["text"])}</span>'
                   + (' <span class="gloss-tag">gloss</span>'
                      if t["language_status"] == "gloss" else ""))
    return "<br>".join(out)


def name_html(texts: dict, eid: str, fallback: str = "") -> str:
    entries = texts.get(eid, {}).get("name", [])
    if not entries:
        return esc(fallback)
    return "<br>".join(f'<span lang="{esc(t["lang"])}">{esc(t["text"])}</span>' for t in entries)


# ------------------------------------------------------------------ chart

def chart_svg(counts: dict[str, int]) -> str:
    """Build-time SVG bar chart of versions per country (role=img, title+desc)."""
    max_n = max(counts.values(), default=0)
    bar_w, gap, top = 64, 40, 20
    width = 80 + len(counts) * (bar_w + gap)
    height = 200
    bars = []
    x = 80
    for cid in sorted(counts):
        n = counts[cid]
        h = int(n / max_n * 120) if max_n else 0
        bars.append(
            f'<rect x="{x}" y="{160 - h}" width="{bar_w}" height="{h}" '
            f'fill="#1a4d80" />'
            f'<text x="{x + bar_w // 2}" y="{155 - h}" text-anchor="middle" '
            f'class="chart-value">{n}</text>'
            f'<text x="{x + bar_w // 2}" y="178" text-anchor="middle" '
            f'class="chart-label">{esc(cid)}</text>')
        x += bar_w + gap
    return (
        '<svg viewBox="0 0 %d %d" width="100%%" height="%d" role="img" '
        'aria-labelledby="chart-title chart-desc" class="chart">'
        '<title id="chart-title">Policy versions per country in this export</title>'
        '<desc id="chart-desc">%s</desc>%s</svg>'
    ) % (width, height, height,
         esc("; ".join(f"{c}: {n} versions" for c, n in sorted(counts.items()))),
         "".join(bars))


# ------------------------------------------------------------------ pages

def scores_table(row: dict) -> str:
    dims = list(SCORE_LABELS)
    measured = sum(1 for d in dims if row.get(f"score_{d}_value_state") == "measured")
    body = []
    for d in dims:
        v, s = row.get(f"score_{d}", ""), row.get(f"score_{d}_value_state", "")
        if s == "measured":
            shown = v + " of 3"
        elif s == "not_applicable":
            shown = "not applicable to this record"
        elif s == "reviewed_absent":
            shown = "reviewed absent"
        else:
            shown = "unknown / not yet reviewed"
        body.append(f"<tr><th scope=\"row\">{esc(SCORE_LABELS[d])}</th>"
                    f"<td>{esc(shown)}</td><td>{esc(s)}</td></tr>")
    derived = []
    for label, col in (("Family: normative force (mean)", "derived_family_normative_force"),
                       ("Family: institutional apparatus (mean)", "derived_family_apparatus"),
                       ("Family: governance and scope (mean)", "derived_family_gov_scope"),
                       ("Composite (sum, descriptive only)", "derived_composite_0_30")):
        v = row.get(col, "")
        derived.append(f"<tr><th scope=\"row\">{esc(label)}</th>"
                        f"<td>{esc(v) if v else 'not computed (incomplete profile)'}</td>"
                        f"<td>{'derived' if v else ''}</td></tr>")
    return (
        "<p>The ten-dimension profile describes what this policy deploys and how forcefully. "
        "It is never aggregated into a ranking or a strength league table.</p>"
        f"<table><caption>Ten-dimension profile of {esc(row['version_id'])} "
        f"({measured} of 10 dimensions measured)</caption>"
        "<thead><tr><th scope=\"col\">Dimension</th><th scope=\"col\">Value</th>"
        "<th scope=\"col\">State</th></tr></thead><tbody>"
        + "".join(body) + "</tbody><tfoot>" + "".join(derived) + "</tfoot></table>"
        "<p class=\"note\">Unknown means not yet reviewed or not determinable; "
        "not applicable means the question does not arise for this record "
        "(for example, a funder does not hire or promote researchers). "
        "Derived values are computed only from fully measured inputs.</p>")


def provisions_html(version: dict, provisions: list[dict],
                    manifest_by_id: dict[str, dict]) -> str:
    if not provisions:
        if version.get("derived_provision_public_count") == "0":
            return ("<p>No provisions are shown for this version: the coded provisions "
                    "are bound to source manifestations that are not publicly accessible, "
                    "so they are withheld from this export together with those sources. "
                    "Their existence is recorded on the version, never their text.</p>")
        return "<p>No provisions coded for this version.</p>"
    out = []
    for p in provisions:
        m = manifest_by_id.get(p.get("manifestation_id", ""), {})
        fields = [
            ("Actor", p.get("actor", "")), ("Action", p.get("action", "")),
            ("Object", p.get("object", "")), ("Scope", p.get("scope", "")),
        ]
        grid = "".join(f"<div><strong>{esc(k)}:</strong> {esc(v)}</div>"
                       for k, v in fields if v)
        cond = p.get("conditions", "")
        cond_state = p.get("conditions_value_state", "")
        cond_html = ""
        if cond:
            cond_html = f"<p><strong>Condition:</strong> {esc(cond)}</p>"
        elif cond_state == "not_applicable":
            cond_html = "<p><strong>Condition:</strong> none (reviewed: unconditional)</p>"
        exc = p.get("exceptions", "")
        exc_state = p.get("exceptions_value_state", "")
        exc_html = ""
        if exc:
            exc_html = f"<p><strong>Exception:</strong> {esc(exc)}</p>"
        elif exc_state == "not_applicable":
            exc_html = "<p><strong>Exception:</strong> none (reviewed)</p>"
        excerpt = p.get("excerpt_text", "")
        ex_state = p.get("excerpt_value_state", "")
        if excerpt:
            excerpt_html = (f'<blockquote lang="{esc(p.get("excerpt_language", ""))}">'
                            f"{esc(excerpt)}</blockquote>")
        elif ex_state == "not_applicable":
            excerpt_html = ("<p class=\"note\">Excerpt withheld: the source's permission "
                            "status does not permit republication of excerpts. "
                            "The anchor below locates the provision in the linked source.</p>")
        else:
            excerpt_html = "<p class=\"note\">No excerpt available (not recovered or not yet reviewed).</p>"
        out.append(
            "<article class=\"provision\">"
            f"<h3><span class=\"badge badge-modality\">{esc(p['modality'])}</span></h3>"
            f"<div class=\"grid\">{grid}</div>"
            + cond_html + exc_html + excerpt_html +
            f"<p><strong>Anchor:</strong> {esc(p.get('anchor', '') or 'not recorded')}"
            + (f' (<a href="{esc(m.get("live_url", ""))}#{esc(p.get("anchor_url_fragment", ""))}"'
               f'>go to passage in source</a>)' if p.get("anchor_url_fragment") and m.get("live_url") else "")
            + f" &nbsp;|&nbsp; <strong>Review extent:</strong> {esc(p['review_extent'])}</p>"
            "</article>")
    return "\n".join(out)


def manifestations_html(version: dict, manifestations: list[dict]) -> str:
    if not manifestations:
        return (f"<p>{esc(version.get('derived_source_status_summary', ''))}</p>"
                "<p class=\"note\">Non-public sources are never linked or attached here; "
                "only their existence and status are summarized, per the export rules.</p>")
    out = ["<ul class=\"manifestations\">"]
    for m in manifestations:
        links = []
        if m.get("live_url"):
            links.append(f'<a href="{esc(m["live_url"])}" rel="noopener">issuer copy</a>')
        if m.get("archived_url"):
            links.append(f'<a href="{esc(m["archived_url"])}" rel="noopener">archival snapshot'
                         + (f' ({esc(m["archive_date"])})' if m.get("archive_date") else "")
                         + '</a>')
        out.append(
            "<li>"
            f"<strong>{esc(m.get('verbatim_title', '') or 'Untitled manifestation')}</strong> "
            f"<span class=\"meta\">({esc(m['form'])}, language "
            f"<span lang=\"{esc(m['language'])}\">{esc(m['language'])}</span>, "
            f"retrieved {esc(m.get('retrieved_date', '') or 'unknown')})</span><br>"
            + (" · ".join(links) if links else "no public link available")
            + f"<br><span class=\"meta\">Rights: {esc(m.get('rights_status', ''))}; "
              f"attribution required: {esc(m.get('attribution_required', ''))}; "
              f"excerpts: {esc(m.get('excerpt_policy', ''))}.</span>"
            "</li>")
    out.append("</ul>")
    return "\n".join(out)


def relationships_html(vid: str, rel_rows: list[dict],
                       version_by_id: dict[str, dict], texts: dict) -> str:
    out = []
    for r in rel_rows:
        if r["from_version_id"] == vid:
            out.append(rel_link(r, "to_version_id", "replaces/sends", texts, "outgoing"))
        elif r["to_version_id"] == vid:
            out.append(rel_link(r, "from_version_id", "is the target of", texts, "incoming"))
    if not out:
        return "<p>No recorded relationships to other policy versions.</p>"
    return "\n".join(out)


def rel_link(r: dict, other: str, _unused: str, texts: dict, direction: str) -> str:
    oid = r[other]
    arrow = f"{esc(r['from_version_id'])} —[{esc(r['type'])}]-> {esc(r['to_version_id'])}"
    return ("<article class=\"relationship\">"
            f"<p>{arrow} <span class=\"meta\">({direction})</span></p>"
            f"<p><a href=\"../record/{esc(oid)}.html\">Open the related version "
            f"({esc(oid)})</a></p>"
            + (f"<p class=\"meta\">Evidence: {esc(r.get('evidence_anchor', ''))}</p>"
               if r.get("evidence_anchor") else "")
            + "</article>")


def record_page(version: dict, family, org, country, texts, provisions,
                manifestations, rel_rows, version_by_id, functions) -> str:
    vid = version["version_id"]
    adopted = date_line(version, "adopted", "Adopted")
    effective = date_line(version, "effective", "Effective")
    title_entries = texts.get(vid, {}).get("title", [])
    h1 = title_entries[0]["text"] if title_entries else vid

    meta_rows = [
        ("Version ID", vid),
        ("Country", f"{country['country_id']} — {name_html(texts, country['country_id'])}"),
        ("Issuer", name_html(texts, org["org_id"], org.get("org_name_raw", ""))),
        ("Issuer type", f"{org['institution_category']} ({org['tier']})"),
        ("Authority level", family["authority_level"]),
        ("Instrument function", FUNC_LABELS.get(family["instrument_function"],
                                                family["instrument_function"])),
        ("Policy area", family["policy_area"]),
        ("Version label", version.get("version_label", "")),
        ("Status", STATUS_LABELS.get(version["status"], version["status"])),
        ("Official languages", version.get("official_languages", "")),
        ("Evidence confidence", version.get("evidence_confidence", "")),
        ("Review state", version.get("review_state", "")),
        ("Approved for publication", version.get("approved_date", "")),
        ("Record origin", version.get("data_origin", "")),
    ]
    meta = "".join(f"<tr><th scope=\"row\">{esc(k)}</th><td>{v}</td></tr>"
                   for k, v in meta_rows)

    special = ""
    if version.get("special_stratum"):
        special = ("<p class=\"warning\"><strong>Comparison warning:</strong> "
                   f"{esc(version['special_stratum'])}</p>")

    funcs_html = ""
    if functions:
        items = []
        for fn in functions:
            try:
                payload = json.dumps(json.loads(fn["payload"]), indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                payload = fn["payload"]
            items.append(f"<h3>{esc(fn['function'])}</h3><pre><code>{esc(payload)}</code></pre>")
        funcs_html = ("<h2>Policy-function details</h2>"
                     "<p>Structured, function-specific data for this version. "
                     "Shapes are documented in the data dictionary.</p>"
                     + "".join(items))

    gloss_titles = "".join(
        f'<p lang="{esc(t["lang"])}">{esc(t["text"])} <span class="gloss-tag">'
        f'{esc(t["language_status"])}</span></p>'
        for t in title_entries[1:])

    return f"""
<nav class="breadcrumb" aria-label="Breadcrumb"><p><a href="../index.html">← All policy versions</a></p></nav>
<p class="badge-line"><span class="badge badge-synthetic">SYNTHETIC</span>
<span class="badge">record origin: {esc(version.get("data_origin", ""))}</span>
<span class="badge">review: {esc(version.get("review_state", ""))}</span></p>
<h1 lang="{esc(title_entries[0]["lang"] if title_entries else "en")}">{esc(h1)}</h1>
{gloss_titles}
{special}
<table class="meta"><caption>Record metadata</caption><tbody>{meta}</tbody></table>
<h2>Dates</h2>
<p class="note">Adoption and effective dates are distinct facts. When only one is known,
the other stays unknown; a partial date never gains an invented day; the source's own
wording is always preserved.</p>
<ul class="dates">
{adopted}
{effective}
</ul>
<h2>Relationships to other policy versions</h2>
{relationships_html(vid, rel_rows, version_by_id, texts)}
<h2>Sources (manifestations)</h2>
{manifestations_html(version, manifestations)}
<h2>Coded provisions and evidence</h2>
{provisions_html(version, provisions, {})}
{funcs_html}
<h2>Ten-dimension profile</h2>
{scores_table(version)}
<p class="note">How to cite this record: OA/OS Policy Explorer (ROARA), record
{esc(vid)}, synthetic demonstration export. See the export manifest for the
contract version and file checksums.</p>
"""


def index_body(orgs: dict, families: dict, texts: dict,
               versions: list[dict], export: dict) -> str:
    counts: dict[str, int] = {}
    for v in versions:
        f = families.get(v["family_id"], {})
        o = orgs.get(f.get("issuer_org_id", ""), {})
        counts[o.get("country_id", "?")] = counts.get(o.get("country_id", "?"), 0) + 1
    total = sum(counts.values())

    chart = chart_svg(counts)
    denom = (f"<p class=\"note\"><strong>Denominator:</strong> n = {total} policy versions in "
             f"this export. Excluded from this chart: 1 draft version not approved for "
             f"publication, and organization-level screening records (shown separately "
             f"below). These counts describe the corpus, not any country's policy sector; "
             f"the corpus is a purposive sample and never a census.</p>")

    # Organization screening table (reviewed absence is data, kept visible).
    org_rows = []
    for oid, o in sorted(orgs.items()):
        hp, hps = o.get("has_policy", ""), o.get("has_policy_value_state", "")
        if hps == "measured" and hp == "N":
            hp_text = "no policy (reviewed absence)"
        elif hps == "measured" and hp == "Y":
            hp_text = "policy (reviewed)"
        elif hps == "unknown":
            hp_text = "unknown / not yet reviewed"
        else:
            hp_text = f"{hp or 'empty'} ({hps})"
        org_rows.append(
            f"<tr><th scope=\"row\">{name_html(texts, oid, o.get('org_name_raw', ''))}</th>"
            f"<td>{esc(o['country_id'])}</td><td>{esc(o['institution_category'])}</td>"
            f"<td>{esc(o['tier'])}</td><td>{esc(hp_text)}</td>"
            f"<td>{esc(o.get('coding_status', ''))}</td></tr>")
    org_table = (
        "<h2>Organizations in the corpus (screening results)</h2>"
        "<p>A source-inventory row is not necessarily a policy version. Organizations "
        "screened without a policy remain in the data: absence is a finding. "
        "These screening results describe the corpus organizations, never national "
        "prevalence.</p>"
        "<table><caption>Screening results of organizations in this export</caption>"
        "<thead><tr><th scope=\"col\">Organization</th><th scope=\"col\">Country</th>"
        "<th scope=\"col\">Type</th><th scope=\"col\">Tier</th>"
        "<th scope=\"col\">Policy screening</th>"
        "<th scope=\"col\">Coding status</th></tr></thead><tbody>"
        + "".join(org_rows) + "</tbody></table>")

    # Version list (the no-JS content; JS filters these rows).
    head = ("<thead><tr>"
            "<th scope=\"col\" id=\"col-title\">Policy version</th>"
            "<th scope=\"col\">Country</th><th scope=\"col\">Issuer</th>"
            "<th scope=\"col\">Issuer type</th><th scope=\"col\">Function</th>"
            "<th scope=\"col\">Area</th><th scope=\"col\">Adopted</th>"
            "<th scope=\"col\">Status</th><th scope=\"col\">Source status</th>"
            "</tr></thead>")
    body_rows = []
    for v in versions:
        vid = v["version_id"]
        f = families.get(v["family_id"], {})
        o = orgs.get(f.get("issuer_org_id", ""), {})
        pub_count = v.get("derived_manifestation_public_count", "0")
        if pub_count and pub_count != "0":
            src = "public source linked"
        else:
            src = "source not publicly accessible"
        body_rows.append(
            f"<tr data-version=\"{esc(vid)}\" data-country=\"{esc(o.get('country_id', ''))}\" "
            f"data-issuer-type=\"{esc(o.get('institution_category', ''))}\" "
            f"data-function=\"{esc(f.get('instrument_function', ''))}\" "
            f"data-area=\"{esc(f.get('policy_area', ''))}\" "
            f"data-year=\"{esc(v.get('adopted_date_iso', '')[:4])}\" "
            f"data-source-status=\"{esc('public' if pub_count != '0' else 'withheld')}\" "
            f"data-search=\"{esc((title_html(texts, vid) + ' ' + (o.get('org_name_raw', ''))).replace('<', ''))}\">"
            f"<th scope=\"row\"><a href=\"record/{esc(vid)}.html\">{title_html(texts, vid, vid)}</a>"
            f"<br><span class=\"meta\">{esc(vid)} · {esc(v.get('version_label', ''))}</span></th>"
            f"<td>{esc(o.get('country_id', ''))}</td>"
            f"<td>{name_html(texts, o.get('org_id', ''), o.get('org_name_raw', ''))}</td>"
            f"<td>{esc(o.get('institution_category', ''))}</td>"
            f"<td>{esc(FUNC_LABELS.get(f.get('instrument_function', ''), f.get('instrument_function', '')))}</td>"
            f"<td>{esc(f.get('policy_area', ''))}</td>"
            f"<td>{esc(v.get('adopted_date_iso', '') or 'unknown')}</td>"
            f"<td>{esc(STATUS_LABELS.get(v['status'], v['status']))}</td>"
            f"<td>{esc(src)}</td></tr>")
    table = ("<h2>Policy versions</h2>"
             "<div id=\"filter-mount\"></div>"
             "<p id=\"filter-status\" aria-live=\"polite\" class=\"note\"></p>"
             "<p class=\"note\">With JavaScript enabled, this list can be filtered and "
             "searched. Without JavaScript, every record remains fully listed and every "
             "record page is a direct link.</p>"
             "<table id=\"version-list\" class=\"version-list\"><caption>All policy "
             "versions in this export, grouped by country</caption>"
             + head + "<tbody>" + "".join(body_rows) + "</tbody></table>")

    return f"""
<h1>Policy versions</h1>
<p class="intro">This is a local demonstration build of the ROARA OA/OS policy
explorer. <strong>Every record on this site is synthetic</strong> (fictional
countries, organizations and policies, using reserved example URLs). Its
purpose is to demonstrate the data contract, the export pipeline and the
record pages before any real corpus data passes through them.</p>

<h2>What this corpus is, and is not</h2>
<p>The underlying research corpus is a <strong>purposive sample</strong> of
open-access / open-science policies. It is not a census of issuers: counts you
see here describe the corpus and nothing else. No national prevalence can be
inferred from them, and nothing on this site ranks countries, institutions or
policies. See <a href="about.html">about, method and limitations</a> for what
unknown, not applicable, reviewed absence and numeric zero mean, and how dates,
evidence and permissions are handled.</p>

<h2>Overview</h2>
{chart}
{denom}
{org_table}
{table}
"""


ABOUT_BODY = """
<h1>About, method and limitations</h1>
<h2>Synthetic demonstration data</h2>
<p>This build contains only clearly labelled synthetic records (fictional
countries with user-assigned ISO codes XA and XB, fictional organizations,
reserved example URLs). No real policy, institution or document is described.
The synthetic seed corpus lives in <code>synthetic/</code> in the repository
and is marked <code>data_origin=synthetic</code> in every row.</p>

<h2>Purposive sampling</h2>
<p>The ROARA corpus is assembled purposively: issuers and documents were
selected for research reasons, not at random and not exhaustively. Therefore:
counts describe the corpus, never a country's sector; screened organizations
are not a national register; and no share, rate or prevalence may be computed
from this interface and presented as a national figure.</p>

<h2>What unknown, not applicable, reviewed absence and zero mean</h2>
<ul>
<li><strong>unknown / not yet reviewed:</strong> the field has not been
determined from available sources. The value column is empty.</li>
<li><strong>not applicable:</strong> the question does not arise for this
record (for example, hiring-linked evaluation for a funder). The value column
is empty, for a different reason than unknown.</li>
<li><strong>reviewed absence:</strong> a reviewer confirmed there is nothing
to find (for example, an organization screened and found to have no policy).
Absence is kept as data.</li>
<li><strong>numeric zero:</strong> a measured value of zero, distinct from all
three cases above (for example, a compliance dimension scored 0 after review
of the policy text).</li>
</ul>

<h2>Dates</h2>
<p>Adoption and effective dates are recorded as separate facts. Partial dates
keep their precision (year, month) and never gain an invented day. The
source's own wording is preserved as a verbatim string, including when it is
not a machine-readable date.</p>

<h2>Evidence, anchors and excerpts</h2>
<p>Each coded provision carries its modality, actor, action, object, scope,
conditions and exceptions, an anchor locating it in a concrete source
(page, article or section), and where permitted, an excerpt in the original
language. Excerpts appear only where the source's per-manifestation permission
review permits republication or a documented quotation exception applies;
otherwise the anchor and the links appear without the excerpt.</p>

<h2>Sources and permissions</h2>
<p>Original policy documents are never redistributed by this project. The
explorer links to issuer copies and archival snapshots. Non-public or
unrecovered sources are never attached; their existence is summarized. Public
accessibility of a document is never taken as permission to redistribute it:
redistribution rights, attribution and excerpt permissions are reviewed per
manifestation.</p>

<h2>Relationships</h2>
<p>Policy versions are linked by typed relationships (for example
<em>replaces</em>). A version record shows its outgoing and incoming edges.
The corpus deliberately does not produce composite scores, rankings or
weighted indices; the ten-dimension profile is always shown per dimension.</p>

<h2>Privacy</h2>
<p>This site sets no cookies, collects nothing, and requires no login. If this
build is ever deployed on GitHub Pages, GitHub logs visitor IP addresses for
security purposes; that is stated here in advance.</p>

<h2>Downloads</h2>
<p>The complete public export is available as CSV files (one per entity) plus a
machine-readable manifest with checksums, linked from the
<a href="data/manifest.json">export manifest</a> and listed in the site
footer of the index page.</p>
"""


def build(export_dir: Path, out_dir: Path) -> None:
    export = {k: read_rows(export_dir / f) for k, f in EXPORT_FILES.items()}
    manifest = json.loads((export_dir / "manifest.json").read_text(encoding="utf-8"))

    texts = texts_map(export["texts"])
    orgs = by_id(export["organizations"], "org_id")
    families = by_id(export["policy_families"], "family_id")
    versions = sorted(export["policy_versions"], key=lambda r: r["version_id"])
    version_by_id = by_id(versions, "version_id")
    countries = by_id(export["countries"], "country_id")
    rel_rows = export["version_relationships"]

    base = Template((SITE_DIR / "templates" / "base.tpl.html").read_text(encoding="utf-8"))

    def footer(root: str) -> str:
        return (
            f"Explorer demo build · contract v{esc(manifest['contract_version'])} · "
            f"exporter v{esc(manifest['exporter_version'])} · "
            f"input: {esc(manifest['input'])} · "
            + ("ALL RECORDS SYNTHETIC. " if manifest.get("contains_synthetic_records") else "")
            + "Data files: "
            + " · ".join(f'<a href="{root}/data/{f}">{f}</a>'
                         for f in sorted(EXPORT_FILES.values()))
            + f' · <a href="{root}/data/manifest.json">manifest.json</a>')

    def render(head_title, body, current, root: str = "."):
        banner = ("<p class=\"banner\"><strong>Synthetic demonstration build.</strong> "
                  "All records are fictional; see the about page.</p>"
                  if manifest.get("contains_synthetic_records") else "")
        return base.substitute(
            head_title=esc(head_title), banner=banner, body=body,
            root=root, footer_note=footer(root),
            aria_index=' aria-current="page"' if current == "index" else "",
            aria_about=' aria-current="page"' if current == "about" else "")

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "record").mkdir(exist_ok=True)

    # index.html
    (out_dir / "index.html").write_text(
        render("Policy versions", index_body(orgs, families, texts, versions, export), "index"),
        encoding="utf-8")
    # about.html
    (out_dir / "about.html").write_text(
        render("About", ABOUT_BODY, "about"), encoding="utf-8")

    # record pages
    provisions_by_version: dict[str, list[dict]] = {}
    for p in export["provisions"]:
        provisions_by_version.setdefault(p["version_id"], []).append(p)
    for lst in provisions_by_version.values():
        lst.sort(key=lambda r: r["provision_id"])
    manifestations_by_version: dict[str, list[dict]] = {}
    for m in export["manifestations"]:
        manifestations_by_version.setdefault(m["version_id"], []).append(m)
    for lst in manifestations_by_version.values():
        lst.sort(key=lambda r: r["manifestation_id"])
    functions_by_version: dict[str, list[dict]] = {}
    for fn in export["version_functions"]:
        functions_by_version.setdefault(fn["version_id"], []).append(fn)

    for v in versions:
        vid = v["version_id"]
        f = families.get(v["family_id"], {})
        o = orgs.get(f.get("issuer_org_id", ""), {})
        c = countries.get(o.get("country_id", ""), {"country_id": "?"})
        page = record_page(v, f, o, c, texts,
                           provisions_by_version.get(vid, []),
                           manifestations_by_version.get(vid, []),
                           rel_rows, version_by_id,
                           functions_by_version.get(vid, []))
        (out_dir / "record" / f"{vid}.html").write_text(
            render(f"Record {vid}", page, "record", root=".."), encoding="utf-8")

    # index.json (search/filter view for the optional JS enhancement)
    index_entries = []
    for v in versions:
        vid = v["version_id"]
        f = families.get(v["family_id"], {})
        o = orgs.get(f.get("issuer_org_id", ""), {})
        titles = {t["lang"]: t["text"]
                  for t in texts.get(vid, {}).get("title", [])}
        index_entries.append({
            "version_id": vid,
            "titles": titles,
            "version_label": v.get("version_label", ""),
            "country": o.get("country_id", ""),
            "issuer": o.get("org_name_raw", ""),
            "issuer_type": o.get("institution_category", ""),
            "authority_level": f.get("authority_level", ""),
            "function": f.get("instrument_function", ""),
            "area": f.get("policy_area", ""),
            "status": v.get("status", ""),
            "adopted_year": (v.get("adopted_date_iso", "") or "")[:4] or None,
            "adopted_precision": v.get("adopted_date_precision", ""),
            "source_status": ("public" if v.get("derived_manifestation_public_count", "0") != "0"
                              else "withheld"),
            "data_origin": v.get("data_origin", ""),
            "url": f"record/{vid}.html",
        })
    (out_dir / "index.json").write_text(
        json.dumps({"versions": index_entries}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")

    # static + data copies
    shutil.copytree(SITE_DIR / "static", out_dir / "static", dirs_exist_ok=True)
    data_dir = out_dir / "data"
    data_dir.mkdir(exist_ok=True)
    for f in EXPORT_FILES.values():
        shutil.copy2(export_dir / f, data_dir / f)
    shutil.copy2(export_dir / "manifest.json", data_dir / "manifest.json")

    print(f"Site written to {out_dir}: "
          f"{len(versions)} record pages, index, about, data files.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the static explorer site from a public export.")
    ap.add_argument("--export", required=True, help="public export directory (e.g. exports/public)")
    ap.add_argument("--output", default="_site", help="output directory (default: _site)")
    args = ap.parse_args()
    export_dir = Path(args.export)
    if not (export_dir / "manifest.json").exists():
        print(f"ERROR: {export_dir} does not look like a public export "
              f"(manifest.json missing)", file=sys.stderr)
        return 2
    build(export_dir, Path(args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
