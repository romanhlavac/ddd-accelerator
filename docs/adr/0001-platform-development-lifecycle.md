# ADR: Reprodukovatelný lifecycle vývoje DDDA platformy

Status: Accepted

Date: 2026-07-26

## Context

DDDA je verzovaný produkt/framework. Dosavadní vývoj používal jednotlivé skripty a CI kontroly, ale neměl jednotný reprodukovatelný tok od PR přes candidate package až po validovaný release. To zvyšovalo ruční práci, riziko testování jiného stavu než skutečného PR head a riziko záměny platformního vývoje s klientským workspace.

Prioritní quality attributes:

- reproducibility;
- testability;
- auditability;
- safety;
- modifiability;
- usability pro jednoho správce i budoucí platformní tým.

## Decision

Zavádíme tento lifecycle:

```text
change request
→ feature branch
→ implementation
→ CI
→ validate-pr nad exact PR head
→ human review
→ promote-pr s explicitním potvrzením
→ merge
→ release package
→ generated example workspace
→ manifest-driven ingestion
→ smoke + acceptance
→ release report
→ release tag
```

Git je source of truth, PR je jednotka změny a candidate/release package je jednotka distribuce a validace. Smoke, E2E a acceptance testy musí běžet z nově rozbaleného package, ne z development working tree.

Veřejným entry pointem je `ddda.ps1`. Specializované skripty zůstávají interními stavebními bloky a compatibility entry points.

## Options considered

### A. Pokračovat s jednotlivými skripty a ručním pořadím

Pros:

- minimální okamžitá změna;
- žádná nová orchestrace.

Cons:

- vysoká manuální chybovost;
- nejednoznačný testovaný SHA;
- slabá reprodukovatelnost;
- komplikované předávání práce.

### B. Testovat pouze development working tree

Pros:

- rychlé lokální testy;
- jednoduchá implementace.

Cons:

- package drift;
- release artifact nemusí odpovídat testovanému obsahu;
- skryté závislosti na lokálním prostředí.

### C. Exact-SHA validation a package-first lifecycle

Pros:

- silná reprodukovatelnost a auditovatelnost;
- jasná hranice platforma/workspace/release;
- automatizovatelný promotion gate;
- example workspace prokazuje reálnou použitelnost balíčku.

Cons:

- delší validation běh;
- potřeba správy dočasných clone, package a reportů;
- promotion vyžaduje GitHub CLI a autentizaci.

## Consequences

Positive:

- jeden doporučený command flow;
- validation report je svázán s PR head SHA a package hashem;
- klientský workspace se nepoužívá jako test fixture;
- běžné testy nemohou samy mergovat nebo tagovat.

Negative:

- více platformního kódu a testovací infrastruktury;
- E2E a online Miro acceptance jsou pomalejší než unit testy;
- release proces má explicitní nároky na nástroje a oprávnění.

New obligations:

- aktualizovat changelog u behaviorálních změn;
- doplnit ADR u dlouhodobých rozhodnutí;
- doplnit migration note u změn kompatibility;
- udržovat minimal example a invariant-based regression;
- zachovat fail-closed promotion.

## Impact

Platform areas:

- CLI;
- testing;
- release;
- workspace generator;
- example and ingestion;
- security governance;
- documentation.

Existing workspaces:

- beze změny;
- nejsou používány jako platformní fixture.

Migration:

- none; změna je aditivní.

## Validation

- unit a component testy helperů, package builderu a report generatoru;
- integration test package → workspace → ingestion → steering;
- security test package contents a path isolation;
- offline acceptance;
- volitelný online Miro acceptance;
- promotion dry-run bez merge oprávnění.

## Follow-up actions

- [ ] Použít lifecycle pro PR #9–#11.
- [ ] Po prvním release zpřesnit časové limity a retention reportů.
- [ ] Podle repository policy upravit počet požadovaných approvals.
