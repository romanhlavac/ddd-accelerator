# Miro DDD Starter traceability

## Účel

Tento dokument dokládá, jak scaffold `strategic-ddd-method-board.yaml` převádí metodický tok DDDA do auditovatelné Miro projekce.

Jde o deterministický vektorový ekvivalent vhodný pro verzování a automatizované testy. Binární Miro backup není součástí release package ani source of truth.

## Traceability matrix

| DDD Starter krok | DDDA stage | Gate | Primární frame | Typické managed evidence | Human acceptance |
|---|---|---|---|---|---|
| Align / Understand | `align` | G1 | `align-intake` | project charter, current status, next actions | problém, cíl, scope a decision owner jsou pochopeny |
| Discover | `discover` | G2 | `discover-big-picture-es` | Big Picture, glossary, hotspots | vznikl sdílený obraz dění a nejasností |
| Decompose | `decompose` | G3 | `decompose-domain` | kandidátní subdomény, BC a lifecycle | hranice mají explicitní rationale |
| Strategize | `strategize` | G4 | `strategize-classification` | core/supporting/generic, investment rationale | investiční fokus je vědomé rozhodnutí |
| Connect | `connect` | G5 | `connect-context-map` | context map, ownership, contracts | vztahy a source of truth jsou explicitní |
| Organise | `organize` | G6 | `organize-teams` | team topology, interaction modes | ownership je organizačně proveditelný |
| Define | `define` | G7 | `define-bounded-context` | BC canvas, design-level ES, lifecycle, QA scenarios | BC je připraven pro detailní návrh |
| Code | `code` | G8 | `code-tactical-model` | aggregates, invariants, events, ADR, C4 | implementace chrání model a quality attributes |

## Reference elements represented by the scaffold

Scaffold zachovává tyto referenční DDD Starter prvky jako editovatelné Miro objects:

- souvislou cestu od Align po Code;
- discovery přes Big Picture EventStorming;
- dekompozici podle jazyka, pravidel, lifecycle a změnového couplingu;
- strategickou klasifikaci core/supporting/generic;
- Context Map a data ownership;
- Team Topologies a interaction modes;
- Bounded Context Canvas;
- Design-Level EventStorming;
- tactical DDD a architektonická rozhodnutí.

Reference je použita pro metodickou orientaci a layout inspiraci. Autoritativní kontrakt je verzovaný YAML scaffold, JSON Schema, renderer, mapping a acceptance report.

## Automatizovaná evidence

Automatizované testy ověřují:

- přesně osm stage/gate kroků;
- všech pět gate stavů;
- Control Center;
- explicitní placement povinných artefaktů;
- stable journey item IDs;
- změnu current-gate highlight bez recreation;
- overlay guard;
- UTF-8 guard;
- technický PASS oddělený od `PENDING_HUMAN_REVIEW`.

## Lidská evidence

Finální reviewer ověřuje:

- čitelnost bez znalosti interní implementace;
- orientaci od Control Center k aktuálnímu frame;
- srozumitelnost statusu, decision question, ownera a blockerů;
- použitelnost workshop templates;
- nepřekrývání a čitelnost při fit-to-content;
- české znaky;
- že board nevytváří dojem automatického gate approval.
