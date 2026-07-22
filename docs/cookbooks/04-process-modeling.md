# Kuchařka 04 — Process Modeling

## Cíl

Rozpracovat hodnotný, rizikový nebo sporný segment Big Picture timeline a odhalit rozhodovací pravidla, exceptions a kandidátní boundary seams.

## Vstup

- vybraný segment,
- aktéři,
- hlavní události,
- hotspot owner,
- známé externí systémy.

## Sekvence

```text
Actor → Command/Action → Policy/Procedure → External System → Event → Read Model
```

## Facilitační otázky

- kdo může vydat command,
- jaké informace potřebuje,
- které pravidlo rozhoduje,
- co se stane při zamítnutí nebo timeoutu,
- který event je business fact,
- co musí uživatel vidět před dalším krokem,
- kde se mění jazyk nebo owner.

## Chat prompt

> Zpracuj process slice bez návrhu mikroservis. U každého commandu uveď actor, preconditions, policy, resulting event, read model a exceptions. Navrhni boundary hypotheses a důvody, ne definitivní BC.

## Výstup

Process-slice YAML, rule clusters, exceptions, read-model needs a vstup pro G3.
