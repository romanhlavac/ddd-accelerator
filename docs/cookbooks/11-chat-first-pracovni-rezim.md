# Kuchařka 11 — Chat-first pracovní režim

## Cíl

Chat je primární orchestration a decision-support rozhraní. Skripty zajišťují deterministické technické kroky, ale nenahrazují doménové rozhodnutí, evidence review ani Git approval.

## Struktura každého promptu

1. `scope` a aktivní projekt,
2. business/architecture decision,
3. zdroje, které smí agent použít,
4. artefakty, které smí číst a měnit,
5. požadovaný plan/dry-run/write režim,
6. validační kritéria,
7. zákaz push/merge/delete bez potvrzení.

## Základní šablona

> Scope: project. Aktivní projekt: X. Cíl: připravit G3 evidence. Použij pouze ingestion a existing artifacts. Zachovej terminologii zdrojů a uveď source paths. Nejprve ukaž plán a očekávané soubory. Miro sync pouze dry-run. Necommituj ani nepushuj.

## Doporučený dialog

1. Agent shrne zadání a předpoklady.
2. Agent vyjmenuje chybějící evidence.
3. Uživatel potvrdí scope a write režim.
4. Agent navrhne prompt/workshop/script plan.
5. Agent provede read-only analýzu.
6. Agent ukáže diff nebo dry-run.
7. Uživatel potvrdí write.
8. Agent validuje výsledek a připraví Git review.

## Handoff na skript

Před voláním skriptu agent uvede:

- proč je skript potřeba,
- přesný příkaz a parametry,
- které soubory nebo Miro items se mohou změnit,
- očekávané exit codes,
- validační a rollback krok.

Příklad:

> Nyní navrhuji `Invoke-DDDAMiroSync.ps1 -Direction Pull -PromoteNew -DryRun`. Příkaz pouze vypíše candidate promotions a konflikty; nevytvoří YAML. Po kontrole bude možné odstranit `-DryRun`.

## Session closure

Na konci chat shrne: změněnou evidence, nová rozhodnutí, pending hotspoty, Miro operace, Git status, doporučený commit a navazující gate.

## Anti-patterny

- prompt bez aktivního scope,
- agent používá obecné znalosti jako nedoložený fakt,
- přímý write bez plánu,
- automatický conflict resolution,
- skript spuštěný bez vysvětlení dopadu,
- push nebo merge jako vedlejší efekt modelování.
