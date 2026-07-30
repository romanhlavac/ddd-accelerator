# Miro DDD Starter traceability

## Účel

Tento dokument dokládá, jak `strategic-ddd-method-board.yaml` převádí [DDD Starter Modelling Process](https://ddd-crew.github.io/ddd-starter-modelling-process/#kicking-off-a-major-program-of-work) do auditovatelné Miro projekce.

Uživatelem dodaný referenční board a DDD Starter vizuály jsou návrhovým vstupem. Release package používá deterministický, editovatelný ekvivalent z Miro shapes, sticky notes, textů a connectors. Board nesmí být pouze souborem prázdných frames ani generických obdélníků.

## Navigační traceability

```text
Control Center onboarding
→ vyšší metodická zóna
→ stage flow shape
→ gate diamond
→ popsaný connector
→ pracovní frame
→ method guide / editovatelná pracovní plocha
→ VZOR / LEGENDA
→ managed YAML artefakt
→ human gate decision
```

Vyšší zóny jsou na jedné vizuální baseline a mají popsané connectors:

```text
Align & Understand
→ Strategic Architecture
→ Strategy & Org Design
→ Tactical Architecture
```

Stage/gate flow je doplněn explicitními feedback loops, aby board nesugeroval rigidní waterfall.

## Traceability matrix

| DDD Starter krok | DDDA stage | Gate | Viditelný pracovní frame | Metodicky specifický vzor | Human acceptance |
|---|---|---|---|---|---|
| Align / Understand | `align` | G1 | `10 – Align / Intake` | problém, cíl, scope, owner a evidence | problém, cíl, scope a decision owner jsou pochopeny |
| Discover | `discover` | G2 | `20 – EventStorming: Big Picture` | EventStorming sticky notes, event timeline, command, policy, hotspot a otázka | vznikl sdílený obraz dění a nejasností |
| Decompose | `decompose` | G3 | `30 – Rozklad domény` | clustery, subdomény, boundary hypotheses a alternativy | hranice mají explicitní rationale |
| Strategize | `strategize` | G4 | `40 – Strategická klasifikace` | core/supporting/generic a build/buy/SaaS table-grid | investiční fokus je vědomé rozhodnutí |
| Connect | `connect` | G5 | `50 – Context Map a data ownership` | upstream/downstream, contract connector, ACL a data owner | vztahy a source of truth jsou explicitní |
| Organise | `organize` | G6 | `60 – Team Topologies` | týmové ownership a interaction-mode vztahy | ownership je organizačně proveditelný |
| Define | `define` | G7 | `70 – Bounded Context Canvases` | canvas grid, lifecycle, Design-Level ES a quality scenarios | BC je připraven pro detailní návrh |
| Code | `code` | G8 | `80 – Taktický DDD a architektura` | agregáty, state machine, C4, contracts a ADR | implementace chrání model a quality attributes |

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

## Vzor versus projektová evidence

Každý pracovní frame obsahuje oddělený panel:

```text
VZOR / LEGENDA – neexportuje se do YAML
```

Panel, jeho položky a connectors mají v mappingu:

```yaml
managed: false
sync_policy: ignore
exclude_from_ingestion: true
```

Sync tento obsah explicitně ignoruje i při `promote_new`. Vzor vysvětluje formu práce, ale nesmí se stát managed projektovým artefaktem ani splnit gate evidence.

Frames `20–82` mají navíc jednotný třízónový shell. Method guide obsahuje method-specific recept, definition of done, otevřené otázky, heuristiky a anti-patterns; střední pracovní plocha je určena pro ruční projektový obsah a má `sync_policy: manual`. Frames `01` a `10` se interně nemění.

## Tabulkové projekce

Slovníky, evidence inventory, strategické klasifikace, canvas a quality-attribute přehledy používají deterministický table-grid ze shapes. Důvodem je, že Miro REST API v2 neposkytuje endpoint pro vytvoření nativní Miro tabulky. Omezení je explicitní ve scaffold contractu a nesmí být maskováno tvrzením, že renderer vytváří nativní tabulku.

## Automatizovaná evidence

Testy ověřují:

- kompaktní first-user onboarding a pět základních metodických odkazů;
- osm stage flow shapes a osm gate diamonds;
- čtyři zarovnané vyšší zóny a tři zone connectors;
- sedm dopředných stage/gate přechodů a nejméně dvě feedback loops;
- minimální fonty, rozměry, rozestupy a nepřekrývání;
- metodicky specifické sticky notes, shapes a table-grid příklady;
- oddělený example panel ve všech pracovních frames;
- kanonický třízónový shell přesně v patnácti frames `20–82`;
- absenci nového workspace shellu ve frames `01` a `10`;
- explicitní sync-ignore a ingestion-exclusion kontrakt pro vzory i jejich connectors;
- oddělení pěti Project/Gate State hodnot, šesti Artifact Lifecycle hodnot a čtyř Artifact Provenance hodnot;
- jeden Artifact Registry se sloupci `Artifact`, `Type`, `Stage`, `Lifecycle`, `Provenance`, `Owner`, `Revision`, `Last sync` a `Detail`;
- remote Miro geometrii a skutečné connector IDs po renderu;
- stabilní item IDs a current-gate highlight bez recreation;
- UTF-8;
- oddělení technical PASS od human visual acceptance.

## Lidská evidence

Reviewer ověřuje:

- že lze bez externího výkladu zjistit, kde začít a kde projekt právě je;
- `00 – Control Center / Project State / Artifact Registry`;
- `01 – DDD Starter journey, gates a iterace`;
- čitelnost stages, gates, zone flow a popisků connectorů;
- zda vizuální typy odpovídají metodě, například sticky notes pro EventStorming;
- zda je projektová pracovní plocha jasně oddělena od `VZOR / LEGENDA`;
- použitelnost method guides, editovatelných pracovních ploch, resources a Artifact Registry;
- nepřekrývání, přiměřenou hustotu a české znaky;
- že board nevytváří dojem automatického gate approval.
