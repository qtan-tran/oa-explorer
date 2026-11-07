# Continuation note — next milestone and expected data handoff (2026-11-08)

Written at the end of the M1 session. Read together with
[docs/handover.md](../handover.md) and the
[M1 implementation report](2026-11-08-m1-implementation-report.md).

## Next milestone: M2 — real-data pilot gate (needs your explicit go)

Per plan §6, M2 runs a small reviewed subset of real corpus data through
the local pipeline. Nothing in M2 publishes anything. It is blocked on
one external input, **U1: the reviewed Axis 2 export** from the corpus
project (or, if Axis 2 does not produce it, the plan's fallback
selection: ~20 DE records with `update_group` chains plus a sample across
all coding statuses, ~15 records, from a pinned corpus release tag).

M2 acceptance (from the plan): pilot export validates against the
contract; corpus team sign-off recorded per record
(`review_state=approved_public` + approver + date); discrepancy log
written for every v1→contract mapping judgement; site runs locally on
the pilot export; pilot files stay in local gitignored directories.

Before M2, two smaller items can proceed independently and are safe
next steps for the corpus team:

- **M0 ratification work** (no code): corpus team answers OQ1–OQ8 in the
  data contract draft; ratifies the public-field allowlist (currently
  `draft_pending_OQ3`) and the `data_origin` column addition proposed in
  M1.
- **Manual accessibility walkthrough of the M1 synthetic site** (part of
  M3, can start early): keyboard-only pass (list → filter → search →
  record → back) plus one screen-reader spot check (NVDA or VoiceOver),
  documented honestly; and `pipeline/check_links.py --check` on a
  network-enabled machine to baseline dead-link reporting.

## Exact data handoff expected from the corpus project

To run M2, the corpus project (Axis 2 / `oa-os-policy-collections`) should
deliver, per a **pinned release tag** (not a moving branch):

1. **A reviewed, approved-for-publication subset** of records as flat
   CSV (or the pinned release's equivalent) covering, for each record:
   - the approved public fields only, matching
     `contract/public_allowlist.csv` (any field outside the allowlist
     must be explicitly flagged as proposed-for-inclusion, with the
     deciding reviewer named, so ratification can happen per field);
   - per-record review state: `approved_public` + approver + approval
     date (or a lower state; those rows simply never enter the export);
   - original-language titles/texts and excerpts exactly as reviewed,
     with their `excerpt_policy` permission decision per manifestation.
2. **Archival snapshots** for every live source link in the subset (the
   corpus dictionary already requires capture): archival URL + archive
   date + archive service, so the explorer never links only to
   issuer-controlled pages.
3. **The resolved `policy_source` vocabulary** (or a mapping table), so
   `contract/legacy_map_v1.csv`'s flagged drift rows can be closed
   instead of guessed.
4. **A discrepancy log template** (or agreement to use the repo's): every
   judgement mapping a v1 56-column row to contract entities gets a line
   — what was mapped, what was dropped, what needs human review.
5. **Explicit statements of non-coverage**: which countries/issuers in
   the subset are intentionally absent from the pilot, so the site's
   corpus-only disclaimers stay truthful.

Not expected and must **not** be delivered: full-resolution source PDFs,
private review notes, or the detailed research ledger — those stay in
corpus-side or institutional storage, per AGENTS.md rule 2.

## Suggested next prompt (for the owner)

> "Proceed with M2. Here is the pinned corpus release tag and the Axis 2
> pilot export at [path]; the pilot subset is [description]. The ledger
> files are placed in the local gitignored `ledger/` directory and are
> NOT to be committed. Validate them, write the discrepancy log, build
> the pilot export and site locally, and report what changed versus the
> synthetic build. Do not publish or push anything."

## Pushing M1 to GitHub (owner action; nothing was pushed by the session)

The session could not push (tooling is read-only against GitHub by
design). After reviewing the working tree:

```bash
git add -A
git commit -m "M1: local vertical slice — contract schemas, validator, exporter, synthetic corpus, static site, 88 tests"
git push origin main
```

Before pushing, spot-check that no build product slipped in
(`git status` should show no `exports/`, `_site/`, `ledger/` files; they
are gitignored) and that `synthetic/` is the only data directory staged.
