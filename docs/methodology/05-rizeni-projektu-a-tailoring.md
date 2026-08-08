# Řízení projektu a lifecycle tailoring

## Zachovaný metodický základ

Kanonická starter metodika zůstává:

```text
Align → Discover → Decompose → Strategize → Connect → Organize → Define → Code
   G1       G2          G3            G4          G5         G6        G7      G8
```

Tailoring tuto posloupnost nenahrazuje. Určuje hloubku práce, typově specifická rozšíření a části, které mohou být u úzce vymezeného projektu odloženy. Odložená fáze není automaticky splněná gate.

## Tři oddělené stavy

1. **evidence status** — zda existují požadované podklady;
2. **artifact status** — observed, candidate, validated, accepted, superseded nebo deleted_pending;
3. **gate decision** — passed, conditional nebo rejected po explicitním review.

Automatizace smí určit první stav. Druhý a třetí vyžadují doménové nebo rozhodovací potvrzení podle významu změny.

## Chat-first odpovědnost

Chat:

- vede intake;
- vysvětluje metodiku;
- navrhuje varianty a další krok;
- připravuje drafty;
- upozorňuje na chybějící evidence a konflikty.

Skript:

- validuje kontrakty;
- vytváří deterministickou strukturu;
- aktualizuje status a gate records;
- provádí potvrzený Miro render nebo sync;
- zanechává auditní diff.

Člověk:

- potvrzuje scope, ownery a business význam;
- schvaluje gate;
- rozhoduje sémantické konflikty;
- potvrzuje commit, push a merge.
