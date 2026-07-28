# Miro DDD Starter traceability

## Účel

Tento dokument dokládá, jak `strategic-ddd-method-board.yaml` převádí DDD Starter Modelling Process do auditovatelné Miro projekce.

Uživatelem dodaný referenční board a jeho situační obrázky jsou návrhovým vstupem. Release package používá deterministický vektorový ekvivalent, protože musí být verzovatelný, testovatelný a editovatelný. Nejde pouze o osm prázdných frames: každá fáze má situační kartu, mini-vzor artefaktů, návod a metodické odkazy.

## Traceability matrix

| DDD Starter krok | DDDA stage | Gate | Viditelný pracovní frame | Vektorová situace a vzor | Human acceptance |
|---|---|---|---|---|---|
| Align / Understand | `align` | G1 | `10 – Align / Intake` | problém, cíl, owner, evidence; problem/decision/scope mini-vzor | problém, cíl, scope a decision owner jsou pochopeny |
| Discover | `discover` | G2 | `20 – EventStorming: Big Picture` | event, command, hotspot, otázka; Big Picture mini-vzor | vznikl sdílený obraz dění a nejasností |
| Decompose | `decompose` | G3 | `30 – Rozklad domény` | doména, subdoména, hranice, alternativa | hranice mají explicitní rationale |
| Strategize | `strategize` | G4 | `40 – Strategická klasifikace` | core/supporting/generic/build-buy-SaaS | investiční fokus je vědomé rozhodnutí |
| Connect | `connect` | G5 | `50 – Context Map a data ownership` | upstream, kontrakt, downstream, data owner | vztahy a source of truth jsou explicitní |
| Organise | `organize` | G6 | `60 – Team Topologies` | stream-aligned, platform, enabling, interaction | ownership je organizačně proveditelný |
| Define | `define` | G7 | `70 – Bounded Context Canvas` | purpose, language, lifecycle, invariant | BC je připraven pro detailní návrh |
| Code | `code` | G8 | `80 – Taktický DDD a architektura` | aggregate, event, ADR/C4, operability | implementace chrání model a quality attributes |

Každý řádek je ve scaffoldu dohledatelný přes:

```text
reference_visual
→ stage
→ gate
→ work_frame
→ example_template
→ cookbook_url / method_url / starter_reference_url
→ human_acceptance
```

## Iterativnost

Přehled obsahuje celý dopředný tok a explicitní návraty, minimálně:

- Discover → Align, pokud nová evidence mění problém nebo scope;
- Define → Decompose, pokud detail odhalí chybnou boundary hypothesis.

Tím se zamezuje dojmu rigidního waterfall procesu.

## Automatizovaná evidence

Testy ověřují:

- osm stage/gate karet a čtyři metodické zóny;
- minimální fonty journey, legendy, guides a mini-vzorů;
- nejméně čtyři situační prvky na gate;
- top-left guide a metodické odkazy v každém pracovním frame;
- neprázdné mini-vzory;
- zarovnání, minimální rozestupy a nepřekrývání frames;
- actual remote geometry po renderu do Miro;
- stable item IDs a změnu current-gate highlight bez recreation;
- UTF-8;
- oddělení technical PASS od human visual acceptance.

## Lidská evidence

Reviewer používá viditelné názvy boardu a ověřuje:

- `00 – Navigace, legenda a stav artefaktů`;
- `01 – DDD Starter journey, gates a iterace`;
- čitelnost stage/gate karet bez extrémního zoomu;
- metodické seskupení a návratové smyčky;
- použitelnost guides, mini-vzorů a odkazů;
- nepřekrývání a přiměřenou hustotu;
- české znaky;
- že board nevytváří dojem automatického gate approval.
