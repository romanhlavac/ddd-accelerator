# ADR 0018 — Branch taxonomy and automation lifecycle

Status: Proposed for DDDA 0.1.2 (#65); pending Human Review.

## Decision

New persistent platform implementation uses exactly
`feature/<change-id>-<short-name>`, `fix/<change-id>-<short-name>`,
`docs/<change-id>-<short-name>` or `release/<version>`.
`automation/<purpose>-<run-id>` is the only ephemeral control-plane namespace.
It never supplies implementation authority or hosts a standard implementation PR.
`feat/`, `chore/`, `gov/`, `governance/` and `agent/` cannot start new work.
Conventional Commit `chore:` remains a commit type, not a branch category.

The versioned policy grants two exact-head compatibility exceptions for the
already open PR #95 and published controlled-source PR #146. Each expires on
PR terminal state or a changed head; renewed implementation requires an explicit
reviewed policy change. Historical branches are not renamed or deleted merely
because their names do not meet the prospective grammar.

Standard repository CI evaluates the branch and PR identity. It loads the
exception registry from trusted `main`, preventing a PR from introducing its
own exception. The policy bootstrap PR may use its source policy only for a
canonical branch, with exceptions disabled. A new automation branch fails the
same implementation PR gate.

An automation branch originates from the exact GitHub Actions `GITHUB_SHA`,
`GITHUB_RUN_ID` and `GITHUB_ACTOR`. A single commit records a versioned manifest
at `.ddda/automation-provenance.json`; further content is restricted to
`.ddda/automation-staging/`. The workflow records the resulting exact branch
HEAD. The `managed_branch` context performs cleanup in `finally` for both
successful and failed work. Ordinary deletion requires fresh HEAD identity,
complete allowed-path history, owner/run/source identity, no associated PR and
no known tag or published release reference. If any proof is absent, retain the
branch and report the reason. This is a mechanism for future control-plane work;
the current Project workflow does not create a staging branch.

The existing Project reconciliation workflow performs a read-only stale audit
on each run. It reports terminal automation branches older than seven days and
their safe/ambiguous classification in its audit artifact. It does not schedule
a new privileged writer or delete historical branches. A producer that uses an
ephemeral branch owns immediate success/failure cleanup; the stale audit catches
residue after interrupted producers.

## Compatibility and migration

The 2026-10-03 inventory records all 118 branch HEADs, associated PRs,
ahead/behind counts, last activity, release/audit references and decisions.
Four V1–V4 recovery-generation branches are retained for release evidence,
including open PR #146 and the published v0.1.1 source. No existing branch
meets deterministic automatic-delete proof; no historical deletion is executed.
Older `gov/` branches and the pre-contract `automation/` branch remain
AMBIGUOUS. Reclassify only after a fresh repository-wide read-back and an
explicit human decision for uncertain history. There is no history rewrite,
force push or migration of active PRs.

This contract does not change Candidate Context, controlled recovery isolation,
release candidate identity or Conventional Commit taxonomy. Merge, release and
tag decisions remain governed by their independent authorities.
