# Facilitace EventStormingu v DDDA

## Tři odlišné úrovně

### Big Picture / Discover

Cíl: sdílený end-to-end obraz dění. Začni oranžovými minulými událostmi v business jazyce. Poté doplň časové události, pivoty, aktéry, externí systémy a hotspoty. Neřeš agregáty ani databáze.

Příprava: scope, účastníci, 90–180 minut, horizontální timeline, legenda, parking lot.

Facilitační sekvence:

1. silent storming událostí,
2. seřazení v čase,
3. odstranění duplicit a sjednocení jazyka,
4. identifikace pivot events,
5. aktéři a externí systémy,
6. hotspoty a rozpory,
7. value-up/value-down momenty,
8. výběr slices pro Process Modeling.

### Process Modeling / Discover → Decompose

Cíl: rozpracovat vybrané scénáře a rozhodování.

```text
Actor → Command/Action → Policy/Procedure → External System → Event → Read Model
```

Zaznamenej alternativní větve, business exceptions, čekání, timeouty a ruční zásahy. Výsledkem jsou clustery pravidel a kandidátní hranice, ne hotová implementace.

### Design-Level / Define

Cíl: navrhnout chování uvnitř jednoho vymezeného BC.

```text
Actor → Command → Aggregate candidate → Invariant → Domain Event
→ Policy → Command → Projection/Read Model
```

Zákazy: distribuovaná transakce přes BC, agregát podle tabulky, event jako technický log bez business významu.

## Chatová podpora

Před workshopem:

> Z dostupné ingestion připrav seed list pouze jako otázky a kandidáty. Nevytvářej autoritativní timeline. U každého seedu uveď zdroj.

Po workshopu:

> Přepiš pouze validované sticky notes do spravovaných YAML artefaktů. Nespravované poznámky zachovej v Miru. Rozpory vytvoř jako hotspoty s ownerem otázky.

## Definition of Done workshopu

- účastníci rozumí scope a legendě,
- události jsou v minulém čase a v business jazyce,
- hotspoty nejsou skryty syntetickým kompromisem,
- výstup má ownera a plán validace,
- Miro sync proběhl nejprve jako dry-run,
- změny jsou reviewovány v projektovém PR.
