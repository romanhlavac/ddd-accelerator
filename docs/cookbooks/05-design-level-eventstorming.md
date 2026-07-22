# Kuchařka 05 — Design-Level EventStorming

## Účel

Design-Level EventStorming modeluje chování uvnitř jednoho konkrétního bounded contextu. Převádí validované business scénáře do commands, invariantů, aggregate candidates, domain events, policies a projections. Nesmí opravovat nejasné strategické hranice taktickými patterny.

## Entry criteria

- BC má purpose, ownera a ubiquitous language,
- inbound/outbound contracts jsou candidate nebo validated,
- G5 je splněn a G7 je připravován,
- vybraný flow patří převážně dovnitř jednoho BC,
- existuje process slice a validovaný nebo candidate lifecycle.

## Role a příprava

Doménový expert, product owner, developer, tester a architekt. Připrav BC Canvas, context map, rules, lifecycle, quality scenarios a otevřené kontrakty.

## Modelovací sekvence

```text
Actor → Command → Aggregate candidate → Invariant → Domain Event
→ Policy → Command → Projection/Read Model
```

Aggregate candidate je hypotéza consistency boundary. Nejdřív formuluj invariant, potom rozhoduj, co musí být atomicky dostupné.

## Chat prompt

> Scope: project. Modeluj pouze BC `Policy Administration`. Pro každý command popiš actor/authority, intent, preconditions, invariant, consistency boundary, resulting domain event, policy reactions, projections a external contracts. Vyznač vše, co vyžaduje synchronní cross-context transakci, jako hotspot. Navrhni acceptance examples a nejjednodušší implementační variantu.

## Facilitační postup

1. Potvrď purpose a hranici BC.
2. Vyber jeden end-to-end scénář.
3. Zapiš commands a autority.
4. U každého commandu formuluj business invariant.
5. Navrhni minimální consistency boundary.
6. Zapiš domain event v business jazyce.
7. Doplň policies a následné commands.
8. Urči projections a query needs.
9. Přidej duplicate, concurrency, timeout a compensation scénáře.
10. Proveď walkthrough proti lifecycle a quality scenarios.

## Miro změny

Použij frame `define-design-level-es`. Odděl interní domain events od published integration events. Cross-context dependencies kresli přes hranici frame a odkaž je na context map; nekresli je jako interní atomickou transakci.

## YAML a Git výstupy

- commands a handlers,
- invariants,
- aggregate candidates s rationale,
- internal domain events,
- integration contracts nebo mapping,
- policies,
- projections,
- acceptance examples,
- ADR candidates.

## Kontroly

- aggregate není tabulka ani celý BC,
- invariant vyžaduje skutečnou konzistenci,
- domain event je business fact,
- integration event je verzovaný contract,
- policy nespouští nekonečný event-command loop,
- model vysvětluje concurrency a idempotence,
- tactical design podporuje prioritní quality attributes.

## Anti-patterny

- agregát pro každou entitu,
- přímé sdílení databáze přes BC,
- distribuovaný aggregate,
- Event Sourcing bez temporal/audit důvodu,
- read model používaný jako write authority.
