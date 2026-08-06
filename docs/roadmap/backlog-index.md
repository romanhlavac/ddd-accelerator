# Roadmap Work Package and GitHub backlog index

This index maps stable roadmap identities to current GitHub Parent/Child Issues. GitHub numbers are backlog/implementation references; stable product identities remain `WP-XX`.

## Relationship semantics

- **Parent/sub-issue** = capability ownership and hierarchy, not release scope.
- **Blocked by** = direct native dependency required for completion.
- **Transitive prerequisite** = inherited dependency, not duplicated natively.
- **Consumed contract** = reused contract without automatic scheduling semantics.
- **Milestone** = release scope, not release approval.

## Governance foundation and cross-cutting work

- #16 — GitHub-native backlog governance and repository artifacts
- Draft PR #43 — governance implementation; remains Draft
- #42 — GitHub Project/Milestone administration
- #44 — direct-main write prevention and incident record
- #49 — role-based documentation information architecture (`Work Package: Other`), blocked by #16, #46 and #48

## WP-08 — Platform lifecycle & project steering

Parent Issue: #17

### Release `DDDA 0.1.0`

- PR #8 — platform lifecycle and project steering
- #9 — Human Review and HRDR; final record is a promotion criterion
- #10 — release documentation/auth/changelog — **Done**
- #11 — legacy workspace compatibility regression — **Done**
- #12 — online Miro acceptance traceability
- #13 — human-only gate decisions — **Done**
- #14 — Miro steering-board redesign
- #15 — Human Review remediation execution plan

### Future WP-08 evolution

- #45 — GitHub Pages Artifact Registry dashboard; child of #17, `Target Release: TBD`, excluded from `DDDA 0.1.0`

Critical path:

```text
#13 DONE → #14 → #12 → deterministic PASS → frozen SHA
→ final human visual acceptance → #9 HRDR → explicit release decision
```

## WP-09 — Strategy, portfolio & program lifecycle

Parent Issue: #18

| Issue | Capability |
|---|---|
| #21 | program lifecycle P0–P10 and human gate contract |
| #22 | strategy intake, purpose, outcomes and value chain |
| #23 | Wardley Mapping artifact and workflow |
| #24 | portfolio prioritization and investment decision records |
| #25 | strategy/capability/subdomain/BC/system/team traceability |
| #50 | program roadmap, increments, sequencing and benefits realization |
| #26 | program Miro Control Center and roadmap projection |
| #51 | reference program and package-first strategic acceptance |

Dependency order:

```text
#21 + #22 → #23
#22 + #23 → #24
#21 + #24 → #25
#25 → #50 → #26 → #51
```

Scope boundaries:

- #25 owns typed graph/impact semantics;
- #50 owns roadmap and benefits lifecycle;
- #26 owns Miro projection;
- #51 owns final cross-capability acceptance.

## WP-10 — Enterprise ingestion

Parent Issue: #19

| Issue | Capability |
|---|---|
| #27 | enterprise manifest, source identity, normalized evidence, Markdown and YAML registration |
| #31 | central security, privacy, classification, redaction and path isolation |
| #28 | Office adapters for DOCX/XLSX/PPTX |
| #29 | PDF ingestion and explicit OCR fallback |
| #30 | ArchiMate supported-subset ingestion and coverage report |
| #32 | incremental lifecycle, tombstones, resume and impact traceability |
| #33 | synthetic enterprise corpus and package-first acceptance |

Dependency order:

```text
#27 → #31
#27 + #31 → #28, #29, #30, #32
#28 + #29 + #30 + #31 + #32 → #33
```

#27 evolves the PR #8 minimal ingestion baseline. #31–#33 must not create parallel source/evidence/security contracts.

## WP-11 — EventStorming & multi-agent orchestration

Parent Issue: #20

| Issue | Capability |
|---|---|
| #34 | executable EventStorming session model |
| #35 | EventStorming-specific Miro/Git round-trip over the PR #8 generic runtime |
| #36 | versioned agent contract and capability catalog, including PR #8 baseline migration |
| #37 | orchestrator state machine and bounded fan-out |
| #38 | fan-in, alternatives and conflict records |
| #39 | human checkpoints, authorization and safety boundaries |
| #40 | failure/retry/replay/resume and observability/cost governance |
| #47 | evidence-to-workshop integration-only orchestration |
| #41 | synthetic multi-agent/EventStorming package-first E2E |
| #48 | DDD Starter phase rules, COTS/BC and tactical-design cookbooks |
| #46 | end-to-end first-user target/as-built guide |

Dependency order:

```text
#34 → #35
#36 → #37 → #38
#36 + #37 + #38 → #39
#37 + #38 + #39 → #40
#27 + #31 + #32 + #34–#40 → #47
#35 + #40 + #47 → #41
#47 + #41 + #48 → #46
```

Ownership rules:

- WP-10 owns source ingestion and registered evidence.
- #34 is the only EventStorming semantic session/item owner.
- #35 extends, but does not duplicate, the PR #8 generic Miro runtime.
- #36 resolves the preliminary PR #8 agent/capability schemas through version compatibility or migration.
- #47 composes existing contracts; it owns no duplicate subsystem.
- #48 owns canonical phase terminology used by #46.
- #46 closes only after #47, #41 and #48 are verified.

## Cross-cutting documentation

#49 is intentionally not a WP-11 child. It reorganizes documentation across developer, architect/user and administrator perspectives after stable content exists:

```text
#16 governance/admin baseline
+ #46 first-user guide
+ #48 methodology terminology
→ #49 role-based documentation information architecture
```

Broad path moves additionally require PR #8 to be merged or otherwise stably resolved. #49 does not authorize changes to, rebase of or merge of PR #43.

## Update rule

Update this index when:

- Parent/Child Issue is created, split, moved, superseded or closed;
- direct dependency or capability ownership changes;
- implementation branch/Draft PR begins;
- target release is explicitly approved;
- WP reaches `done`, `cancelled` or `superseded`;
- roadmap scope changes.

Operational priority, dates and ownership remain authoritative in GitHub Project. Human Review PASS, HRDR and GO/NO-GO remain explicit human decisions.
