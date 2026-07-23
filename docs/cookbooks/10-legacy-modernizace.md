# Kuchařka 10 — Legacy modernizace

## Zásada

Modernizace není technologický rewrite. Musí mít měřitelný business nebo change outcome a evoluční cestu bez ztráty provozní kontroly, datové integrity a doménového knowledge.

## Entry criteria

- známý business pain a decision owner,
- přístup k provozní a změnové evidence,
- účast doménových i technických expertů,
- možnost ověřovat seams a migrační slices,
- explicitní provozní kontinuita a rollback očekávání.

## Evidence inventory

- system-of-record a data owners,
- runtime topology a deployment dependencies,
- integration inventory a batch windows,
- incidenty, release lead time a change failure rate,
- skrytá business pravidla a manual workarounds,
- vendor knowledge, smluvní a exit constraints,
- reconciliation, backup a recovery postupy.

## Chat prompt

> Scope: project. Vytvoř modernization evidence map. Odděl business rule, regulatory constraint, data dependency, technical workaround a organizational dependency. U každé položky uveď source. Navrhni target boundaries, seams, ACL, migrační slices, reconciliation, rollback, observability a decommission criteria. Nezaměň BC za deployment unit.

## Postup

1. Definuj outcome a baseline metriky.
2. Katalogizuj evidence a gaps.
3. Modeluj business realitu odděleně od technického as-is.
4. Zmapuj runtime/change/data coupling.
5. Navrhni target domain boundaries.
6. Najdi seams a anti-corruption boundaries.
7. Prioritizuj vertical migration slices.
8. Definuj dual-run/reconciliation.
9. Připrav rollout, rollback a observability.
10. Definuj decommission evidence a knowledge transfer.

## Miro změny

Big Picture business timeline, samostatný technical as-is frame, coupling overlay, seam map, transition context map, data migration lanes, reconciliation checkpoints, risks a decommission dashboard.

## Výstupy

Modernization brief, characterization tests/evidence, target boundaries, transition contracts, slice backlog, data migration plan, operational readiness, ADR a decommission checklist.

## Anti-patterny

- big-bang replacement,
- strangler pouze na URL/API vrstvě bez data ownershipu,
- shared database bez exit criteria,
- kopie legacy modelu do nových služeb,
- vendor replacement bez knowledge retention,
- decommission podle kalendáře místo evidence.
