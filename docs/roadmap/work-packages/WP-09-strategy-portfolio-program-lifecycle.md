# WP-09 — Strategy, portfolio & program lifecycle

## Outcome

DDDA rozšíří project-level G1–G8 workflow o samostatnou strategickou/programovou vrstvu P0–P10. Propojí purpose, situational awareness, portfolio decisions, strategy-domain-team traceability, roadmap increments a benefits evidence bez smíchání programového a projektového approval.

## State

```text
State: backlog
Target release: TBD
Depends on: WP-08 release-grade validation and human-decision contracts
```

## Boundary with project lifecycle

```text
P0–P10 program/portfolio layer
  proč, kde a v jakém pořadí investovat

G1–G8 project layer
  jak vést konkrétní DDD/architecture project od Align po Code
```

Project states may be referenced by a program, but cannot be rolled up into automatic program approval.

## Child issues and capability ownership

| Issue | Owned capability |
|---|---|
| #21 | P0–P10 lifecycle and program gate contract |
| #22 | Strategy intake, purpose, outcomes and value chain |
| #23 | Wardley Mapping artifact and workflow |
| #24 | Portfolio prioritization and investment decision records |
| #25 | Strategy-domain-team traceability graph and impact queries |
| #50 | Program roadmap, increments, sequencing and benefits realization |
| #26 | Program Miro projection and Control Center |
| #51 | Synthetic reference program and package-first strategic acceptance |

The split is intentional:

- #25 owns typed links and graph semantics, not roadmap lifecycle;
- #50 owns roadmap/benefits, not traceability graph ownership;
- #26 owns visual projection, not the final cross-capability E2E;
- #51 owns reference acceptance, not implementation of component capabilities.

## Dependency order

```text
#21 + #22 → #23
#22 + #23 → #24
#21 + #24 → #25
#25 → #50
#50 → #26
#26 → #51
```

Issue text distinguishes:

- **Direct blocked-by** — native dependency required for completion;
- **Transitive prerequisites** — inherited, not duplicated natively;
- **Consumed contracts** — reusable contracts without automatic scheduling semantics;
- **Related work** — informational relationship only.

## In scope

- separate P0–P10 lifecycle and human gate semantics;
- strategy intake, user needs, purpose, outcomes and ownership;
- Wardley value chain, visibility/evolution hypotheses and strategic options;
- transparent portfolio evaluation, thresholds, veto criteria and sensitivity;
- human investment decision records;
- typed traceability among outcomes, capabilities, subdomains, BCs, systems and teams;
- roadmap increments, dependencies, sequencing and exit/decommission criteria;
- benefits hypotheses, indicators, observations and review points;
- program Miro Control Center/projection;
- synthetic multi-project package-first acceptance.

## Out of scope

- corporate PPM replacement;
- detailed task scheduling or financial accounting;
- automatic strategy, investment, priority, date or release approval;
- WP-10 ingestion implementation;
- WP-11 multi-agent runtime;
- changes to G1–G8 meaning;
- tactical DDD inside one BC as primary scope.

## Acceptance criteria

- [ ] P0–P10 and G1–G8 remain separate schemas, states and decisions;
- [ ] strategy intake identifies need, purpose, outcome, constraints and owner;
- [ ] Wardley Mapping starts from user need/value chain and makes uncertainty explicit;
- [ ] BC/application overlays do not silently replace the Wardley value-chain model;
- [ ] portfolio scores remain reproducible decision support, not approval;
- [ ] veto/mandatory criteria and sensitivity remain visible;
- [ ] traceability preserves BC-specific language and ownership boundaries;
- [ ] application realization does not imply domain ownership;
- [ ] priority, dependency, capacity, sequence, date and release are distinct dimensions;
- [ ] roadmap increments reference outcomes, decisions and exit criteria;
- [ ] benefit hypothesis is distinct from observed benefit;
- [ ] Miro is projection/workshop surface, not strategic authority;
- [ ] package-first reference includes at least two projects and one cross-project dependency;
- [ ] technical PASS plus human PENDING does not become overall PASS.

## Quality attributes

- strategic traceability;
- auditability and decision transparency;
- program/project state isolation;
- executive and architect usability;
- deterministic replay from versioned inputs;
- human control;
- tailoring and low ceremony.

## Dependencies

- WP-08 supplies package-first validation, exact-SHA evidence and human-decision safety;
- WP-10 may enrich evidence but is not required for initial synthetic/manual scenarios;
- WP-11 may assist analysis but cannot approve strategy.

## Exit criteria

- #21–#26, #50 and #51 are complete or explicitly deferred;
- program/project boundary tests PASS;
- reference program runs from package and produces auditable evidence;
- one strategic decision is explicitly human-reviewed;
- roadmap, Project hierarchy and dependency graph are current.
