# WP-11 — EventStorming & multi-agent orchestration

## Outcome

```text
WP-10 registered evidence
→ analytical capabilities
→ executable EventStorming session
→ EventStorming-specific Miro workshop projection
→ governed round-trip
→ consolidated artifacts and Control Center
→ explicit human decision
```

## Baseline compatibility

WP-08 / PR #8 already owns:

- generic project-owned Miro runtime, mapping, sync state and idempotence;
- human-only gate semantics and validation evidence;
- preliminary agent/capability schemas;
- G1–G8 methodology/cookbooks.

WP-11 must extend/version these baselines, not create parallel sources of truth:

- #35 adds EventStorming-specific adapters/layout semantics over the generic Miro runtime;
- #36 evolves the preliminary agent contracts with compatibility/deprecation rules;
- #48 remediates methodology gaps over the stable PR #8 baseline.

## Capability ownership

| Issue | Owned capability |
|---|---|
| #34 | executable EventStorming session/item model |
| #35 | EventStorming-specific Miro seed, layout and round-trip adapters |
| #36 | versioned agent/capability contracts and catalog |
| #37 | orchestrator state machine and bounded fan-out |
| #38 | fan-in, alternatives, deduplication and conflict records |
| #39 | human checkpoints, authorization and safety boundaries |
| #40 | failure, retry, replay, resume, observability and cost governance |
| #47 | integration-only evidence-to-workshop orchestration |
| #41 | synthetic package-first multi-agent/EventStorming E2E |
| #48 | DDD Starter phase rules and cookbooks |
| #46 | first-user target/as-built guide |

WP-10 #27–#33 remain the sole owners of source/evidence inception. #47 composes existing contracts and creates no duplicate model, renderer, agent runtime or datastore.

## Dependency order

```text
#34 → #35
#36 → #37 → #38
#36 + #37 + #38 → #39
#37 + #38 + #39 → #40
#27 + #31 + #32 + #34–#40 → #47
#35 + #40 + #47 → #41
#47 + #41 + #48 → final as-built closure #46
```

#48 may progress after a stable PR #8 methodology baseline. #46 may be drafted earlier as a target operating model, but final closure requires #47, #41 and #48.

## Authority and ownership principles

1. Source, evidence, interpretation, candidate artifact and human decision are distinct authority levels.
2. #34 is the only EventStorming semantic session/item model.
3. #35 reuses the generic PR #8 Miro runtime; no second sync engine or mapping store.
4. #36 resolves the PR #8 preliminary agent baseline through explicit version compatibility/migration.
5. Git/YAML owns semantic identity, provenance and lifecycle; Miro owns collaborative layout.
6. Fan-in preserves alternatives, contradictions and incomplete status.
7. Automation may prepare `ready_for_review`, never human `passed`.
8. No agent implicitly commits, pushes, merges, releases or performs destructive Miro actions.
9. #48 owns the canonical Discover/Connect, COTS/BC and tactical-design phase rules used by #46.

## In scope

- Big Picture, Process and Design-Level EventStorming sessions;
- session charter, states, modeled items, history and aftermath;
- evidence-backed hypotheses and candidate boundaries;
- EventStorming-specific Miro templates and governed round-trip;
- provider-neutral agent contracts, bounded fan-out/fan-in and conflicts;
- least-privilege tools and human checkpoints;
- cancellation, retry, replay, resume and audit/metrics;
- WP-10 evidence-to-session hand-off through #47;
- DDD Starter methodology gap remediation through #48;
- package-first reference workflow and first-user guide.

## Out of scope

- source catalog, document parsing or evidence registry — WP-10;
- second generic Miro runtime;
- autonomous business/domain/architecture/release approval;
- unrestricted Git, Miro or network writes;
- hidden chain-of-thought as evidence;
- generic enterprise agent platform;
- program/portfolio semantics — WP-09.

## Acceptance criteria

- [ ] evidence is consumed through WP-10 contracts, not copied into a second model;
- [ ] analytical outputs materialize only through #34;
- [ ] #35 is compatible with the generic PR #8 Miro contracts;
- [ ] #36 has explicit PR #8 schema compatibility/deprecation evidence;
- [ ] #47 contains only orchestration and identity/provenance hand-offs;
- [ ] manual layout survives semantic refresh;
- [ ] new Miro items require explicit PromoteNew;
- [ ] semantic conflicts never use last-write-wins;
- [ ] agent tasks have explicit scope, tools, budgets and result schema;
- [ ] fan-in retains contradictions and incomplete child-task status;
- [ ] retry/replay/resume creates no duplicate managed artifacts;
- [ ] automation cannot create human approval;
- [ ] #48 and #46 use one canonical DDD Starter terminology;
- [ ] package-first E2E uses synthetic evidence and exact-SHA human acceptance;
- [ ] no implicit push, merge, release or destructive Miro action exists.

## Exit criteria

- #34–#40 contracts/runtime are stable and compatible with PR #8 baselines;
- #47 proves the end-to-end hand-off without duplicate capabilities;
- #41 proves package-first failure/resume, conflict, Miro and human acceptance;
- #48 methodology is reviewed and consistent;
- #46 matches as-built behavior;
- native hierarchy/dependencies and roadmap are current;
- no automated approval path remains.
