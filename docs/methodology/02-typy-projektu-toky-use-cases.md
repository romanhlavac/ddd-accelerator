# Typy projektů, workflow profily a use cases

## Princip volby

Vyber nejmenší profil, který pokrývá rozhodovací problém. Velikost rozpočtu sama o sobě neznamená `portfolio-program`. Typ nastavuje výchozí tok; rozšíření se zapisují do `workflow.extensions`.

| Typ | Hlavní rozhodnutí | Typický konec |
|---|---|---|
| `portfolio-program` | portfolio domén, ownership, roadmapa | programové inkrementy |
| `greenfield-product` | první hodnotný slice a hranice produktu | implementovatelný slice |
| `legacy-modernization` | evoluční náhrada a decommission | ověřený migrační slice |
| `legacy-transformation` | nový business + operating model + IT | transition architecture |
| `integration-landscape` | data ownership a kontrakty | integrační guardrails |
| `purchased-product-adoption` | fit-gap a ochrana vlastního modelu | implementační boundary |
| `domain-discovery` | jazyk, události, hotspoty, kandidátní hranice | G3 / backlog otázek |
| `architecture-review` | riziko a investiční doporučení | review report + ADR backlog |
| `operating-model-and-teams` | týmový ownership a interaction modes | cílová topology |
| `bounded-context-design` | chování a taktický model jednoho BC | G8 |

## Kombinace profilů

Příklad modernizace s COTS a změnou týmů:

```yaml
project:
  type: legacy-modernization
workflow:
  profile: legacy-modernization
  extensions:
    - purchased-product-adoption
    - operating-model-and-teams
```

## Portfolio program

Povinné workshopy: strategy alignment, capability landscape, Big Picture ES podle value streams, portfolio decomposition, context mapping, Team Topologies, roadmap slicing.

Miro změny: jeden control center, portfolio capability frame, několik Big Picture lanes, programová context map, ownership overlay a roadmapa.

## Greenfield product

Povinné workshopy: product vision, user outcomes, Big Picture ES, decomposition, first-slice selection, Design-Level ES, quality attribute workshop.

Miro změny: hlavní timeline, jeden prioritní process slice, BC canvases pouze pro vybrané kandidáty, detailní frame pro první slice.

## Legacy modernization

Povinné evidence: runtime topology, data stores, integration inventory, incident/change data, batch windows, release constraints, skrytá pravidla a provozní vlastníci.

Miro změny: business timeline oddělená od technického as-is, seam map, transition context map, reconciliation a decommission lane.

## Purchased product adoption

Modeluj odpovědnost organizace, nikoli interní agregáty produktu, které neovládáš. Zvlášť označ vendor language, canonical enterprise language a překlad v ACL.

## Architecture review

EventStorming není povinný. Použije se tam, kde je sporné, zda technická hranice odpovídá business chování. Findings musí být evidence-based.

## Rozhodovací otázky

1. Mění se primárně business, software, integrace, nebo ownership?
2. Musí běžet současný systém bez přerušení?
3. Je scope jeden produkt, nebo portfolio?
4. Je významná část řešení koupená?
5. Potřebujeme discovery, cílový návrh, review, nebo realizovatelnou migraci?
6. Jaké quality attributes mají architektonickou prioritu?
