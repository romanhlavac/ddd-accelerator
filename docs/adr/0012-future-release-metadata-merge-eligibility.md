# ADR 0012: Future-release metadata merge eligibility

Status: Accepted

Date: 2026-08-26

## Context

ADR 0011 blocks an implementation PR whose primary Change Request is outside
the one active release Milestone. That protects the physical source of the
active release. It also blocked PRs which only define the versioned plan and
Project projection for later releases: those PRs have a future CR but ship no
runtime or active-release content.

## Decision

The read-only merge eligibility collector may permit a future-release planning
PR only when it proves all of the following from live GitHub data and the exact
base/head Git trees:

- its changed-path set is exactly the four versioned planning paths;
- every changed file is a modification, not an add, rename or delete;
- the active `DDDA X.Y.Z` milestone specification is byte-for-data unchanged
  between base and head;
- the active live milestone issue set equals the base specification; and
- metadata for every active-release issue is unchanged between base and head.

The exception does not create a milestone, change a Project, merge a PR,
promote, release or tag. It only permits a separately governed implementation
merge after the ordinary exact-SHA CI, candidate, Human Review and explicit
merge authorization gates pass.

The guard remediation that introduces this decision has one exact-base-bound
transition: base `b61392ace66a95c808f321f3bd4b046cc5f564e5`, primary CR #16,
an exact JSON marker and an exact six-file path/status set. It expires automatically
when `main` advances and is not a general governance exception.

## Consequences

- a runtime, release or active-scope change remains blocked outside the active
  train;
- missing, ambiguous or stale GitHub/file evidence fails closed; and
- future milestones remain versioned Git authority and are projected only by
  the canonical reconciler after their PR is governed-merged.

## Validation

- unit tests cover active-train allowance, future-plan proof, incomplete proof
  rejection and the exact-base transition;
- standard exact-SHA CI and package-first validation remain mandatory.
