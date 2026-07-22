# Kuchařka 06 — Stavové modely

## Účel

Stavový model vysvětluje business chování objektu v čase. Nevzniká automaticky ze sloupce `status`.

## Postup

1. Discover: observed states a skutečné přechody,
2. Decompose: candidate lifecycle a ownership,
3. Define: validovaný model, forbidden transitions, timeouts, authorization,
4. Code: implementation state machine pouze pokud zjednodušuje invarianty nebo audit.

## Prompt

> Z událostí odvoď observed lifecycle. Odděl explicitní state, implicitní condition a milestone. U každého přechodu uveď command, event, actor, guard, timeout a forbidden alternatives.

## Výstup

State diagram, transition table, command-event mapping, acceptance tests a odkazy na source events.
