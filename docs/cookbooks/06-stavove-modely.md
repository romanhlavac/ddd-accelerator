# Kuchařka 06 — Stavové modely

## Účel

Stavový model vysvětluje business chování objektu v čase, povolené a zakázané přechody, autoritu, časové podmínky a důsledky. Nevzniká automaticky ze sloupce `status` ani z UI obrazovek.

## Čtyři úrovně

| Fáze | Úroveň | Otázka |
|---|---|---|
| Discover | observed | Jaké stavy a přechody skutečně pozorujeme? |
| Decompose | candidate | Naznačují odlišné lifecycles jiné modely nebo boundaries? |
| Define | validated | Jaký business state machine schvaluje doménový expert? |
| Code | implementation | Je explicitní technický automat užitečný a jak mapuje business model? |

## Vstupy

Events, commands, policies, temporal events, interview evidence, exceptions, authorization rules a quality scenarios.

## Chat prompt

> Z validovaných events odvoď observed lifecycle pro `Policy`. Rozliš state, milestone, condition a derived status. U každého přechodu uveď command, actor/authority, guard, resulting event, timeout, compensation a forbidden alternatives. Nezaváděj state bez evidence.

## Postup

1. Seřaď lifecycle events.
2. Hledej období, ve kterých se mění povolené chování.
3. Odděl milestone od stavu.
4. Pojmenuj commands a autority přechodů.
5. Doplň timeouts a scheduled transitions.
6. Zapiš forbidden transitions a jejich business důvod.
7. Ověř concurrent commands a duplicates.
8. Porovnej lifecycle s candidate boundaries.
9. Validuj s expertem pomocí příkladů.
10. Rozhodni, zda implementace potřebuje explicitní state machine.

## Miro změny

Observed model patří do Discover, candidate do Decompose, validated do Define a implementation view do Code. Nepřepisuj předchozí úroveň; odkazuj na ni a zaznamenej rationale změn.

## Výstupy

State diagram, transition table, command-event mapping, authority matrix, timeout policy, forbidden transitions, acceptance tests a traceability na source events.

## Kontroly

- každý state mění povolené chování,
- každá transition má trigger a resulting event,
- derived status není chybně persistovaný jako authority,
- timeout má ownera a recovery,
- model rozlišuje business a technický stav,
- implementation state machine nepřidává business význam bez doménového rozhodnutí.
