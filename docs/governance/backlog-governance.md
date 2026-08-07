# GitHub-native backlog governance DDDA platformy

## 1. Účel

Tento dokument definuje řízení produktového backlogu DDDA platformy od nalezeného GAP přes Work Package a implementační Issue až po PR, release a auditovatelnou lidskou release decision.

Backlog governance se týká vývoje DDDA platformy jako verzovaného produktu. Není to lifecycle klientského DDDA projektu ani náhrada metodických gatů G1–G8.

## 2. Základní model

```text
Idea / GAP
→ GitHub Issue
→ Parent Work Package
→ Child Issue / delivery slice
→ prioritizace v GitHub Project
→ přiřazení k Milestone
→ Ready
→ feature/fix/docs branch
→ Draft PR
→ implementace + testy + docs
→ CI + validate-pr
→ human review + HRDR
→ promote-pr
→ merge
→ release package + validation report
→ tag / release evidence
```

Plánovaný PR není backlogový artefakt. Draft PR se zakládá až po zahájení implementace a existenci branch s konkrétní změnou.

## 3. Backlogové úrovně

### 3.1 Idea / GAP Issue

Používá se pro nově nalezenou potřebu, problém nebo mezeru v platformních schopnostech.

Minimální obsah:

- původ a evidence GAP;
- problém a dopad;
- očekávaná platformní hodnota;
- prvotní in scope / out of scope;
- předpoklady a otevřené otázky;
- návrh dalšího kroku: reject, discovery, začlenění do WP nebo samostatný Change Request.

GAP Issue nemusí mít finální acceptance criteria. Musí ale být dostatečně konkrétní pro triage.

### 3.2 Parent Issue / Work Package

Work Package je velký outcome-oriented roadmap blok. Má stabilní interní identifikátor `WP-XX`, nezávislý na GitHub čísle Issue nebo budoucího PR.

Příklad:

```text
WP-09 — Strategy, Portfolio & Program Lifecycle
```

Work Package obsahuje:

- goal a desired outcome;
- problem/GAP;
- business a platform value;
- in scope a out of scope;
- platform boundaries;
- quality attributes a constraints;
- závislosti;
- delivery slices;
- acceptance criteria na úrovni WP;
- risks a mitigations;
- exit criteria;
- target release pouze pokud je rozhodnutý.

Work Package se neuzavírá dokončením jednoho PR, pokud nebyla splněna všechna exit criteria.

### 3.3 Child Issue / Change Request

Child Issue je samostatně implementovatelný delivery slice. Má být dostatečně malý pro jednoznačný review a dostatečně úplný pro vytvoření jednoho nebo malého počtu koherentních PR.

Povinný obsah:

- parent WP;
- Goal;
- Problem;
- In scope;
- Out of scope;
- Classification podle DDDA platform areas;
- Impact;
- Migration impact;
- Acceptance criteria;
- Required repository changes;
- Required tests;
- Dependencies;
- Risks;
- Definition of Done.

Jeden Child Issue může být realizován více PR pouze tehdy, pokud je dělení explicitní a každý PR má vlastní acceptance boundary.

### 3.4 Branch + Draft PR

Branch a Draft PR vznikají až při skutečném zahájení implementace.

Doporučené názvy:

```text
feature/<issue>-<short-name>
fix/<issue>-<short-name>
docs/<issue>-<short-name>
release/<version>
```

PR musí používat:

```markdown
Implements #<issue>
```

nebo při úplném uzavření Issue:

```markdown
Closes #<issue>
```

PR body musí popsat skutečný diff, ne kopírovat dlouhodobou roadmapu. Scope review porovnává parent WP, child issue, changed files, changelog a validation report.

## 4. GitHub Project

Doporučený projekt:

```text
DDDA Platform Backlog
```

### 4.1 Povinná pole

| Pole | Typ | Hodnoty / pravidla |
|---|---|---|
| Status | single select | Backlog, Discovery, Triaged, Ready, In progress, In review, Blocked, Done, Cancelled |
| Priority | single select | P0, P1, P2, P3 |
| Work Package | single select | WP-08, WP-09, WP-10, WP-11, Other |
| Item Type | single select | GAP, Work Package, Change Request, Defect, Risk, Enabler |
| Platform Area | single select nebo text | taxonomy z DDDA Platform Development Skill |
| Impact | single select | LOW, MEDIUM, HIGH, BREAKING |
| Target Release | text nebo iteration | X.Y.Z nebo TBD |
| Owner | assignee/person | konkrétní odpovědnost |
| Blocked | boolean | ano/ne; důvod zůstává v Issue |
| Human Review | single select | Not required, Pending, PASS, FAIL, Accepted risks |
| Dependency | text | blocking issue/PR/WP |

`Blocked` je samostatná vlastnost. Item může být `In progress` a současně blokovaný. Pokud GitHub Project nepodporuje současnou reprezentaci přehledně, používej Status `Blocked` a udržuj předchozí stav v Issue komentáři.

### 4.2 Priority

- `P0` — bezpečnostní, release nebo data-integrity blocker; práce má přednost před plánovaným delivery;
- `P1` — nejvyšší produktová priorita pro nejbližší release nebo kritickou capability;
- `P2` — důležitý plánovaný inkrement bez bezprostředního blockeru;
- `P3` — opportunistic, dlouhodobý nebo nízce naléhavý backlog.

Priorita není severity. Defekt může mít severity RED, ale jeho delivery priority se stále explicitně určuje.

### 4.3 Doporučené pohledy

1. **Delivery board** — sloupce podle Status.
2. **Roadmap by Work Package** — seskupení podle WP a Target Release.
3. **Release scope** — seskupení podle Milestone/Target Release.
4. **Blocked and risks** — filtr `Blocked = true` nebo P0.
5. **Human review queue** — `Status = In review` nebo `Human Review = Pending`.
6. **Unassigned Ready** — položky `Ready` bez Ownera.
7. **Recently done** — uzavřené položky posledních 30 dnů.

## 5. Milestones a release planning

Milestone reprezentuje konkrétní cílový release, například:

```text
DDDA 0.1.0
```

Do milestone patří pouze issues a PR, jejichž dokončení je součástí release scope. Work Package může přesahovat více milestone.

Pravidla:

- neznámá cílová verze = žádný milestone a `Target Release: TBD`;
- release blocker patří do stejného milestone jako blokovaný release;
- scope se mění explicitním rozhodnutím, ne pouze přesunutím Project pole;
- milestone se uzavírá až po vytvoření validovaného release state;
- `CHANGELOG`, promotion parametr a tag musí odpovídat stejné verzi.

## 6. Stavový model backlogu

```text
Backlog
→ Discovery
→ Triaged
→ Ready
→ In progress
→ In review
→ Done
```

Vedlejší přechody:

```text
libovolný aktivní stav → Blocked
Blocked → předchozí aktivní stav
Backlog/Discovery/Triaged → Cancelled
Done → reopened pouze novým explicitním rozhodnutím
```

### Entry criteria pro Ready

- Goal a Problem jsou jednoznačné;
- In scope / Out of scope jsou vymezené;
- acceptance criteria jsou testovatelná;
- klasifikace, impact a migration impact jsou určeny;
- hlavní dependencies jsou známé;
- není známý nevyřešený produktový konflikt;
- owner nebo plán převzetí je známý.

### Entry criteria pro In progress

- issue je Ready nebo je explicitně dokumentována urgentní výjimka;
- existuje branch;
- vznikl Draft PR nebo je vytvořen bezprostředně po prvním koherentním commitu;
- žádná práce neprobíhá přímo na `main`.

### Exit criteria pro Done

- acceptance criteria jsou pokryta evidencí;
- relevantní PR je mergovaný;
- CI a požadovaný validation report jsou PASS;
- docs, ADR, changelog a migration note jsou aktualizovány podle dopadu;
- Human Review/HRDR je dokončen, pokud je požadován;
- release-specific item je zahrnut v validovaném release state;
- parent WP a roadmap jsou aktualizovány.

## 7. Governance změn scope

### Scope expansion

Nový požadavek během implementace se posuzuje jako:

- clarification — nemění outcome ani acceptance boundary;
- in-scope elaboration — doplňuje detail a aktualizuje Issue;
- scope expansion — přidává novou capability nebo významný risk;
- separate follow-up — samostatné Child Issue;
- scope creep — neodsouhlasená změna mimo In scope.

Scope expansion vyžaduje aktualizaci Issue a nové impact analysis. U HIGH/BREAKING změny se zvažuje samostatný PR.

### Scope review před merge

Review porovnává:

1. Goal;
2. In scope;
3. Out of scope;
4. acceptance criteria;
5. changed files;
6. CHANGELOG;
7. validation report pro current SHA;
8. skutečné runtime a dokumentační chování.

Výsledek každého požadavku:

- `covered`;
- `partial`;
- `missing`;
- `scope creep`.

## 8. ADR, changelog a migration

ADR je povinné pro dlouhodobé dopady na:

- platform architecture;
- workspace layout;
- artifact contracts;
- orchestration a gate semantics;
- ingestion model;
- release lifecycle;
- security/isolation;
- external dependencies;
- compatibility policy.

CHANGELOG:

- eviduje pouze dodané nebo k vydání připravené změny;
- neobsahuje vzdálený backlog;
- odkazuje na relevantní issue/PR podle potřeby;
- sekce `Unreleased` se při release deterministicky převede na verzi a datum.

Migration note je povinná pro BREAKING změnu a doporučená pro významný additive compatibility contract.

## 9. Evidence a lidské rozhodnutí

Automatická evidence:

- CI checks;
- exact source SHA;
- candidate/release package hash;
- test suite results;
- validation report;
- security/isolation checks;
- online integration evidence.

Lidské rozhodnutí:

- scope judgment;
- metodická správnost;
- architektonická vhodnost;
- použitelnost;
- residual risks;
- GO, GO_WITH_ACCEPTED_RISKS nebo NO_GO.

Automatizace nesmí vytvořit lidské `passed`, approval nebo release GO. HRDR musí být navázaný na current SHA a candidate hash a změna relevantního scope či evidence jej zneplatní.

## 10. Backlog hygiene

Minimálně jednou za release nebo měsíčně:

- odstranit nebo uzavřít duplicates;
- označit superseded položky;
- prověřit items bez ownera;
- prověřit dlouhodobě Blocked items;
- potvrdit stále platný Goal a acceptance criteria;
- sjednotit Project metadata a Issue obsah;
- ověřit parent/child vazby;
- aktualizovat roadmap status;
- odstranit neplatná budoucí PR čísla z dokumentace;
- zkontrolovat, zda otevřené Draft PR skutečně představují aktivní implementaci.

## 11. Výjimky

P0 incidentní fix může začít před úplným triage, ale musí:

- mít Issue nejpozději současně s branchem;
- explicitně uvést důvod zkráceného procesu;
- zachovat testy, review, audit a release evidence podle rizika;
- nepoužít přímou změnu `main` jako standardní postup.
