# DDDA backlog and product governance

Tato sekce je vstupním bodem pro governance backlogu, roadmapy, issues, pull requestů, release evidence a lidských rozhodnutí DDDA platformy.

## Základní dokumenty

- [Backlog governance](backlog-governance.md)
- [WP ↔ Backlog ↔ Implementation consistency](wp-backlog-consistency.md)
- [Autoritativní mapa artefaktů](authoritative-artifact-map.md)
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

Kontrakty definují:

- hierarchii GAP → Work Package → Child Issue → implementation PR;
- autoritativní umístění informací;
- Project fields a views;
- nativní Parent/Sub-issue mapping;
- dependency edges a jejich rationale;
- Roadmap date fields a pravidlo nevymýšlet TBD termíny;
- Milestone semantics;
- stavový model, priority, Ready/Done kritéria a počáteční Work Packages.

Závazný consistency invariant a povinný pre/post read-back jsou definovány v `docs/governance/wp-backlog-consistency.md` a promítnuty do PR template a backlog review checklistu.

## Základní pravidlo

```text
Issue popisuje co a proč.
Parent/Sub-issues drží skutečnou backlogovou hierarchii.
Project řídí prioritu, pořadí a operativní stav.
Dependencies říkají, co blokuje co.
Roadmap zobrazuje rozhodnutá data, ne vymyšlené termíny.
Milestone určuje cílový release.
PR realizuje konkrétní změnu a má jednoznačnou Change Request authority.
ADR vysvětluje dlouhodobé rozhodnutí.
CHANGELOG eviduje vydané změny.
Validation report dokládá technickou kvalitu.
HRDR dokládá lidské GO/NO-GO.
Roadmap dokument drží dlouhodobou produktovou vizi.
```

Pro každou aktivní implementaci musí být úplný a vzájemně konzistentní řetězec:

```text
Work Package (nebo explicitní Other)
↔ Change Request
↔ branch / Draft PR
↔ DDDA Platform Backlog Project item
```

Před i po každé strukturální backlog/WP/governance změně se provádí repository-wide read-back. Post-change mismatch count musí být `0`; jinak je technical governance PASS a doporučení Ready/merge blokováno.

Plánované změny se nezakládají jako prázdné nebo dlouhodobé draft PR. Nejprve vzniká GitHub Issue; branch a Draft PR vznikají až se zahájením implementace.
