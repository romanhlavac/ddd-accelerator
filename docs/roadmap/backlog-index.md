# Roadmap Work Package and GitHub backlog index

Parent/sub-issue represents capability ownership. Native `blocked by` represents direct completion dependency. Priority/order is authoritative in GitHub Project.

## Recommended implementation order

1. **WP-08 / #17 — P0**: close current PR #8 / DDDA 0.1.0 foundation.
2. **WP-11 / #20 — P1**: EventStorming methodology & workshop runtime.
3. **WP-12 / #60 — P2**: Miro platform environments & lifecycle; may overlap WP-11 after stable PR8 Miro baseline.
4. **WP-13 / #61 — P3**: multi-agent orchestration & evidence synthesis.

## Approved release train

Milestone membership is a deliberate release-scope decision, not release approval. No target date is implied.

| Release | Scope |
| --- | --- |
| DDDA 0.1.1 | Stabilization/release safety only: #9, #12, #67, #68, #70, #96, #98. Do not add scope. |
| DDDA 0.1.2 | Governance simplification and stabilization: #16, #65, #69, #73, #85, #94, #113, #125, #131, #132, #171, #172, #173, #174. Planning target: 2026-09-30; the date is not release authorization. |
| DDDA 0.2.0 | EventStorming MVP: #34, #35, #48, #52, #66. |
| DDDA 0.3.0 | Enterprise ingestion and EventStorming evidence integration: #27–#33, #47, #62, #46. |
| DDDA 0.3.1 | Miro platform lifecycle: #53–#57. |
| DDDA 0.4.0 | Strategy and portfolio: #21–#25, #50, #26, #51. |
| DDDA 0.5.0 | Multi-agent orchestration: #36–#41. |

The plan corrects one dependency conflict in the earlier draft: #62 cannot be in 0.2.0 because it is directly blocked by #47, which needs the ingestion core and security work in 0.3.0. Therefore #62 and the resulting first-user explanation #46 are both in 0.3.0.

Remain intentionally outside any milestone: #44 (0.1.1 pre-release prerequisite, not release scope), #45 and #49 (separate cross-cutting decisions), and #88 (scope decision pending).

## WP-08 — #17

Children: #9–#15 only. PR #8 remains the implementation under closure. No new feature scope.

#45 is now cross-cutting `Work Package: Other`.

## WP-09 — #18

Children: #21, #22, #23, #24, #25, #50, #26, #51.

## WP-10 — #19

Children: #27–#33.

## WP-11 — #20 EventStorming

Children: #34, #52, #35, #47, #48, #46, #62.

Dependency model:

```text
#34 + #52 → #35
#27 + #31 + #32 + #34 + #35 → #47
#34 + #35 + #47 + #48 + #52 → #62
#47 + #62 + #48 + #52 → #46
```

## WP-12 — #60 Miro platform environments

Children: #53, #54, #55, #56, #57.

```text
#53 → #57
#54 → #57
#55 → #57
```

## WP-13 — #61 Multi-agent

Children: #36, #37, #38, #39, #40, #41.

```text
#36 → #37 → #38
#36 + #37 + #38 → #39
#37 + #38 + #39 → #40
#36 + #37 + #38 + #39 + #40 → #41
```

## WP-14 — #148 Multi-Model Workbench & Git-backed Model Synchronization

Children: #149, #150, #151, #152, #153, #154.

```text
#149 → #150
#149 → #151
#149 → #152
#149 + #150 + #151 + #152 → #153
#150 + #153 → #154
```

Proposed target 0.2.0 is planning metadata only; #148–#154 remain outside Milestones and Project priority/order remains unset until separate human decisions.

## Cross-cutting

- #16 — GitHub-native backlog governance;
- #45 — GitHub Pages Artifact Registry dashboard (`Other`);
- #49 — role-based documentation IA (`Other`), blocked by #16, #46, #48 and #53;
- #113 — entry-point operating-model documentation (`Other`, primary `DOC`, secondary `METHODOLOGY`), planned for DDDA 0.1.2.
- #125 — historical DDDA 0.1.0 GitHub Release publication backfill (`Other`, primary `RELEASE`), P1 and planned for DDDA 0.1.2.
- #131 — canonical release-candidate PR identity (`Other`, primary `RELEASE`), P1 and planned for DDDA 0.1.2; visible through title, labels, branch and versioned body marker.
- #132 — canonical GitHub artifact naming convention (`Other`, primary `SECURITY-GOVERNANCE`), P2 and planned for DDDA 0.1.2; consumes #65 branch ownership and #131 release-candidate specialization.
- #171 — P0 Candidate Context and singular Governance Kernel (`Other`, primary `RELEASE`); consolidation authority only.
- #172 — P1 emergency-only controlled-recovery isolation (`Other`, primary `RELEASE`); blocked by #171.
- #173 — P1 safety-critical vs governance-projection mismatch taxonomy (`Other`, primary `SECURITY-GOVERNANCE`); blocked by #171.
- #174 — P1 scenario-first quality and methodology simplification (`Other`, primary `TESTING`); its Characterization Gate precedes #171, while issue completion is blocked by #172 and #173.

DDDA 0.1.2 direct completion dependencies:

```text
#171 -> #172, #173
#172 + #173 -> #174 completion
#173 -> #69, #94
#171 + #173 -> #73
#174 -> #85, #113
#171 + #172 -> #131
#65 + #131 -> #132
```

#174 is deliberately phased: its Characterization Gate is an entry criterion for #171, not a native completion dependency, so the native dependency graph remains acyclic. #125 remains independent and any historical GitHub Release publication still requires separate explicit human authorization.

- #155 — WP-14 canonical backlog/Project governance enablement (`Other`, proposed 0.1.2); priority and Milestone membership remain unset.

## Boundary invariant

WP-11 base EventStorming does not have a mandatory dependency on WP-13. WP-13 output can be an optional analytical input only.
