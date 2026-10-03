# DDDA governance: scenario-first methodology v2

## Status and authority

This is the S4-B operating guide for #174, after S1 Candidate Context/Governance Kernel, S2 emergency-only recovery isolation and S3 authority/projection separation. It routes to their canonical contracts; it creates no additional evaluator or decision authority.

`tests/fixtures/governance/scenario-matrix-v1.json` and [Governance characterization v1](governance-characterization-v1.md) remain the frozen pre-migration baseline. [Scenario matrix v2](../../tests/fixtures/governance/scenario-matrix-v2.json) describes the active post-migration behavior. A changed expectation must cite the owning change request and be tested against the production decision owner.

The S4-A Characterization Gate passed before S1 in merged PR #176 at exact SHA `fe7157efdd0e94c7ede4dfe7e7c71c91f045091f`; its recorded Python/PowerShell characterization and package-first validation are preserved as the v1 baseline.

## Core safety invariants

These invariants apply to every implementation and release path:

- Bind decisions to one repository, PR, candidate kind, source SHA and candidate package identity.
- Treat missing, stale, conflicting or non-success evidence as a blocker for its governed action.
- Keep collectors responsible for fresh evidence and the Governance Kernel responsible for semantic decisions.
- Keep Human Review, Human Release Decision, merge authorization and release/promotion authorization separate. Technical PASS grants none of them.
- Classify safety, projection and presentation mismatches separately. Unknown mismatch codes default to `SAFETY_BLOCKING`.
- Treat Project as a projection of canonical Issues, PRs, milestones and dependencies. A projection mismatch does not authorize or decide a release.
- Keep backlog/Project changes transactional: reconcile the complete repository and require `remaining_mismatches = 0` on read-back before accepting the mutation.
- Require explicit emergency intent for controlled recovery; titles, branches and other presentation signals cannot select it.

The [mandatory check contract](mandatory-check-semantics.md) defines #73 exact-SHA,
explicit-success and authoritative-attempt semantics in the existing kernel.

## Standard implementation path

1. Select the owning Change Request and its bounded acceptance criteria.
2. Create one implementation branch and one reviewable PR for that slice.
3. Run exact-SHA GitHub Actions validation and retain the single candidate-package identity.
4. Ask for Human Review of the same PR SHA and package.
5. Run the governed merge preflight, then wait for separate merge authorization.
6. Merge only the approved PR. Implementation merge does not start promotion or release.

## Standard release path

Use the versioned candidate and release workflow after the implementation changes are integrated. Candidate validation, Human Review, HRDR, physical release scope, required checks and Project projection are distinct evidence. Promotion and publication occur only after their own explicit human release decision and authorization. Follow the current [platform development lifecycle](../developer-guide/platform-development-lifecycle.md) and [release decision guide](../developer-guide/human-release-decision-and-release-scope-gate.md); this summary does not replace them.

## Exceptional playbooks and routing

| Situation | Use this canonical route |
|---|---|
| Controlled release recovery | [Controlled release-source recovery](../developer-guide/controlled-release-source-recovery.md). Emergency-only entry, explicit intent, separate authorization and preserved historical evidence. |
| Backlog or Project mismatch | [WP ↔ Backlog ↔ Delivery consistency](wp-backlog-consistency.md) and the repository's canonical Project reconciler. Reconcile and read back the whole repository; never repair only the visible row. |
| Miro automation or visual acceptance | [Miro execution profiles](../developer-guide/miro-execution-profiles.md). REST-first for deterministic automation; MCP is optional for interactive review and is not a CI gate. |
| Failed or stale implementation evidence | [Remediation contract in the development skill](../../knowledge/ddda-platform-development-skill.md#26-remediation-terminology-and-scope). Use a bounded, manifest-driven remediation only when it provides a concrete transport or repeatability benefit, then return to the normal PR lifecycle. |

## Scenario coverage and quality measures

The active matrix records the operation, flow, candidate kind, expected result and the canonical decision owner. Its executable Python rows call the production Governance Kernel, mismatch classifier or release-scope evaluator; Project mutation read-back remains exercised by the existing Project governance test and the canonical reconciliation workflow.

The matrix contract verifies its scenario count, unique identifiers, required axis coverage and one declared semantic owner per decision domain. These are contract-level measures: they do not claim to discover every duplicate implementation by static source counting. The migration keeps the v1 baseline for comparison, adds post-migration scenario coverage, and replaces the duplicate-package workflow sentence assertion with an artifact-cardinality behavior test.

If an implementation-shape assertion has no behavior-level meaning, remove it only after its invariant is represented by a scenario that exercises the production owner. Keep assertions that protect a distinct workflow boundary until equivalent behavior coverage exists.

## Change rule

Add or change a scenario in the same PR that changes its owning behavior. Keep the matrix descriptive: evidence collection remains in adapters, decisions remain in their canonical owner, and side effects remain behind the relevant authorization gate.

