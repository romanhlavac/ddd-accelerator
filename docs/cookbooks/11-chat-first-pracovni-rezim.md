# Kuchařka 11 — Chat-first pracovní režim

## Struktura každého promptu

1. scope a aktivní projekt,
2. cílové rozhodnutí,
3. zdroje, které smí agent použít,
4. artefakty, které smí měnit,
5. požadovaný dry-run nebo write režim,
6. validační kritéria,
7. zákaz push/merge bez potvrzení.

## Šablona

> Scope: project. Aktivní projekt: X. Cíl: připravit G3 evidence. Použij pouze ingestion a existing artifacts. Zachovej terminologii zdrojů a uveď source paths. Nejprve ukaž plán a diff. Miro sync pouze dry-run. Necommituj ani nepushuj.

## Handoff mezi chatem a skriptem

Chat má vysvětlit, proč se skript volá, s jakými parametry, co očekává za výstup a jak se ověří. Skript nesmí být magická náhrada doménového rozhodnutí.
