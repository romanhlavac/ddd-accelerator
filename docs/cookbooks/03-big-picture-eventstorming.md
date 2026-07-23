# Kuchařka 03 — Big Picture EventStorming

## Cíl

Objevit end-to-end business dění, jazyk, pivoty, hodnotu, externí závislosti a hotspoty bez návrhu služeb nebo databází.

## Příprava

- scope a časový horizont,
- 6–15 účastníků s doménovou znalostí,
- 90–180 minut,
- frame `discover-big-picture-es`,
- seed otázky ze zdrojů, ne předvyplněná pravda.

## Prompt před workshopem

> Z ingestion připrav maximálně 20 kandidátních business událostí jako otázky. U každé uveď source path a confidence. Nevytvářej agregáty, API ani systémy jako cílový návrh.

## Facilitační kroky

1. silent storming událostí v minulém čase,
2. seřazení na časové ose,
3. odstranění duplicit,
4. pivot a temporal events,
5. aktéři a externí systémy,
6. hotspoty, rozpory a neznámé,
7. value-up/value-down,
8. výběr slices.

## Po workshopu

> Importuj pouze sticky notes označené jako validované nebo candidate managed artifacts. Vytvoř YAML domain events, actors, systems a hotspots. Neřízené poznámky ponech v Miru. Proveď pull dry-run a připrav diff.

## Gate G2

G2 neprojde, pokud tým pouze přepsal dnešní systémový workflow a neodhalil business rozhodnutí nebo rozpory.
