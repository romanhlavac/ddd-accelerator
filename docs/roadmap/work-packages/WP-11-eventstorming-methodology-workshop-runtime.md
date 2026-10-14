# WP-11 — EventStorming methodology & workshop runtime

Parent: #20. Target: TBD. Priority: P1.

Children: #34, #52, #35, #47, #48, #46, #62.

## Desired outcome

Deliver a standalone, methodologically consistent, package-first EventStorming workflow.
Registered WP-10 evidence seeds an executable session and Miro workshop; governed round-trip consolidates artifacts and the Control Center before an explicit human decision.
The base workflow and its acceptance do not require multi-agent orchestration.

## Scope and ownership

| Owner | Outcome owned by the existing Change Request |
|---|---|
| #48 | DDD Starter WHEN/WHY and phase semantics |
| #52 | Detailed HOW to facilitate Big Picture, Process Modeling and Design-Level |
| #34 | Executable EventStorming session/item contracts and runtime state |
| #35 | EventStorming-specific Miro realization over generic PR8/WP-12 runtime |
| #47 | Registered evidence → session → workshop composition |
| #62 | Package-first workshop E2E acceptance |
| #46 | First-user target/as-built explanation of the composed workflow |

Generic Miro environment lifecycle stays in WP-12.
#36–#41 belong to WP-13; its analytical hypotheses may later be optional input, but cannot become a mandatory WP-11 completion dependency.
This roadmap describes existing native Issue #20 scope; it does not implement those future capabilities or change their target Milestones.

## Dependencies and delivery slices

Consumed contracts: stable PR8 validation/Human Review safety and generic Miro baseline, WP-10 registered evidence/provenance, and applicable WP-12 environment lifecycle.

Dependency model:

```text
#34 + #52 → #35
#27 + #31 + #32 + #34 + #35 → #47
#34 + #35 + #47 + #48 + #52 → #62
#47 + #62 + #48 + #52 → #46
```

Recommended slices from Issue #20:

1. Align #52/#48 terminology and non-duplicated methodology ownership.
2. Establish #34 compatibility with the session/item model.
3. Realize #35 using the generic Miro boundary.
4. Compose #47 without mandatory agent runtime.
5. Prove #62 from a physical package.
6. Close #46 using the resulting EventStorming E2E evidence.

The Work Package may span release Milestones. Individual CR membership remains authoritative in the [approved release train](../backlog-index.md); this documentation does not activate a train or reprioritize work.

## Acceptance and exit criteria

Issue #20 remains the capability acceptance authority:

- Exactly three EventStorming formats stay canonical.
- Big Picture does not require Commands, Policies or Aggregates.
- #48 and #52 do not duplicate methodology ownership.
- #47 has no mandatory dependency on #36–#40.
- #62 passes without multi-agent runtime.
- EventStorming Miro logic reuses generic platform runtime.
- Technical completion never implies human approval.
- #46 uses #62, not WP-13/#41, as its final EventStorming E2E acceptance.

WP-11 closes only when its native child acceptance and required human decisions are complete; documenting this roadmap does not mark the capability Done.

## Risks and mitigations

| Existing boundary at risk | Impact | Mitigation in the approved ownership/dependency model |
|---|---|---|
| #48 and #52 teach incompatible or duplicate methodology | Workshop inconsistency | One WHEN/WHY owner and one HOW owner; align terminology before executable slices |
| Big Picture inherits design-level prerequisites | Premature design and blocked discovery | Preserve the three formats and the explicit no Commands/Policies/Aggregates requirement for Big Picture |
| WP-13 becomes an implicit prerequisite | Base EventStorming delivery deadlock | #47/#62 acceptance must run without agent runtime; WP-13 input remains optional |
| #35 duplicates generic Miro lifecycle | Divergent ownership and maintenance | Reuse PR8/WP-12 contracts; keep EventStorming-specific realization in #35 |
| Evidence/session/round-trip loses provenance | Untraceable consolidated artifacts | Consume registered WP-10 evidence and test composition in #47, followed by package-first #62 |
| Technical PASS is mistaken for human approval | Invalid downstream decisions | Preserve explicit human decisions and the existing governance gates |
| #46 closes against unrelated agent evidence | Misleading first-user/as-built guide | Require #62 workshop E2E evidence and #47 composition before final #46 closure |

No residual risk is accepted by this roadmap. Risk decisions remain with the existing Issue owners and human governance.
