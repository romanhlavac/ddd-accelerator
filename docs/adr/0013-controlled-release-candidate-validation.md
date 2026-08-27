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

The workflow has three isolated operations:

1. `technical_validation` checks out the exact candidate, builds one
   canonical package, and runs `validate-pr` against that physical package.
2. `publish_hrdr_scaffold` publishes only a pending HRDR after explicit
   reviewer and decision-owner inputs.
3. `release_scope_dry_run` invokes `promote-pr -DryRun`; it cannot merge,
   tag, publish or promote.

Each operation fails closed on identity drift. The workflow never changes a
milestone, Project field, scope, release, tag or promotion state.

## Consequences

Technical candidate evidence, the human release decision and release promotion
remain separate gates. A PASS technical validation does not create a GO
decision, and the scope dry-run remains authoritative only with live Project
read-back and an HRDR for the same candidate identity.
