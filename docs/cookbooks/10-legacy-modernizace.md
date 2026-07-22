# Kuchařka 10 — Legacy modernizace

## Výsledek

Vznikne businessově ukotvený modernizační plán s cílovými hranicemi, seams, přechodnými stavy, ownershipem dat, migračními slices, observabilitou a rollbackem.

## Předpoklady

- je znám business důvod modernizace,
- je dostupná alespoň minimální provozní a technická evidence,
- stakeholderům je jasné, že cílem není automaticky přepis 1:1,
- kontinuita provozu a regulatorní omezení jsou explicitní.

## Postup

1. V Align formulujte měřitelné business a provozní cíle modernizace.
2. Oddělte business Big Picture ES od technického runtime flow legacy systému.
3. Inventarizujte faktické vlastníky dat, batch procesy, integrační body a manuální workarounds.
4. Identifikujte change coupling, runtime coupling a knowledge ownership.
5. V Decompose navrhněte cílové doménové hranice podle jazyka, pravidel a lifecycle; ne podle modulů legacy aplikace.
6. V Connect určete transitional contracts, anti-corruption layers a dočasné system-of-record.
7. Vyberte seams, které umožní odebrat business slice end-to-end.
8. Seřaďte slices podle business hodnoty, rizika, závislostí a schopnosti měřit výsledek.
9. Pro každý slice definujte dual-run/parallel-run potřebu, migraci dat, reconcile, rollback a observabilitu.
10. Zaveďte fitness functions pro snižování coupling a odstraňování dočasných vazeb.
11. Evidujte přechodné bounded contexts a datum/condition jejich zániku.
12. Po každém slice aktualizujte Context Map, data ownership a provozní evidence.

## Povinné artefakty

- as-is evidence map,
- observed business lifecycle,
- current data ownership a system-of-record,
- target Context Map,
- transition Context Map,
- seam catalog,
- migration slice backlog,
- risk and rollback plan,
- observability plan,
- ADR pro významné kompromisy.

## Kontroly

- každý slice přináší business nebo provozní hodnotu,
- nevzniká dlouhodobě sdílená databáze jako skrytý integrační kontrakt,
- dual-write má vlastníka, reconcile a konečné datum,
- přechodné řešení má exit criteria,
- nový model není kolonizován názvy a omezeními legacy systému bez důvodu,
- organizace má tým schopný převzít ownership nového kontextu.

## Typické chyby

- přepis obrazovku po obrazovce bez změny hranic,
- extrakce mikroservis podle tabulek,
- big-bang migrace bez business nutnosti,
- ignorování historických dat a reportingu,
- dočasná integrace bez plánu odstranění,
- cílový model bez plánu přechodu.