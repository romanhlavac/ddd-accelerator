# DDDA backlog and product governance

Tato sekce je vstupním bodem pro governance backlogu, roadmapy, issues, pull requestů, release evidence a lidských rozhodnutí DDDA platformy.

## Základní dokumenty

- [Backlog governance](backlog-governance.md)
- [WP ↔ Backlog ↔ Delivery consistency](wp-backlog-consistency.md)
- [Autoritativní mapa artefaktů](authoritative-artifact-map.md)
- [Governance characterization v1](governance-characterization-v1.md)
- [Scenario-first governance methodology v2](governance-methodology-v2.md)
- [GitHub Project setup](github-project-setup.md)
- [Triage a delivery runbook](triage-and-delivery-runbook.md)
- [Status a relationship model](status-and-relationship-model.md)
- [Periodický backlog review checklist](backlog-review-checklist.md)
- [Scope review matrix template](review-matrix-template.md)
- [Governance templates reference](templates-reference.md)
- [GitHub administration checklist](project-administration-checklist.md)
- [Implementation notes pro bezpečný rollout kolem PR #8](implementation-notes.md)
- [Produktová roadmapa](../roadmap/README.md)
- [Roadmap ↔ GitHub backlog index](../roadmap/backlog-index.md)
- [ADR 0003 — GitHub-native backlog governance](../adr/0003-github-native-backlog-governance.md)

## Machine-readable contracts

```text
config/governance/backlog-policy.yaml
config/governance/github-bootstrap.json
```

Backlog authority je GitHub Issue + native WP hierarchy. GitHub Project V2 má dvě oddělené projekce: planning pro Work Packages/Change Requests a delivery pro otevřené implementační PR. PR je povinný delivery item navázaný na jeden primární Change Request; nikdy se tím nestává druhým Change Requestem.

Povinný consistency model:

```text
Work Package (nebo explicitní Other)
↔ Change Request Issue
↔ Project planning item

Change Request Issue
↔ implementation branch / Draft PR
↔ Project delivery item
```

Před i po strukturální backlog/WP/governance změně se provádí repository-wide read-back. Post-change mismatch count musí být `0`; jinak je technical governance PASS a doporučení Ready/merge blokováno.

Release safety se rozhoduje podle exact candidate identity, Git/SHA/package, canonical Issues/PRs/Milestones/dependencies, lidských rozhodnutí, explicitní authorization a required CI. Project je pouze projekce a jeho health není release authority. Mismatches se klasifikují jako `SAFETY_BLOCKING`, `GOVERNANCE_PROJECTION` nebo `PRESENTATION`; Project/backlog mutation stále vyžaduje po mutaci `remaining_mismatches = 0`.

Detailní pravidla a výjimky jsou v `docs/governance/wp-backlog-consistency.md`.
