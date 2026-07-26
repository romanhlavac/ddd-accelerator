# ADR: Project steering a význam lifecycle gatů

Status: Accepted

Date: 2026-07-26

## Context

DDDA musí podporovat primárně konverzační práci, ale současně potřebuje auditovatelný projektový stav. Mechanické nalezení souboru nesmí být zaměněno za architektonické nebo business schválení. Současná starter metodika musí zůstat zachována a rozšiřována, nikoli nahrazena novým technickým workflow.

## Decision

Kanonický tok zůstává:

```text
Align → Discover → Decompose → Strategize → Connect → Organize → Define → Code
   G1       G2          G3            G4          G5         G6        G7      G8
```

Rozlišujeme tři nezávislé stavy:

1. evidence status — požadované evidence existují nebo chybějí;
2. artifact status — pracovní, review-ready nebo přijatý stav artefaktu;
3. gate decision — explicitní lidské rozhodnutí `passed`, `conditional` nebo `rejected`.

Automatizace může vyhodnotit evidence status a připravit review. Nikdy sama neoznačí gate jako `passed`.

`Get-DDDAProjectStatus.ps1` je ve výchozím režimu read-only. Přepočet generovaných status artefaktů je explicitní write operace přes `-Refresh`.

## Options considered

### A. Gate je splněna, jakmile existují soubory

Pros:

- jednoduchá automatizace.

Cons:

- zaměňuje formální úplnost za kvalitu a rozhodnutí;
- vytváří falešný pocit jistoty;
- potlačuje business a architektonický ownership.

### B. Gaty jsou pouze manuální checklist bez evidence engine

Pros:

- jasné lidské rozhodnutí.

Cons:

- vysoká manuální práce;
- chybí rychlá detekce chybějících vstupů;
- slabá konzistence mezi projekty.

### C. Automatizované evidence + explicitní lidské rozhodnutí

Pros:

- mechanické kontroly jsou automatické;
- judgment zůstává u odpovědného člověka;
- Git zachovává auditní stopu;
- chat může doporučit nejmenší další krok.

Cons:

- více stavových artefaktů;
- nutnost vysvětlit rozdíl mezi ready-for-review a passed.

## Consequences

Positive:

- starter metodika je stabilní a rozšiřitelná;
- gaty mají auditovatelný význam;
- current status a next actions lze generovat deterministicky;
- Miro zobrazuje stav, ale není autoritou pro gate approval.

Negative:

- po změně evidence může být nutný explicitní refresh a commit;
- conditional/rejected gate vyžaduje další rozhodnutí, ne automatický postup.

New obligations:

- dokumentace musí používat stejnou terminologii;
- testy musí ověřovat, že read-only dotaz nemění Git working tree;
- žádný sync nebo render nesmí implicitně schválit gate.

## Impact

Platform areas:

- methodology;
- orchestration;
- schemas;
- CLI;
- Miro projection;
- tests.

Existing workspaces:

- stávající rozhodnutí zůstávají zachována;
- nové metadata jsou aditivní.

Migration:

- bez povinné migrace.

## Validation

- bootstrap vytváří G1–G8;
- G1 review posune next gate na G2 pouze po explicitním `passed`;
- read-only status query nemění hash status souborů;
- Miro mapping a sync state obsahují current-status a next-actions bez změny gate decision.
