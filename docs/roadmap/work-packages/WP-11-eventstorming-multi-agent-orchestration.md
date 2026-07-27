# WP-11 — EventStorming & multi-agent orchestration

## Outcome

DDDA poskytne proveditelný, auditovatelný EventStorming workflow a řízenou multi-agent orchestration, která umí rozdělit analytickou práci mezi specializované agenty, sloučit evidenci a konflikty a vrátit výstup člověku k rozhodnutí bez automatického schválení doménových, architektonických nebo release gatů.

## State

```text
State: backlog
Target release: TBD
Depends on: WP-08 human-only decisions, validation and release lifecycle
Consumes: WP-10 provenance contracts when available
```

## Problem / GAP

Současná platforma obsahuje metodické materiály, Miro templates a základní agent-contract schema, ale neobsahuje produkční runtime pro:

- řízené provedení Big Picture, Process a Design-Level EventStormingu;
- explicitní session state, facilitaci a workshop aftermath;
- rozdělení práce mezi specializované agenty;
- fan-out/fan-in execution;
- evidence provenance a merge;
- konfliktní návrhy a varianty;
- failure/resume a replay;
- human review points;
- audit a observabilitu agentických běhů.

Bez těchto kontraktů hrozí netransparentní autonomní generování artefaktů, ztráta source evidence, přepsání lidských rozhodnutí a nekontrolovatelný scope expansion.

## In scope

### EventStorming execution

- Big Picture EventStorming workflow;
- Process Modeling workflow;
- Design-Level EventStorming workflow;
- session charter, scope, participants/roles a facilitation state;
- events, commands, actors, policies, systems, hotspots, questions a evidence;
- timeline/order and correction semantics;
- candidate boundaries and rationale;
- workshop checkpoints and human decisions;
- aftermath, unresolved questions and hand-off to G2–G8 artifacts;
- Miro projection and Git/YAML authority.

### Agent orchestration

- versioned agent contracts;
- agent capability catalog;
- orchestrator run manifest;
- fan-out tasks with explicit scope and input evidence;
- fan-in result collection;
- conflict and alternative proposal records;
- provenance for every generated claim/artifact fragment;
- deterministic state machine for run status;
- cancellation, timeout, retry and resume;
- human checkpoints;
- audit logs, metrics and diagnostics;
- example multi-agent workflow;
- package-first validation.

## Out of scope

- autonomous business or architecture approval;
- autonomous gate `passed`;
- replacing domain experts or workshop participants;
- unrestricted agents with repository, network or Miro write access;
- hidden chain-of-thought storage as evidence;
- generic enterprise agent platform unrelated to DDDA;
- provider-specific lock-in as the primary contract;
- enterprise source ingestion adapters — WP-10;
- program portfolio semantics — WP-09;
- automatic code generation as a required outcome.

## Core principles

1. Agent receives explicit scope, inputs, allowed tools and expected output contract.
2. Every claim links to source evidence or is marked as hypothesis/inference.
3. Fan-in does not silently choose between conflicting outputs.
4. Human review decides accepted model, boundary, gate and architecture.
5. Miro changes follow existing mapping, conflict and tombstone contracts.
6. Agent runs are resumable and auditable.
7. No agent can commit, push, merge, release or approve unless a future explicit capability and human confirmation contract allows a bounded action.
8. Test fixtures use synthetic examples, never client workspace data.

## Proposed delivery slices

1. **Executable EventStorming session model**
   - schemas, session state, artifacts, checkpoints and aftermath.
2. **EventStorming Miro/Git round-trip**
   - managed items, mapping, conflict handling, layout and UTF-8.
3. **Agent contract v1 and capability catalog**
   - inputs, outputs, tools, scopes, provenance and safety constraints.
4. **Orchestrator state machine**
   - planned/running/waiting_for_human/failed/resumable/completed states.
5. **Fan-out execution**
   - bounded parallel tasks and resource limits.
6. **Fan-in, evidence merge and conflicts**
   - alternatives, duplicate detection, contradictions and unresolved questions.
7. **Human checkpoints and decision integration**
   - ready_for_review only; human provenance for accepted results.
8. **Failure, retry, replay and resume**
   - idempotency, correlation IDs and diagnostics.
9. **Observability and audit**
   - run manifest, events, metrics, timing, costs and tool usage.
10. **Reference workflow and acceptance**
    - synthetic domain, multiple agents, conflict, human resolution and final artifacts.

## Agent roles — initial candidates

These are capability roles, not mandatory independent services:

- `domain-evidence-analyst` — extracts events, terms and questions from supplied evidence;
- `eventstorming-facilitator` — proposes session progression and detects missing categories;
- `boundary-analyst` — proposes candidate subdomains/BC boundaries and alternatives;
- `context-map-analyst` — proposes relationships, contracts and data ownership questions;
- `quality-attribute-analyst` — formulates scenarios and trade-offs;
- `team-topology-analyst` — proposes ownership and interaction implications;
- `architecture-reviewer` — identifies risks, contradictions and missing decisions;
- `evidence-synthesizer` — merges compatible claims while preserving provenance;
- `conflict-moderator` — structures alternatives for human decision without choosing silently.

One runtime may execute multiple roles. The public contract is role/capability-oriented, not provider-oriented.

## Run state model

```text
planned
→ validating_inputs
→ ready
→ running
→ waiting_for_human
→ running
→ completed
```

Failure branches:

```text
running → retryable_failure → running
running → failed → resumable
resumable → running
any active state → cancelled
```

`completed` means technical orchestration completed. It does not mean domain gate or release approval passed.

## Acceptance criteria at WP level

- [ ] EventStorming session types have explicit scopes and output contracts;
- [ ] events, commands, actors, policies, systems, hotspots and questions retain provenance;
- [ ] candidate boundaries are alternatives until human acceptance;
- [ ] every agent task is bound to scope, inputs, allowed tools and output schema;
- [ ] fan-out cannot access undeclared client or workspace data;
- [ ] fan-in preserves conflicting alternatives and does not silently last-write-win;
- [ ] automated output can become `ready_for_review`, never production `passed`;
- [ ] run state supports cancellation, retry, resume and correlation;
- [ ] replay does not duplicate managed artifacts;
- [ ] Miro sync follows project-owned projection and explicit conflict rules;
- [ ] source evidence and inference are distinguishable;
- [ ] audit report records agent roles, inputs, outputs, tool calls, timing and status without secrets;
- [ ] provider/model substitution does not change artifact contracts;
- [ ] reference example includes at least one inter-agent contradiction resolved by a human;
- [ ] package-first E2E produces valid DDDA artifacts and validation report;
- [ ] no agent performs implicit Git push, merge, release, gate approval or destructive Miro operation.

## Quality attributes

- auditability;
- explainability and provenance;
- safety and least privilege;
- resumability and idempotence;
- interoperability;
- provider portability;
- observability;
- deterministic contracts despite non-deterministic reasoning;
- human control;
- cost and resource governance.

## Risks

| Risk | Impact | Mitigation |
|---|---:|---|
| Agent output is treated as truth | High | claim types, provenance and human acceptance |
| Fan-in hides contradictions | High | explicit conflict records and no last-write-wins |
| Agent impersonates approver | High | human provenance contract from WP-08 |
| Tool permissions enable destructive actions | High | allowlists, dry-run, sandbox and explicit confirmation |
| Non-determinism creates brittle tests | High | schema/invariant tests, bounded fixtures and recorded manifests |
| Costs or execution time grow uncontrolled | Medium | budgets, limits, metrics, cancellation and batching |
| Provider lock-in leaks into artifacts | Medium | provider-neutral contracts and adapters |
| EventStorming becomes automated document extraction | High | workshop/human checkpoints and explicit session semantics |

## Dependencies

- WP-08 for human-only decisions, package-first validation, Miro governance and release lifecycle;
- WP-10 for rich source evidence and provenance, with synthetic/manual inputs usable initially;
- WP-09 for strategic context when orchestration is used at program level.

## Exit criteria

- executable EventStorming session model is validated;
- agent contract and orchestrator state model are stable;
- fan-out/fan-in, conflicts, retry and resume pass deterministic tests;
- one end-to-end synthetic example passes human review;
- no automated approval path exists;
- security, observability and cost boundaries are documented and tested;
- release package and roadmap status are updated.
