# ADR: Project steering a význam lifecycle gatů

Status: Accepted

Date: 2026-07-26

## Context

DDDA musí podporovat primárně konverzační práci, ale současně potřebuje auditovatelný projektový stav. Mechanické nalezení souboru nesmí být zaměněno za architektonické nebo business schválení. Současná starter metodika musí zůstat zachována a rozšiřována, nikoli nahrazena novým technickým workflow.

Human Review PR #8 odhalilo, že původní implementace umožňovala automatizaci zapsat `passed` pouze pomocí volného textu revieweru. Takové rozhodnutí nemá ověřitelnou lidskou provenance a je v rozporu s významem lifecycle gate.

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

Automatizace může vyhodnotit evidence status a připravit `not_ready` nebo `ready_for_review`. Nikdy sama neoznačí gate jako `passed`, `conditional` ani `rejected`.

### Human decision contract

Produkční gate decision musí obsahovat minimálně:

- gate a outcome;
- project ID a explicitně posuzovaný scope;
- Git commit projektu;
- hash scope/ownership a SHA-256 relevantních evidence artefaktů;
- konkrétního decision ownera z `project.yaml`;
- konkrétní lidskou identitu reviewera a approvera;
- UTC timestamp;
- `provenance: human`.

Obecné identity typu `CI`, `bot`, `automation`, `pipeline` nebo `Acceptance runner` nejsou lidským schválením.

`conditional` není completed gate. Musí obsahovat podmínky, jejich ownera a termín. `rejected`, `ready_for_review` a `not_ready` rovněž nejsou completed gates.

Platnost rozhodnutí se přepočítává vůči aktuálnímu projektu. Změna relevantního scope, ownership nebo evidence hashů rozhodnutí zneplatní. Reviewed commit musí zůstat předkem aktuálního HEAD; historie přepsaná mimo tuto lineage rozhodnutí zneplatní.

Test-only simulation je povolena pouze v explicitně označeném dočasném fixture projektu, v systémovém temp prostoru a s opt-in environment guardem. Není platným produkčním lidským rozhodnutím.

`Get-DDDAProjectStatus.ps1` je ve výchozím režimu read-only. Přepočet generovaných status artefaktů je explicitní write operace přes `-Refresh`.

## Options considered

### A. Gate je splněna, jakmile existují soubory

Pros:

- jednoduchá automatizace.

Cons:

- zaměňuje formální úplnost za kvalitu a rozhodnutí;
- vytváří falešný pocit jistoty;
- potlačuje business a architektonický ownership.

### B. Volný text revieweru je dostatečné schválení

Pros:

- jednoduchý příkaz a malé množství metadat.

Cons:

- bot nebo CI se může vydávat za člověka;
- chybí decision owner, scope a vazba na evidence;
- rozhodnutí nelze bezpečně invalidovat ani auditovat.

### C. Strukturované human decision recordy

Pros:

- mechanické kontroly jsou automatické;
- judgment zůstává u odpovědného člověka;
- Git zachovává auditní stopu;
- změna relevantních podkladů rozhodnutí zneplatní;
- chat může doporučit nejmenší další krok bez implicitního schválení.

Cons:

- více povinných polí při review;
- potřeba vysvětlit rozdíl mezi ready-for-review a passed;
- starší neauditovatelné `passed` záznamy nejsou považovány za platné bez nového review.

## Consequences

Positive:

- starter metodika je stabilní a rozšiřitelná;
- gaty mají auditovatelný význam;
- automatizace nemůže vydat produkční `passed`;
- current status a next actions lze generovat deterministicky;
- Miro zobrazuje stav, ale není autoritou pro gate approval.

Negative:

- lidské rozhodnutí vyžaduje explicitní owner, reviewer, approver a scope;
- relevantní změny evidence vyžadují nové review;
- staré neúplné decision recordy se zobrazí jako neplatné a workflow se vrátí k evidence statusu.

New obligations:

- dokumentace musí používat stejnou terminologii;
- testy musí ověřovat human provenance a spoofing guard;
- žádný sync, import, render ani acceptance runner nesmí implicitně schválit gate;
- conditional decision musí mít ownera a termín;
- promotion/release acceptance musí záviset na testu tohoto invariantu, nikoli na automatickém G1 → G2 průchodu.

## Impact

Platform areas:

- methodology;
- orchestration;
- schemas;
- CLI;
- Miro projection;
- tests;
- security and audit.

Existing workspaces:

- stávající evidence a artefakty zůstávají zachovány;
- starší `passed` bez strukturované human provenance se nepovažuje za platné schválení;
- nové decision metadata jsou aditivní, ale nové review je nutné pro pokračování přes dotčenou gate.

Migration:

- žádná automatická konverze lidských rozhodnutí;
- decision owner musí být explicitně uveden v `project.yaml owners`;
- dotčenou gate musí znovu schválit oprávněný člověk.

## Validation

- bootstrap připraví G1 jako `ready_for_review`, nikoli `passed`;
- acceptance runner nevytvoří žádné produkční lidské rozhodnutí;
- `passed` bez `provenance: human`, ownera, scope, evidence, reviewer/approvera nebo commit vazby selže;
- automatizační identita nemůže obejít human provenance guard;
- změna relevantní evidence zneplatní dřívější `passed`;
- `conditional` není v `completed_gates`;
- test-only simulation nelze použít v běžném projektu;
- read-only status query nemění Git working tree;
- Miro mapping a sync state nemění gate decision.

## Follow-up actions

- [ ] standardizovat Human Release Decision Record v #9;
- [ ] doplnit Miro visual acceptance kontrakt v #14;
- [ ] doplnit online Miro evidence v #12.
