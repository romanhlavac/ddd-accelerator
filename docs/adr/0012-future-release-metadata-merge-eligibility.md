# ADR 0012: Future-release metadata merge eligibility

Status: Accepted

Date: 2026-08-26

## Context

ADR 0011 blocks an implementation PR whose primary Change Request is outside
the one active release Milestone. That protects the physical source of the
active release. It also blocked PRs which only define the versioned plan and
Project projection for later releases: those PRs have a future CR but ship no
runtime or active-release content.

Open GitHub Milestones alone cannot identify the active train: planned future
versions may legitimately be open for roadmap visibility. The collector must
therefore distinguish the sole versioned active train from those future plans
without rewriting their live milestone state.

## Decision

The read-only merge eligibility collector derives the active train from the
exact PR-base `backlog-policy.yaml`: exactly one `DDDA X.Y.Z` entry must be
declared `open`, and exactly one live open Milestone with that same title must
exist. Any other open DDDA Milestone remains a planned future train; it cannot
change merge eligibility merely through its live state. Missing, duplicate or
non-live active evidence fails closed.

The collector may permit a future-release planning PR only when it proves all
of the following from live GitHub data and the exact base/head Git trees:

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

The first implementation of the integration-merge normalization exposed a
second bootstrap condition: a correction to that guard is neither a future
release plan nor active-release content. A second exact-base-bound transition
may therefore introduce a **governance-repair-only** allowance. Its base is
`fdcc2b323eff4bcc9cef71207e280f3ffa950dd8`, its primary CR is #16, and its
PR must carry one exact transition record and change exactly the collector,
its collector tests, the eligibility evaluator and this ADR. The transition
expires when `main` advances.

After that transition, a guard repair is allowed only if it changes exactly
the collector, its collector tests and this ADR; all are modifications; its
sole primary CR is #16; and the complete versioned governance bootstrap is
identical between base and branch-only head. A conventional current-`main`
integration merge may be normalized only under the existing two-parent proof.
Thus neither the active 0.1.1 scope nor any release-plan metadata can enter
through this allowance.

## Consequences

- a runtime, release or active-scope change remains blocked outside the active
  train;
- an open future Milestone cannot silently become the active train;
- missing, ambiguous or stale GitHub/file evidence fails closed; and
- future milestones remain versioned Git authority and are projected only by
  the canonical reconciler after their PR is governed-merged.

## Validation

- unit tests cover active-train allowance, future-plan proof, incomplete proof
  rejection and the exact-base transition;
- standard exact-SHA CI and package-first validation remain mandatory.

## Active-train marker regression

An open future milestone is planning data, not an active release train. The guard selects exactly one open train carrying the explicit `pre_release_prerequisites` marker. Missing or duplicate markers fail closed; future open milestones cannot block an implementation merge for the active train.
