# ADR-0013: Exact validation lane for controlled release candidates

## Context

A controlled recovery candidate is intentionally an open Draft audit surface and
must not be merged into `main`. Standard PR CI creates `validate-pr`
evidence only for ordinary `pull_request` events, so it cannot establish the
technical identity required by the release lifecycle for such a candidate.

## Decision

Add a manual GitHub Actions workflow hosted on trusted `main`.

Before every operation it reads the live candidate PR and requires all of:

- open Draft PR owned by this repository;
- exact requested head SHA;
- branch exactly `release/<version>-controlled-recovery-source`;
- base `main`;
- candidate body marker for the requested version.

The selection step is named and is the sole publisher of the selected exact SHA across job boundaries. If that output is absent or does not match the requested identity, validation must fail rather than fall back to the default branch.

The workflow has three isolated operations:

1. `technical_validation` checks out the exact candidate and invokes
   `validate-pr` in dedicated pre-promotion mode. It remains the sole canonical
   package builder and records evidence for that physical package without
   pretending the candidate is already a final release cut.
2. `publish_hrdr_scaffold` restores the one exact validation artifact and
   publishes only a pending HRDR after explicit reviewer and decision-owner
   inputs.
3. `release_scope_dry_run` restores that same physical package and report,
   reads exactly one authoritative HRDR, and invokes the read-only Physical
   Release Scope Gate directly. It does not call `promote-pr`, because that
   command deliberately rejects Draft implementation/release PRs.

Each operation fails closed on identity drift, missing/ambiguous validation
artifacts, package-hash mismatch or HRDR ambiguity. The workflow never changes a
milestone, Project field, scope, release, tag or promotion state.

## Consequences

Technical candidate evidence, the human release decision and release promotion
remain separate gates. A PASS technical validation does not create a GO
decision, and the scope dry-run remains authoritative only with live Project
read-back and an HRDR for the same candidate identity.

## Pre-promotion validation boundary

A controlled recovery candidate is an auditable source for validation, not a published
release. Its technical validation therefore uses `-PrePromotionCandidate`: it skips only
cross-stream integration assertions that require the canonical `main` CI surface.

This mode never authorizes promotion. The `promote-pr` path remains unchanged and
fail-closed: before any tag or GitHub Release, the release must contain versioned release
notes and pass the final promotion guards. A technical PASS is evidence of candidate
integrity, not a release decision.


## Evidence staging boundary

Runner-local environment variables are not evaluated in an action input expression.
After successful technical validation, the workflow therefore stages the exact report
directory and the single exact candidate package from `$env:LOCALAPPDATA` into
`$env:RUNNER_TEMP`. The upload action consumes only that staged directory.

Staging fails closed if the report directory is missing or the exact package count is
not one. This keeps artifact upload bound to the selected PR and SHA while avoiding a
silent empty upload.

## Report-bound package staging

The candidate package filename intentionally contains a short SHA for readability; the
full candidate identity is held by the validation report. Evidence staging therefore
requires exactly one PASS result.json, verifies its repository, PR and full commit
SHA, then resolves only the reported package basename beneath the runner-local package
store. It recomputes the package SHA-256 and requires it to match the report before
upload.

A missing report, invalid identity, unsafe package record, absent package or hash
mismatch fails closed. The filename alone is never treated as exact candidate evidence.


## Artifact pagination boundary

Artifact discovery is repository-wide and may exceed one API page. The workflow
therefore collects GitHub Actions artifact pages with a JSON-safe paged response,
flattens only their artifacts arrays and then requires exactly one unexpired
artifact with the exact candidate identity. A pagination, response-shape or
identity ambiguity remains fail-closed; it cannot select an arbitrary first
artifact or silently narrow the evidence set.