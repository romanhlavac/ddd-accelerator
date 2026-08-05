# WP-11 — EventStorming & multi-agent orchestration

## Outcome

```text
WP-10 registered evidence
→ analytical capabilities
→ #34 EventStorming session
→ #35 Miro workshop
→ governed round-trip
→ Control Center and artifacts
→ human decision
```

## Ownership

- #34 — EventStorming session/item contracts
- #35 — Miro seeding, mapping, layout ownership and round-trip
- #36 — agent/capability contracts
- #37 — bounded orchestration/fan-out
- #38 — fan-in, alternatives and conflicts
- #39 — human checkpoints and authorization
- #40 — failure/retry/replay/resume and observability
- #47 — integration-only evidence-to-workshop orchestration
- #41 — final synthetic package-first E2E
- #46 — first-user target/as-built documentation

WP-10 #27–#33 remain the sole owners of ingestion, normalized/Markdown evidence and YAML evidence registration. #47 composes existing contracts and creates no parallel model.

## Dependency order

```text
#34 → #35
#36 → #37 → #38
#36/#37/#38 → #39
#37/#38/#39 → #40
#27/#31/#32 + #34–#40 → #47
#35/#40/#47 → #41
#47/#41 → final as-built closure #46
```

## Acceptance and exit

Analytical output materializes only through #34 and Miro round-trip only through #35. Manual layout survives refresh; new Miro items require explicit promotion; semantic conflicts never use last-write-wins. Evidence is traceable through task, session and workshop delta. Automation may create ready-for-review, never human passed. Exit requires #47 integration without duplicate models, #41 package-first and human acceptance, #46 as-built validation, and current native hierarchy/dependencies.
