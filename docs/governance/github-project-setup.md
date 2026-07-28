# GitHub Project setup — DDDA Platform Backlog

## Účel

Tento dokument je administrátorský runbook pro vytvoření a údržbu GitHub Projectu, který je autoritou pro prioritu, pořadí a průběžný delivery status DDDA platformy.

GitHub Project není autoritou pro detailní požadavek ani architektonické rozhodnutí. Detail zůstává v Issues, ADR, PR, validation reportu a HRDR podle autoritativní mapy artefaktů.

## Projekt

```text
Name: DDDA Platform Backlog
Visibility: podle visibility repozitáře; preferováno public pro public repository
Owner: romanhlavac nebo budoucí DDDA organizace
Scope: pouze vývoj DDDA platformy
```

Klientské DDDA projekty se do tohoto Projectu nepřidávají.

## Povinná vlastní pole

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

### Start date a Target date

```text
Start date   Date
Target date  Date
```

Používají se pro Roadmap layout.

Pravidla:

- datum se zadává pouze tehdy, když existuje skutečné plánovací rozhodnutí;
- přesná data se nevymýšlejí pouze kvůli vizualizaci;
- backlog item bez termínu může zůstat na Roadmapě jako unscheduled;
- změna termínu neznamená automaticky změnu Target Release;
- dependency vztah je logická podmínka, datum je plánovací projekce.

### Outcome summary

```text
Outcome summary  Text
```

Jednořádkové shrnutí outcome, zejména pro Parent Work Package. Plný popis zůstává v těle Parent Issue.

Počáteční hodnoty:

```text
WP-08: Reproducible platform lifecycle, G1-G8 steering and human-controlled release governance.
WP-09: Strategy, Wardley, portfolio and P0-P10 program governance linked to DDD and teams.
WP-10: Secure and auditable Office, PDF and ArchiMate ingestion with source provenance.
WP-11: Executable EventStorming and bounded multi-agent workflows with explicit human checkpoints.
```

### Další pole

```text
Owner          Person
Blocked        Boolean
Human Review   Not required | Pending | PASS | FAIL | Accepted risks
Dependency     Text
```

Pole `Dependency` je čitelná projekce nebo doplňující popis. Pokud GitHub podporuje nativní `Blocked by` / `Blocking`, používají se jako primární operativní dependency vazby.

## Povinná systémová pole

V relevantních Project views zapni:

```text
Parent issue
Sub-issue progress
Milestone
Linked pull requests
```

Význam:

- `Parent issue` — nativní hierarchie Child Issue → Work Package;
- `Sub-issue progress` — agregovaný postup Parent Work Package;
- `Milestone` — skutečný release scope;
- `Linked pull requests` — aktuální implementace.

Prefix `[WP-09]` v názvu zůstává navigační pomůcka, ale nesmí být jediným nositelem hierarchie.

## Nativní Parent/Sub-issue hierarchie

Pokud jsou GitHub Sub-issues dostupné, vytvoř tyto vazby:

```text
WP-08 #17
├── #9
├── #10
├── #11
├── #12
├── #13
├── #14
└── #15

WP-09 #18
├── #21
├── #22
├── #23
├── #24
├── #25
└── #26

WP-10 #19
├── #27
├── #28
├── #29
├── #30
├── #31
├── #32
└── #33

WP-11 #20
├── #34
├── #35
├── #36
├── #37
├── #38
├── #39
├── #40
└── #41
```

PR #8 ani Draft PR #43 nejsou Sub-issues. Vazba implementačního PR se zobrazuje přes Issue reference a `Linked pull requests`.

Pokud nativní Sub-issues nejsou dostupné, zachovej checklist v Parent Issue a textové odkazy, ale administrativní stav označ jako `partial`.

## Dependency model

Dependency říká, co musí být dokončeno nebo stabilizováno před jinou položkou. Neurčuje automaticky prioritu, vlastníka ani datum.

Používej nativní `Blocked by` / `Blocking`, pokud je GitHub nabízí. Pole `Dependency` a Issue body drží čitelný rationale.

### WP-08 critical path

```text
#13 human-only gate semantics
→ #14 Miro board redesign
→ #12 Miro evidence contract
→ #11 legacy compatibility evidence
→ #10 release documentation/auth/changelog consistency
→ #9 final Human Review / HRDR
```

Issue #15 zůstává autoritativní execution plan a může obsahovat detailnější pořadí deterministic suites, SHA freeze, final visual acceptance a promotion dry-run.

### WP-09

```text
#21 P0–P10 lifecycle ─┐
                      ├─→ #23 Wardley Mapping
#22 strategy intake ──┘

#22 + #23 → #24 portfolio prioritization
#21 + #24 → #25 strategy-domain-team traceability
#25 → #26 program Miro Control Center and acceptance
```

#21 a #22 mohou začít paralelně. Finální integrace #23–#26 respektuje uvedené dependency.

### WP-10

```text
#27 ingestion core
  ├─→ #28 Office
  ├─→ #29 PDF
  ├─→ #30 ArchiMate
  └─→ #32 incremental lifecycle

#31 security/isolation
  ├─→ completion of #28
  ├─→ completion of #29
  ├─→ completion of #30
  └─→ #33 final acceptance

#28 + #29 + #30 + #31 + #32 → #33
```

#31 je průřezová práce a může začít současně s #27, ale blokuje dokončení adaptérů a finální acceptance.

### WP-11

```text
#34 EventStorming session model → #35 Miro/Git round-trip

#36 agent contracts → #37 bounded orchestrator → #38 fan-in/conflicts

#36 + #37 + #38 → #39 human checkpoints and authorization

#37 + #38 + #39 → #40 failure/retry/resume/observability

#35 + #40 → #41 package-first multi-agent E2E
```

Nativní dependency hrany a jejich rationale jsou rovněž verzovány v `config/governance/backlog-policy.yaml`.

## Pohledy

### 1. Work Packages

- layout: Table;
- filter: `Item Type = Work Package`;
- columns: Title, Outcome summary, Status, Priority, Sub-issue progress, Start date, Target date, Target Release, Human Review;
- sort: Priority, manual order.

Toto je hlavní manažerský přehled roadmap bloků.

### 2. WP hierarchy

- layout: Table;
- group: Parent issue;
- columns: Title, Parent issue, Status, Priority, Blocked, Dependency, Target Release, Linked pull requests;
- filter: Item Type != Work Package, pokud je žádoucí zobrazit jen děti.

Tento pohled zobrazuje skutečné WP → Child Issues, nikoli pouze prefixy názvu.

### 3. Delivery board

- layout: Board;
- columns: Status;
- sort: Priority, manual order;
- show: Issue/PR title, Priority, Work Package, Owner, Target Release, Blocked.

### 4. Roadmap by Work Package

- layout: Roadmap;
- start date field: Start date;
- target date field: Target date;
- group: Work Package;
- markers: Milestones;
- filter: Status != Cancelled;
- unscheduled items: visible;
- recommended zoom: Quarter nebo Year.

Roadmap ukazuje plánovaný čas. Nativní dependencies ukazují logickou posloupnost.

### 5. Release scope

- layout: Table;
- group: Milestone, případně Target Release jako podpůrná projekce;
- filter: Target Release != TBD nebo Milestone is not empty;
- show: Status, Priority, Work Package, Human Review, Blocked, Linked pull requests.

### 6. Blocked and P0

- filter: `Blocked = true OR Priority = P0`;
- sort: Priority, updated date;
- show: Parent issue, Dependency, Owner, Target Release.

### 7. Human review queue

- filter: `Status = In review OR Human Review = Pending`;
- show: PR, Linked pull requests, exact review evidence link v Issue, owner.

### 8. Ready without owner

- filter: `Status = Ready AND Owner is empty`.

### 9. Recently completed

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
- Target Release nebo Milestone;
- Start date nebo Target date;
- Human Review PASS;
- Work Package nebo Parent issue bez explicitního mapování;
- dependency hrany bez schváleného kontraktu;
- GO/NO-GO.

## Milestones

Počáteční milestone:

```text
DDDA 0.1.0
```

Do `DDDA 0.1.0` patří PR #8 a pouze položky nutné pro jeho release readiness. Přesný scope se řídí Human Review a remediation plánem; Issue nesmí být přidáno jen proto, že tematicky souvisí.

Parent Work Package #17 se standardně do milestone nepřidává, pokud by tím zkresloval completion progress. Milestone má obsahovat implementační Issues a PR tvořící skutečný release scope.

Pro WP-09 až WP-11 se milestone nepřiděluje, dokud není schválena cílová release strategie. V Projectu zůstává `Target Release = TBD` a data mohou zůstat prázdná.

## Počáteční Project hodnoty

### WP-08

```text
Status: Blocked
Target Release: 0.1.0
Human Review: FAIL nebo Pending podle aktuálního authoritative review state
Start date: podle skutečné historie pouze pokud je rozhodnuto jej evidovat
Target date: TBD / prázdné, dokud není release termín rozhodnut
```

### WP-09 až WP-11

```text
Status: Backlog
Target Release: TBD
Start date: prázdné
Target date: prázdné
Human Review: Not required
Priority: rozhodnout v Project triage; nevymýšlet automaticky
```

## Kontrolní checklist po založení

- [ ] Project má přesný název `DDDA Platform Backlog`;
- [ ] všechna vlastní pole a jejich přesné hodnoty existují;
- [ ] `Start date`, `Target date` a `Outcome summary` existují;
- [ ] systémová pole Parent issue, Sub-issue progress, Milestone a Linked pull requests jsou zobrazena v relevantních views;
- [ ] existují Work Packages a WP hierarchy views;
- [ ] existuje Delivery board, Roadmap, Release scope a ostatní definované views;
- [ ] Roadmap používá Start date/Target date a zobrazuje Milestone markers;
- [ ] přesná data nebyla vymyšlena pro TBD backlog;
- [ ] native Sub-issue vazby odpovídají mapování #17–#20 → #9–#41;
- [ ] native Blocked by / Blocking vazby odpovídají dependency contractu;
- [ ] prefixy názvu nejsou jediným nositelem hierarchie;
- [ ] automatizace nepředstírá lidské rozhodnutí ani nevymýšlí priority/termíny;
- [ ] PR #8, Issues #9–#15, #16–#42, Draft PR #43 a governance defect #44 jsou podle relevance přidány;
- [ ] Project nepoužívá budoucí GitHub PR čísla jako stabilní roadmap ID;
- [ ] Milestone `DDDA 0.1.0` obsahuje pouze schválený release scope;
- [ ] WP-09 až WP-11 zůstávají bez milestone a s Target Release TBD;
- [ ] Parent WP nejsou započítány do Milestone progress, pokud by docházelo k dvojímu započtení;
- [ ] screenshoty nebo review komentář dokládají fields, views, hierarchy, dependencies a milestone scope.

## Změny konfigurace

Každá změna polí, hodnot, hierarchy, dependency semantics nebo významu stavu musí být nejprve aktualizována v:

```text
config/governance/backlog-policy.yaml
```

a v tomto runbooku. Změna s dlouhodobým dopadem může vyžadovat nové nebo superseding ADR.
