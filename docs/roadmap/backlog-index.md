# Roadmap Work Package and GitHub backlog index

This index maps stable roadmap identities to current GitHub Parent and Child Issues. GitHub numbers are implementation/backlog references; the stable roadmap identity remains `WP-XX`.

## Governance foundation

- Change Request #16 — GitHub-native backlog governance and repository artifacts
- Draft PR #43 — governance implementation
- Administrative Issue #42 — create GitHub Project and Milestone

## WP-08 — Platform lifecycle & project steering

Parent Issue: #17

Implementation and remediation:

- PR #8 — platform lifecycle and project steering
- #9 — Human Review and HRDR
- #10 — release documentation, authentication and changelog
- #11 — legacy workspace compatibility regression
- #12 — online Miro acceptance traceability
- #13 — human-only gate decisions
- #14 — Miro steering-board redesign
- #15 — Human Review remediation execution plan

## WP-09 — Strategy, portfolio & program lifecycle

Parent Issue: #18

Child Change Requests:

- #21 — program lifecycle P0–P10 and human gate contract
- #22 — strategy intake, purpose, outcomes and value-chain model
- #23 — Wardley Mapping artifact, schema and workflow
- #24 — portfolio prioritization and investment decision records
- #25 — strategy/capability/subdomain/BC/team traceability and program roadmap
- #26 — program Miro Control Center and reference acceptance

## WP-10 — Enterprise ingestion

Parent Issue: #19

Child Change Requests:

- #27 — enterprise manifest, normalized evidence, Markdown materialization and YAML registration
- #28 — Office ingestion adapters for DOCX, XLSX and PPTX
- #29 — PDF ingestion and explicit OCR fallback
- #30 — ArchiMate ingestion and supported-subset coverage report
- #31 — ingestion security, privacy, classification and path isolation
- #32 — incremental ingestion, tombstones, resume and source-to-artifact traceability
- #33 — synthetic enterprise corpus and package-first acceptance

## WP-11 — EventStorming & multi-agent orchestration

Parent Issue: #20

Child Change Requests:

- #34 — executable EventStorming session model
- #35 — EventStorming Miro/Git round-trip and workshop artifacts
- #36 — agent contract v1 and capability catalog
- #37 — orchestrator state machine and bounded fan-out
- #38 — fan-in evidence merge, alternatives and conflict records
- #39 — human checkpoints, authorization and safety boundaries
- #40 — failure/timeout/retry/replay/resume and observability/cost governance
- #47 — evidence-to-workshop integration orchestration
- #41 — synthetic multi-agent reference workflow and package-first acceptance
- #46 — end-to-end first-user target/as-built documentation

Issues #46 and #47 are native sub-issues of #20 and are included in the linked GitHub Project. Their `Blocked by` relationships are versioned in the governance configuration and materialized in GitHub.

## WP-10 → WP-11 authority hand-off

```text
#27–#33 registered source evidence
→ #36–#40 analytical and orchestration capabilities
→ #34 EventStorming session artifacts
→ #35 Miro workshop seed and governed round-trip
→ #47 cross-Work-Package integration
→ #41 package-first reference acceptance
→ #46 as-built first-user documentation
```

Ownership rules:

- WP-10 owns source ingestion, normalized evidence, Markdown evidence and YAML evidence registration.
- #34 is the only EventStorming session and item contract owner.
- #35 is the only EventStorming Miro seed, mapping, layout-ownership and synchronization owner.
- #47 composes existing contracts; it does not create a second ingestion, artifact, agent or Miro subsystem.
- #46 describes the complete target/as-built user workflow and closes only after #47 and #41 are verified.

## Update rule

Update this index when:

- a Parent or Child Issue is created, split, superseded or closed;
- a delivery branch/Draft PR begins;
- an Issue is moved to another Work Package;
- a Work Package reaches `done`, `cancelled` or `superseded`;
- roadmap scope changes.

Operational priority, status and target release remain authoritative in GitHub Project/Milestone after #42 is completed.
