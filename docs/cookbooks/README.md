# Kuchařky DDDA

Kuchařka je opakovatelný pracovní postup pro chat, workshop, Miro, YAML a Git. Není to pouze seznam příkazů. Každá kuchařka má vysvětlit, jaké rozhodnutí podporuje, jakou evidence vyžaduje, co má změnit v Miru, jaké soubory vzniknou, jak se výsledek validuje a kdy je nutné se vrátit o fázi zpět.

## Jak kuchařky používat

1. V chatu deklaruj `scope` a aktivní projekt.
2. Načti `project.yaml`, `ddda.lock.yaml`, tento index a relevantní kuchařku.
3. Popiš business nebo architektonické rozhodnutí.
4. Zkontroluj vstupy a chybějící evidence.
5. Nech chat navrhnout plán a prompty.
6. Před Miro write nebo synchronizací proveď dry-run.
7. Po změně zkontroluj YAML, Miro mapping, sync report a Git diff.
8. Commituj význam změny, nikoli pouze technický sync.

## Anatomie kuchařky

- **Účel a rozhodnutí** — proč se postup provádí.
- **Entry criteria** — kdy má smysl začít.
- **Vstupy a role** — evidence a účastníci.
- **Chat prompt** — doporučený výchozí prompt.
- **Postup** — facilitační a technické kroky.
- **Miro změny** — očekávané frames a itemy.
- **YAML/Git výstupy** — kanonické soubory a review.
- **Kontroly** — Definition of Done.
- **Anti-patterny** — časté chyby.
- **Navazující gate** — rozhodnutí, které výstup podporuje.

## Doporučené pořadí

Po novém clone začni kuchařkou 13. Potom obvykle následuje 01 → 14 → 02 → 03 → 04 → 06 → 08. Po stabilizaci hranic následuje 05 pro konkrétní BC. Kuchařky 07, 11 a 12 jsou průřezové. Kuchařka 10 rozšiřuje tok legacy modernizace.
