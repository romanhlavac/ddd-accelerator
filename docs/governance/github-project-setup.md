# GitHub Project setup — DDDA Platform Backlog

## Účel

Tento dokument je administrátorský runbook pro vytvoření a údržbu GitHub Projectu, který je autoritou pro prioritu, pořadí a průběžný delivery status DDDA platformy.

## Projekt

```text
Name: DDDA Platform Backlog
Visibility: podle visibility repozitáře; preferováno public pro public repository
Owner: romanhlavac nebo budoucí DDDA organizace
Scope: pouze vývoj DDDA platformy
```

Klientské DDDA projekty se do tohoto Projectu nepřidávají.

## Povinná pole

### Status

| Hodnota | Význam |
|---|---|
| Backlog | evidováno, dosud netriagováno |
| Discovery | probíhá porozumění problému a variantám |
| Triaged | klasifikováno, ale ještě ne Ready |
| Ready | splňuje entry criteria pro implementaci |
| In progress | existuje aktivní branch / Draft PR |
| In review | implementace je připravena k technickému nebo human review |
| Blocked | nelze pokračovat bez konkrétní podmínky |
| Done | splněna Definition of Done |
| Cancelled | vědomě ukončeno bez realizace |

### Priority

```text
P0 — release/safety/data-integrity blocker
P1 — nejvyšší aktivní produktová priorita
P2 — důležitý plánovaný inkrement
P3 — dlouhodobý nebo opportunistic backlog
```

### Work Package

Počáteční hodnoty:

```text
WP-08 Platform lifecycle & project steering
WP-09 Strategy, portfolio & program lifecycle
WP-10 Enterprise ingestion
WP-11 EventStorming & multi-agent orchestration
Other
```

### Item Type

```text
GAP
Work Package
Change Request
Defect
Risk
Enabler
```

### Platform Area

Použij taxonomii:

```text
DOC
METHODOLOGY
TEMPLATE
SCHEMA
ORCHESTRATION
INGESTION
CLI
WORKSPACE-GENERATOR
EXAMPLE
TESTING
RELEASE
SECURITY-GOVERNANCE
```

Pokud jedna položka zasahuje více oblastí, pole obsahuje dominantní oblast a úplný seznam zůstává v Issue.

### Impact

```text
LOW
MEDIUM
HIGH
BREAKING
```

### Target Release

Text nebo iteration:

```text
0.1.0
0.2.0
TBD
```

Toto pole je projekce Milestone a nesmí se s ním rozcházet.

### Další pole

```text
Owner          Person
Blocked        Boolean
Human Review   Not required | Pending | PASS | FAIL | Accepted risks
Dependency     Text
```

## Pohledy

### 1. Delivery board

- layout: Board;
- columns: Status;
- sort: Priority, manual order;
- show: Issue/PR title, Priority, Work Package, Owner, Target Release.

### 2. Roadmap by Work Package

- layout: Roadmap nebo Table;
- group: Work Package;
- date/iteration: Target Release, pokud dostupné;
- filter: Status != Cancelled.

### 3. Release scope

- layout: Table;
- group: Target Release;
- filter: Target Release != TBD;
- show: Status, Priority, Human Review, Blocked.

### 4. Blocked and P0

- filter: `Blocked = true OR Priority = P0`;
- sort: Priority, updated date.

### 5. Human review queue

- filter: `Status = In review OR Human Review = Pending`;
- show: PR, exact review evidence link v Issue, owner.

### 6. Ready without owner

- filter: `Status = Ready AND Owner is empty`.

### 7. Recently completed

- filter: `Status = Done`;
- sort: recently updated descending.

## Automations

Doporučené built-in automations:

- nově přidaný Issue → Status `Backlog`;
- otevřený PR → Status `In progress`;
- PR marked ready for review → Status `In review`;
- merged PR → související implementační Issue `Done` pouze pokud je skutečně uzavřeno;
- closed Issue → Status `Done` nebo `Cancelled` podle state reason;
- reopened Issue → Status `Triaged`.

Automatizace nesmí sama nastavovat:

- Priority;
- Target Release;
- Human Review PASS;
- Work Package bez explicitního mapování;
- GO/NO-GO.

## Milestones

Počáteční milestone:

```text
DDDA 0.1.0
```

Do `DDDA 0.1.0` patří PR #8 a všechny položky, které jsou nutné pro jeho release readiness. Přesný scope se řídí Human Review a remediation plánem; issue nesmí být přidáno jen proto, že tematicky souvisí.

Pro WP-09 až WP-11 se milestone nepřiděluje, dokud není schválena cílová release strategie. V Projectu zůstává `Target Release = TBD`.

## Kontrolní checklist po založení

- [ ] Project má přesný název `DDDA Platform Backlog`;
- [ ] všechna povinná pole existují;
- [ ] hodnoty polí odpovídají tomuto dokumentu;
- [ ] existují všechny doporučené pohledy;
- [ ] automatizace nepředstírá lidské rozhodnutí;
- [ ] Issues #9–#15 a PR #8 jsou přidány pod WP-08;
- [ ] nové Work Package issues WP-09 až WP-11 jsou přidány;
- [ ] Project nepoužívá budoucí GitHub PR čísla jako stabilní roadmap ID;
- [ ] milestone `DDDA 0.1.0` obsahuje pouze schválený release scope.

## Změny konfigurace

Každá změna polí, hodnot nebo významu stavu musí být nejprve aktualizována v:

```text
config/governance/backlog-policy.yaml
```

a v tomto runbooku. Změna s dlouhodobým dopadem může vyžadovat nové nebo superseding ADR.
