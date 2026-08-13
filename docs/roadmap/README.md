# DDDA platform product roadmap

## Purpose

Versioned long-term product roadmap. GitHub Issues remain authoritative for detailed requirements; GitHub Project is authoritative for operational priority/order; Milestones define release scope, not approval.

## Work Packages

| Order | Priority | WP | Outcome | State | Target |
|---:|---|---|---|---|---|
| 1 | P0 | WP-08 | DDDA 0.1.0 platform foundation & PR8 closure | active / blocked | 0.1.0 |
| 2 | P1 | WP-11 | EventStorming methodology & workshop runtime | backlog | TBD |
| 3 | P2 | WP-12 | Miro platform environments & lifecycle | backlog | TBD |
| 4 | P3 | WP-13 | Multi-agent orchestration & evidence synthesis | backlog | TBD |
| — | existing project priority | WP-09 | Strategy, portfolio & program lifecycle | backlog | TBD |
| — | existing project priority | WP-10 | Enterprise ingestion | backlog | TBD |

The numbered order above is the recommended default sequence requested for the newly restructured streams. WP-12 may overlap WP-11 after the relevant PR8 Miro baseline is stable. This ordering is represented by Project `Priority`; it is not an artificial native blocked-by chain between sibling Work Packages.

## Capability boundaries

```text
WP-08  close current PR8 foundation only

WP-10 registered evidence ───────┬────→ WP-11 EventStorming
                                └────→ WP-13 multi-agent

PR8 generic Miro baseline ───────────→ WP-12 Miro platform lifecycle
                                      └→ WP-11/#35 reuses generic boundary
```

WP-11 does not require WP-13 for its base workshop flow. WP-13 may later provide optional analytical hypotheses/candidates to WP-11.

## Scope rules

- Parent/sub-issue = capability ownership, not release scope.
- Milestone = release scope, not release approval.
- Project Priority = operational implementation order.
- Human Review PASS / HRDR / GO-NO-GO remain explicit human decisions.
- No new feature scope is added to PR #8 through WP-08.

## Detail

- [WP-08 — DDDA 0.1.0 platform foundation & PR8 closure](work-packages/WP-08-platform-lifecycle-and-steering.md)
- [WP-09 — Strategy, portfolio & program lifecycle](work-packages/WP-09-strategy-portfolio-program-lifecycle.md)
- [WP-10 — Enterprise ingestion](work-packages/WP-10-enterprise-ingestion.md)
- [WP-11 — EventStorming methodology & workshop runtime](work-packages/WP-11-eventstorming-methodology-workshop-runtime.md)
- [WP-12 — Miro platform environments & lifecycle](work-packages/WP-12-miro-platform-environments-lifecycle.md)
- [WP-13 — Multi-agent orchestration & evidence synthesis](work-packages/WP-13-multi-agent-orchestration-evidence-synthesis.md)
- [GitHub backlog index](backlog-index.md)
