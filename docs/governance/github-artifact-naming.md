# GitHub artifact naming v1 (#132)

This is the single vocabulary for DDDA GitHub artifacts. A name is a human-facing projection of an artifact's role; Git, Issue/PR state, versioned records and release evidence retain their respective authority. New artifacts use the patterns below. Historical identities are preserved under the legacy policy at the end of this guide.

| Artifact | Semantic role | Canonical pattern and example | Machine authority | Human projection / legacy exception | Owner |
|---|---|---|---|---|---|
| Issue: Work Package | Roadmap parent | `[WP-09] Outcome` | GitHub Issue, native parent relation, Project planning fields | `[WP-XX]` prefix; no state in title | backlog contract, #132 |
| Issue: Change Request | One planned change | `[CR][GOV] Outcome` | Issue body, native relations and Project planning fields | `[CHR]` is historical alias only; never create a new `[CHR]` | backlog contract, #132 |
| Issue: defect | Reproducible fault | `[DEFECT][AREA] Symptom` | Issue classification and evidence | Existing differently titled defects retain identity | #132 |
| Issue: enabler | Prerequisite capability | `[ENABLER][AREA] Outcome` | Issue classification and dependency | Existing titles retain identity | #132 |
| Issue: release planning | Release work/decision request | `[RELEASE][X.Y.Z] Outcome` | Issue scope and release evidence | An Issue title never proves publication | release lifecycle, #132 |
| Ordinary implementation PR | Code/docs change | `feat(governance): outcome (#132)`; `fix(release): guard` | PR head SHA, primary `Implements/Closes #n`, CI and Human Review | Conventional title describes change; `fix(release)` is not a release candidate | development lifecycle, #132 |
| Release candidate PR | Exact normal or controlled candidate | See [candidate identity](release-candidate-identity.md) | S1 Governance Kernel evaluates title, branch, labels and v1 body marker together | `[RELEASE][X.Y.Z] Release candidate`; recovery has `[RECOVERY]` | #131 / ADR 0019 |
| Branch | Implementation, release or managed automation | See [branch lifecycle](branch-lifecycle.md) | #65 policy and exact ref/SHA | `feature/`, `fix/`, `docs/`, `release/`, `automation/`; legacy exceptions stay registered there | #65 / ADR 0018 |
| Labels | Navigation, or explicit candidate identity | `release-candidate`, `controlled-recovery`; other labels below | Candidate labels are interpreted only by S1 Kernel with all other surfaces | Labels never replace Project Item Type, Status or release evidence | #131, #132 |
| Body/comment marker | Versioned machine record | `<!-- ddda:<semantic-kind>:vN -->` | The owning schema/evaluator and provenance | Marker is not a second decision owner | record owner, #132 |
| Milestone | Planned train | `DDDA 0.1.2` | Milestone scope and planning contract | Planned scope is not release success | release lifecycle |
| Annotated Git tag | Immutable version ref | `v0.1.2` | Annotated tag object and peeled source SHA | Preserve historical tag object | release lifecycle |
| GitHub Release | Published distribution | `DDDA 0.1.2`, tag `v0.1.2` | Validated package hash, report, decision and server read-back | Publication is separate from tag and Milestone | release lifecycle / #125 |
| Actions workflow and job | Stable execution/check role | `DDDA platform CI` / `Governed merge dry-run` | Exact run, job/check name, attempt, conclusion and SHA | Do not rename required checks cosmetically; pin changes with migration | #73, CI contract |
| Actions candidate/report artifact | Exact validation evidence | `ddda-candidate-<40-hex-SHA>` / `validate-pr-<PR>-<40-hex-SHA>` | Physical ZIP digest and validation report from one run | Run and artifact IDs are read-back locators, not name substitutions | candidate context, #73 |
| Actions reconciliation artifact | Project audit | `ddda-project-backlog-delivery-audit-v6-<40-hex-SHA>` | JSON audit, source SHA, remaining mismatches | Runner-local paths are never stable identity | Project contract |
| GitHub Project / view | Navigation projection | `DDDA Platform Backlog & Delivery`; `Plánování a Backlog`, `Implementace a Delivery`, `Release & Delivery History` | Versioned Project projection contract plus fresh read-back | Active delivery filters `is:pr is:open`; history filters merged PRs, with release fields only after #69 evidence checks | Project contract, #69 |

The three version surfaces `DDDA X.Y.Z` Milestone, `vX.Y.Z` annotated tag and `DDDA X.Y.Z` GitHub Release share a version string but represent different facts. A Project row, Issue title, tag alone or workflow artifact name cannot assert `Released`.

## Small label catalog

`release-candidate` and `controlled-recovery` are identity signals owned by #131; both must be provisioned before creating a new candidate. The existing GitHub defaults (`bug`, `documentation`, `enhancement`, `duplicate`, `good first issue`, `help wanted`, `invalid`, `question`, `wontfix`) remain optional navigation labels. Do not infer Item Type, impact, milestone, Human Review or release status from those defaults. New role labels require a separately versioned mapping to deterministic authority and a dry-run backfill; no label name should duplicate Project status.

## Marker registry

The namespace is `ddda`, semantic kind is lower-case kebab case and `vN` is an integer schema version. A new synonym for an existing record is prohibited. Owners parse the full record and fail closed on cardinality or disagreement.

| Marker | Meaning / owner |
|---|---|
| `ddda:release-candidate:v1` | Candidate identity, S1 Governance Kernel / #131 |
| `ddda:human-pr-review:v1` | Human implementation review, provenance collector and Kernel |
| `ddda:change-classification:v1` | PR impact classification, merge policy |
| `ddda:0.1.2-residual-scope:v1` | Planning rebaseline, backlog contract |

Other existing versioned HRDR, release-decision and exception markers retain their owning contracts; this catalog does not reinterpret them. Keep explicit `CR #n` and `PR #n` references. `R<n>` is implementation revision lineage; #85 owns the review vocabulary.

## Legacy inventory and non-destructive backfill

| Historical pattern | Canonical semantic role | Disposition |
|---|---|---|
| `[CHR]` Issue | Change Request only with independent planning authority | `AMBIGUOUS` without that proof; preserve title |
| `[WP-XX][CR]` Issue | Historical WP-scoped child Change Request when native parent and Item Type agree | `PRESERVE_AS_HISTORICAL_IDENTITY`; first prefix alone never makes it a Work Package |
| `[CR]`, `[WP-XX]`, `[DEFECT]`, `[ENABLER]`, `[RELEASE]` Issue | Role indicated by structured prefix, subject to Project/Issue agreement | `SAFE_TO_NORMALIZE` only for additive metadata with fresh corroboration; no automatic rename |
| `[GAP]` Issue | Intake before triage | `PRESERVE_AS_HISTORICAL_IDENTITY`; do not promote by title alone |
| `[0.1.1][#n]`, `[GOV]`, `gov(roadmap):`, `recovery(0.1.1):`, `fix(release):` PR | Implementation or historical release/recovery role by exact PR/branch/evidence | `PRESERVE_AS_HISTORICAL_IDENTITY`; an ambiguous role needs decision |
| `feat/`, `gov/`, `governance/`, `chore/`, `agent/`, old `automation/` branch | Legacy ref | `PRESERVE_AS_HISTORICAL_IDENTITY` or `AMBIGUOUS` per #65; no cosmetic ref change |
| Existing tag, published Release, Human Review, HRDR, release-decision evidence | Audit identity | `PRESERVE_AS_HISTORICAL_IDENTITY` |

Inventory must record each artifact ID, observed title/ref, current labels/status, authoritative evidence, proposed additive mutation and one of `SAFE_TO_NORMALIZE`, `PRESERVE_AS_HISTORICAL_IDENTITY`, `AMBIGUOUS`. Missing evidence is `AMBIGUOUS`, not guessed from free text. Open title rename additionally needs fresh proof of no machine/audit binding and a bounded audit record. Closed/merged PR titles, tags, published Releases, audit-sensitive refs and human/release evidence are not renamed for consistency.

Backfill sequence: capture fresh repository-wide snapshot → deterministic dry-run and plan digest → review ambiguous rows → bounded additive writes for explicitly proved rows only → read back every changed ID → full Project reconcile with `remaining_mismatches = 0` → second run with zero writes. Stop on changed identity, drifted plan digest or a conflicting label. The initial inventory is intentionally read-only; this guide does not authorize heuristic writes. Project history and release-state backfill remain #69.
