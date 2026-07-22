# Kuchařka 05 — Design-Level EventStorming

## Entry criteria

- BC má účel, language a inbound/outbound contracts,
- G5 je splněn a G7 připravován,
- vybraný flow patří dovnitř jednoho BC.

## Sekvence

```text
Actor → Command → Aggregate candidate → Invariant → Domain Event
→ Policy → Command → Projection
```

## Prompt

> Modeluj pouze BC `Policy Administration`. Pro každý command popiš autoritu, invariant, consistency boundary, resulting domain event a read model. Označ vše, co vyžaduje synchronní cross-context transakci, jako hotspot a navrhni alternativu.

## Kontroly

- agregát není jen tabulka,
- invariant je business pravidlo vyžadující atomickou ochranu,
- integration event není zaměněn za interní domain event,
- policy nespouští nekonečný event-command loop,
- lifecycle odpovídá validovanému state modelu.
