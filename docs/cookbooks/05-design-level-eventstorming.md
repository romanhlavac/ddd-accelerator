# Kuchařka 05 — Design-Level EventStorming

## Výsledek

Uvnitř jednoho validovaného bounded contextu vznikne behaviorální model commandů, consistency boundaries/agregátů, invariantů, událostí, policies a projekcí.

## Předpoklady

- bounded context má jasnou odpovědnost, ownera a hranici,
- Context Map a data ownership jsou alespoň pracovně schváleny,
- je vybrán konkrétní business scénář,
- účastní se doménový expert a vývojáři odpovědní za implementaci.

## Postup

1. Uveďte název bounded contextu, jeho odpovědnost a out-of-scope.
2. Vezměte jeden scénář z Process Modelingu.
3. Zapište command jako záměr aktéra nebo policy.
4. Určete fakta potřebná pro rozhodnutí a jejich vlastníka.
5. Navrhněte consistency boundary pouze pro pravidla, která musí být atomicky pravdivá.
6. Formulujte invarianty jako testovatelné business věty.
7. Zapište vzniklé doménové události v minulém čase.
8. Doplňte policies, které reagují na události a mohou vyvolat další command.
9. Doplňte projekce/read modely pro rozhodování a dotazy.
10. Ověřte chybové scénáře, idempotenci, souběh a časové podmínky.
11. Označte hranice konzistence, nikoli automaticky deployable služby.
12. Přeneste rozhodnutí do YAML a relevantních ADR.

## Kontrolní otázky

- Musí být toto pravidlo pravdivé ihned, nebo stačí eventual consistency?
- Který objekt je skutečným vlastníkem změny?
- Je navržený agregát příliš velký kvůli pohodlí dotazu?
- Není policy ve skutečnosti lidské rozhodnutí?
- Je událost business fakt, nebo integrační obálka?
- Co se stane při opakovaném commandu nebo doručení události?

## Chyby

- začít třídami, endpointy nebo databázovým schématem,
- přenést jeden agregát přes více bounded contexts,
- označit každou validaci jako invariant,
- použít Design-Level ES k rozhodování o strategických hranicích,
- zavést Event Sourcing jen proto, že model používá doménové události.

## Navazující krok

Validujte business lifecycle, vytvořte contract/invariant tests a ADR pro důležitá technická rozhodnutí.