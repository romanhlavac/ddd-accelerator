# ADR: Reprodukovatelný lifecycle vývoje DDDA platformy

Status: Accepted — amended 2026-08-18 by ADR 0008; amended 2026-08-20 by ADR 0009

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

Git je source of truth, PR je jednotka platformní změny a candidate/release package je jednotka reprodukovatelné validace/distribuce. Package-dependent smoke, E2E a acceptance musí běžet z nově rozbaleného package, ne z development working tree.

### Amendment 2026-08-18 — implementation merge ≠ release promotion

Post-release review DDDA 0.1.0 a PR #74 ukázaly, že původní lineární sekvence `human review → promote-pr → merge → release` směšovala dvě různé governance boundaries. ADR 0008 proto tento lifecycle prospektivně zpřesňuje.

#### Governed implementation PR

```text
change request
→ feature/fix branch
→ implementation
→ exact-SHA CI
→ validate-pr nad exact PR head
→ Human Review pro stejné SHA/package
→ merge-pr -DryRun
→ explicitní human merge authorization
→ merge-pr -ConfirmMerge
→ merge do main
→ NO release package
→ NO release validation
→ NO release tag
```

Implementation merge nevyžaduje HRDR ani Release Scope Gate. `merge-pr` je merge-only command a nesmí volat release/tag execution path.

#### Release candidate

Až po integraci práce určené pro konkrétní release:

```text
release candidate (typicky release/<version> PR nebo ekvivalent)
→ exact-SHA candidate validation
→ release cut / changelog consistency
→ Human Release Decision Record
→ strict Release Scope Gate
→ promotion dry-run
→ explicitní Human Release Decision
→ samostatná explicitní release/promotion authorization
→ canonical promotion
→ release-candidate merge, pokud jej workflow vyžaduje
→ release package
→ generated release-validation workspace
→ manifest-driven ingestion
→ smoke + acceptance
→ release report
→ release tag
```

Release Scope Gate vyžaduje kompletní/konzistentní release scope, ale **není** precondition pro předchozí merge jednotlivých implementačních PR. Tím se zachová strict release governance bez multi-PR deadlocku.

Human Review, implementation merge authorization, Human Release Decision a release/promotion authorization jsou odlišné lidské boundaries. Automation nesmí žádnou z nich inferovat z technického PASS ani z jiné authorization.

### Amendment 2026-08-20 — exact-SHA ancestry a merge strategy

ADR 0009 prospektivně zpřesňuje způsob samotného implementation merge:

```text
HIGH / BREAKING → merge commit REQUIRED
LOW / MEDIUM    → merge commit DEFAULT; squash jen explicitní human exception
UNKNOWN impact  → merge commit only
rebase           → forbidden
```

Důvodem je zachování exact validated PR HEAD jako přímo dohledatelného ancestor výsledného `main` state. Čitelnost hlavní historie se řeší first-parent pohledem, nikoli ztrátou reviewované ancestry.

LOW/MEDIUM squash exception je samostatný human-governed record vázaný na stejné PR/SHA/candidate package/impact a musí po merge vytvořit explicitní source→result mapping. Automation ji nesmí vytvořit ani inferovat.

Pro canonical merge provádí `merge-pr` server-side post-read-back a ověřuje validated PR HEAD jako parent/ancestor výsledného merge commit.

#70 mění merge policy samotnou; jeho vlastní integraci proto řídí pre-existing policy z exact base `297f61f6012f180e70805999df2ac1abe9616a05`. Nový contract je účinný až po integraci #70 do `main`. Transition je exact-base-bound a není precedentem pro budoucí HIGH/BREAKING squash. Historie PR #8 / `v0.1.0` ani dalších již mergovaných PR se nepřepisuje.

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
- automatizovatelné mechanical gates;
- example workspace prokazuje reálnou použitelnost balíčku.

Cons:

- delší validation běh;
- potřeba správy dočasných clone, package a reportů;
- release promotion vyžaduje dostupnou GitHub autentizaci; GitHub CLI je pouze volitelný provider.

### D. Jeden promote-pr pro implementation merge i release

Zamítnuto dodatkem 2026-08-18. Se strict Release Scope Gate může vytvořit kruhovou závislost u multi-PR releasu a směšuje integration a release authority.

### E. Globální squash jako merge default

Zamítnuto dodatkem 2026-08-20 pro HIGH/BREAKING. Squash zachová výsledný obsah, ale exact reviewed PR HEAD není ancestor výsledného main state a audit závisí na externím mappingu. Detail trade-offu a LOW/MEDIUM exception popisuje ADR 0009.

## Consequences

Positive:

- exact-SHA validation report je svázán s PR head SHA a package hashem;
- klientský workspace se nepoužívá jako test fixture;
- běžné testy nemohou samy mergovat nebo tagovat;
- implementation PR lze bezpečně integrovat bez vytvoření release;
- strict Release Scope Gate se aplikuje až na skutečný release candidate;
- merge a release authorization zůstávají oddělené;
- HIGH/BREAKING validated SHA zůstává po merge v ancestry;
- first-parent history zachovává čitelnost bez ztráty auditability.

Negative:

- lifecycle má explicitně dva orchestration commands/boundaries (`merge-pr`, `promote-pr`);
- před release je potřeba explicitní release candidate;
- E2E a online Miro acceptance jsou pomalejší než unit testy;
- release proces má explicitní nároky na nástroje, evidence a oprávnění;
- historie obsahuje více merge commits;
- LOW/MEDIUM squash vyžaduje explicitní human exception evidence.

New obligations:

- aktualizovat changelog u behaviorálních změn;
- doplnit ADR u dlouhodobých rozhodnutí;
- doplnit migration note u změn kompatibility;
- udržovat minimal example a invariant-based regression;
- zachovat fail-closed implementation merge i release promotion;
- Human Review evidence vázat na exact implementation SHA/package;
- HRDR + Release Scope Gate vázat na exact release candidate;
- wrong merge method odmítnout před irreversible merge;
- canonical merge ověřit post-merge ancestry read-backem.

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

- none; změna je aditivní/non-breaking governance tightening.

## Validation

- unit a component testy helperů, package builderu a report generatoru;
- integration test package → workspace → ingestion → steering;
- security test package contents a path isolation;
- offline acceptance;
- volitelný online Miro acceptance;
- governed `merge-pr` dry-run bez side effects;
- impact → merge-method matrix a wrong-method negative regression;
- canonical merge ancestry invariant a LOW/MEDIUM squash exception contract;
- multi-PR anti-deadlock regression;
- strict release-scope regression;
- promotion dry-run bez release side effects.

## Follow-up actions

- [x] Používat oddělený implementation merge / release candidate lifecycle pro post-0.1.0 stabilization.
- [ ] Po maintenance release zpřesnit časové limity a retention reportů.
- [x] Verzovat risk-based merge strategy a exact-SHA ancestry contract v ADR 0009 / #70; activation zůstává podmíněna HVR a samostatnou merge authorization #70.
