# ADR-0015: Fail-closed promotion from a controlled recovery source

## Context

A controlled recovery candidate is reconstructed from the previous canonical
tag because current `main` contains changes outside the approved release scope.
Merging that candidate back to `main` defeats the recovery boundary and may be
impossible when the histories intentionally diverge. The standard promotion
executor nevertheless assumed that every release PR must first merge.

## Decision

Governed promotion automatically selects controlled-source mode only when the
fresh Release Scope Gate is PASS and its physical-source evidence contains a
schema-v2 recovery ledger with an exact release-cut record. The PR must remain
open, Ready, repository-owned, based on `main`, use
`release/<version>-controlled-recovery-source` or a numbered superseding
generation `release/<version>-controlled-recovery-source-vN` where `N >= 2`,
and carry both the canonical candidate marker and explicit no-merge boundary.
The branch contract is identical to the trusted candidate selector: `v1`,
leading-zero generations and arbitrary suffixes are rejected fail-closed.

The governed wrapper passes operation-local Gate, validation-report and package
evidence to the executor. The executor revalidates repository, PR, exact head
SHA, version, package hash, Gate PASS and schema-v2 release-cut authority. In
controlled mode it:

- does not require GitHub mergeability;
- never merges the candidate or deletes its branch;
- checks out the exact PR head detached and keeps it as the release source;
- runs the normal changelog, CI, approval, release-validation and publication
  guards;
- materializes the canonical release package only after the validation suites
  and machine-readable report are PASS;
- creates the annotated tag and GitHub Release only after that PASS boundary.

Schema v2 permits exactly one deterministic release-cut metadata commit. It may
change only `CHANGELOG.md` and is bound to its single parent/result blob SHAs.
It is followed by exactly one ledger-only tip commit. Schema v1 remains
readable for existing evidence but cannot authorize controlled promotion.
Recovered commits and both metadata commits are disjoint roles. Any overlap,
including an entry that reuses the release-cut or ledger-tip SHA, fails closed.

Actual controlled no-merge promotion uses the explicit `-ConfirmPromotion`
authorization boundary. It rejects `-ConfirmMerge`; that parameter remains
specific to standard merge-first promotion and implementation merge.

Promotion dry-run exits before merge, package materialization, tag or release.
The governed wrapper performs fresh before/after read-back and records
zero-side-effect assertions.

## Consequences

The released source can remain the frozen, audited PR SHA without contaminating
`main` or weakening HRDR, RTDR, Release Scope Gate, exact-SHA validation, release
validation or publication controls. Ordinary release candidates retain the
standard merge-first behavior. Missing, ambiguous, stale or directly supplied
controlled evidence fails closed.
