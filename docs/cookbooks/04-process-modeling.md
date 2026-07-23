# Kuchařka 04 — Process Modeling

## Účel a rozhodnutí

Process Modeling rozpracuje hodnotný, rizikový nebo sporný segment Big Picture timeline. Cílem je pochopit rozhodování, exceptions, čekání, externí závislosti a možné boundary seams. Výsledkem není návrh mikroservis ani hotové agregáty.

## Entry criteria

- Big Picture timeline má validovaný scope,
- vybraný slice má business důvod a ownera,
- klíčové události a aktéři jsou alespoň candidate,
- tým zná otázku, kterou má model zodpovědět.

## Vstupy a role

Vstupy: timeline segment, glossary, hotspoty, source evidence, známé policy statements a externí systémy. Účastníci: doménový expert, process owner, operace, produkt, architekt a podle potřeby compliance nebo data owner.

## Modelovací sekvence

```text
Actor → Command/Action → Policy/Procedure → External System → Event → Read Model
```

Rozlišuj:

- **command/action** — záměr aktéra,
- **policy** — pravidlo reagující na fakt nebo rozhodující o dalším kroku,
- **procedure** — opakovatelný postup, často s lidskou interakcí,
- **event** — business fakt v minulém čase,
- **read model** — informace potřebná pro rozhodnutí nebo další akci.

## Chat prompt

> Scope: project. Pro slice `accepted offer → policy issuance` vytvoř Process Model. U každého commandu uveď actor, preconditions, potřebný read model, policy/procedure, resulting event, alternative branches, timeout, manual intervention a external dependency. Nevytvářej agregáty ani deployment units. Na konci navrhni boundary hypotheses s důvody a seznam otázek pro experty.

## Facilitační postup

1. Zarámuj začátek, konec a hodnotu slice.
2. Začni hlavním actor intentem, ne dnešním systémovým krokem.
3. Doplň informace, které aktér potřebuje.
4. Pojmenuj policy nebo rozhodovací pravidlo.
5. Zapiš resulting event a business význam.
6. Přidej rejected, timeout, duplicate, unavailable a manual branches.
7. Označ místa změny jazyka, authority, lifecycle nebo data ownera.
8. Zaznamenej synchronní závislosti a čekání.
9. Vytvoř candidate boundary seams a validační otázky.

## Miro změny

Ve frame `discover-process-modeling` vytvoř samostatné rows pro hlavní flow a exceptions. Použij stabilní barvy actor/command/policy/system/event/read model. Hotspoty umísti přímo k nejasnému rozhodnutí. Layout zůstává vlastnictvím Mira.

## YAML a Git výstupy

- process-slice artefakt,
- command/event catalog,
- policy/rule candidates,
- exception catalog,
- read-model needs,
- boundary hypotheses a rationale,
- nové glossary terms a hotspoty.

Po workshopu proveď Pull dry-run, promotion review a projektový diff. Nevkládej technické rozhodnutí do stejného commitu jako kuraci workshopové evidence.

## Kontroly

- každý command má autoritu,
- každé rozhodnutí má rule ownera nebo hotspot,
- eventy nejsou UI kliknutí ani technické logy,
- exceptions nejsou skryty do poznámky „error handling“,
- candidate boundaries jsou zdůvodněny jazykem, pravidly, lifecycle nebo ownershipem,
- výstup podporuje G3, ale nevydává hypotheses za accepted BC.

## Anti-patterny

- přepis BPMN nebo systémového workflow bez business otázky,
- command = API endpoint,
- event = databázový update,
- všechny kroky v jednom univerzálním modelu,
- předčasný aggregate nebo service design.
