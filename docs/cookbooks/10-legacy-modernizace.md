# Kuchařka 10 — Legacy modernizace

## Zásada

Modernizace není technologický rewrite. Musí mít měřitelný business/change outcome a evoluční cestu bez ztráty provozní kontroly.

## Evidence

- system-of-record a data owners,
- runtime/change coupling,
- incidenty a release lead time,
- batch windows a provozní omezení,
- skrytá pravidla,
- vendor knowledge a exit constraints.

## Prompt

> Vytvoř modernization evidence map. Odděl business rule od technického workaroundu. Navrhni seams, ACL, migrační slices, reconciliation, rollback a decommission criteria. Nezaměň target BC za deployment unit.

## Miro

Business EventStorming drž odděleně od technického as-is. Přidej transition context map, data migration lanes, parallel-run checkpoints a decommission dashboard.
