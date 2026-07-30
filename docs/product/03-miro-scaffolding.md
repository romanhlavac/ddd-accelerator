# Miro scaffolding

## Účel

Scaffold není hotový doménový model ani dekorativní prezentace. Je to deterministická navigační, facilitační a auditní projekce DDDA projektu. Spojuje mapu DDD Starter Modelling Process, provozní Control Center a pracovní plochy pro discovery, strategic design, socio-technický návrh a tactical design.

Miro není autoritou pro gate approval. Git/YAML uchovává autoritativní artefakty a auditní evidenci; Miro slouží pro orientaci, exploraci a workshopovou spolupráci. Stav `passed`, `conditional` nebo `rejected` vzniká pouze explicitním human decision recordem v projektovém Gitu.

## Jak se board používá

Nový nebo příležitostný uživatel postupuje vždy stejně:

1. začne ve frame **`00 – Navigace, legenda a stav artefaktů (Control Center)`**;
2. zjistí aktuální stage, gate, decision question, blockery a next actions;
3. ve frame **`01 – DDD Starter journey, gates a iterace`** si ověří kontext celé metodiky a povolené návraty;
4. přejde do aktivního pracovního frame uvedeného u gate;
5. použije oddělený panel **`VZOR / LEGENDA – neexportuje se do YAML`** jako vizuální návod;
6. workshopový výsledek konsoliduje do managed YAML artefaktu;
7. automatizace připraví `ready_for_review`, ale gate rozhodne oprávněný člověk;
8. podle rozhodnutí pokračuje, doplní podmínku nebo se vrátí k dřívější hypotéze.

Kompaktní verze tohoto postupu je přímo v Control Center. Miro REST API v2 neposkytuje obecný collapse/expand kontejner, proto renderer používá kompaktní onboarding panel s odkazem na tento podrobný návod, nikoli neexistující skládací widget.

## Viditelná struktura boardu

Renderer vytváří:

1. **`00 – Navigace, legenda a stav artefaktů (Control Center)`**;
2. **`01 – DDD Starter journey, gates a iterace`**;
3. jednu horizontální osu osmi stage flow shapes a osmi samostatných gate diamonds `G1–G8`;
4. popsané Miro connectors mezi stage, gate a vyššími metodickými zónami;
5. čtyři zarovnané metodické zóny:
   - Align & Understand,
   - Strategic Architecture,
   - Strategy & Org Design,
   - Tactical Architecture;
6. sedm dopředných přechodů a explicitní feedback loops;
7. zarovnané pracovní frames s facilitačním návodem vlevo nahoře;
8. v každém pracovním frame oddělený metodicky specifický panel `VZOR / LEGENDA`;
9. odkazy na DDD Starter Modelling Process, DDDA metodiku, cookbooks a knowledge index.

Interní ID `control-center` zůstává stabilní pro mapping a synchronizaci. Viditelný název explicitně obsahuje označení Control Center.

## `00 – Navigace, legenda a stav artefaktů (Control Center)`

Frame musí na první pohled ukázat:

- project name a project ID;
- current stage a current gate;
- gate status;
- decision question, decision ownera a reviewer/approvera;
- chybějící nebo sporné evidence;
- doporučené next actions;
- project/source commit a poslední sync;
- kompaktní osmibodový návod k použití boardu;
- legendu všech pěti gate stavů;
- synchronizovaný přehled zralosti managed artefaktů.

Povinné managed artefakty mají stabilní placement:

```text
project-charter       → control-center
ddda.current-status   → control-center
ddda.next-actions     → control-center
```

### Přehled stavů artefaktů

Miro REST API v2 aktuálně neposkytuje endpoint pro vytvoření nativní Miro tabulky. Renderer proto používá deterministický vizuální table-grid složený z Miro shapes. Mřížka je naplněna z managed YAML a rozlišuje například scaffold, generated, workshop/candidate, validated, accepted a superseded.

Tato projekce nesmí být zaměněna s gate statusy. `validated` artefakt může existovat i při gate `not_ready`; gate vyhodnocuje úplnost evidence a lidské rozhodnutí, nikoli pouze zralost jedné položky.

## `01 – DDD Starter journey, gates a iterace`

Přehled je skutečný flow diagram, nikoli pás generických rounded rectangles:

- stage používají stabilní základní flow shapes podporované Miro REST API;
- každá gate je samostatný rhombus;
- stage → gate a gate → následující stage jsou spojeny Miro connectors s textovými captions;
- vyšší metodické zóny leží na jedné vizuální baseline a mají vlastní popsané connectors;
- feedback loops jsou odlišeny zakřiveným nebo přerušovaným connector stylem;
- příklady výstupů používají odpovídající typy prvků, zejména sticky notes pro EventStorming a table-grid pro slovníky či klasifikace;
- resource panel odkazuje na základní DDD Starter metodiku, DDDA metodiku, cookbooks a knowledge index.

Základní reference:

- [DDD Starter Modelling Process – Kicking off a major program of work](https://ddd-crew.github.io/ddd-starter-modelling-process/#kicking-off-a-major-program-of-work)
- [DDDA metodický tok a gates](../methodology/01-metodicky-tok-a-gates.md)
- [DDDA workshopové cookbooks](../cookbooks/)
- [DDDA knowledge index](../../knowledge/00-knowledge-index.md)

Přehled musí působit jako iterativní rozhodovací mapa, nikoli jako rigidní waterfall.

## Gate states

| Stav | Symbol | Význam |
|---|---:|---|
| `not_ready` | ⛔ | chybí povinné evidence nebo owner |
| `ready_for_review` | ◉ | mechanicky připraveno k lidskému review |
| `conditional` | △ | lidské rozhodnutí s podmínkou, ownerem a termínem; gate není dokončena |
| `rejected` | ✕ | lidské rozhodnutí gate odmítlo |
| `passed` | ✓ | explicitní lidské schválení |

Rozlišení je založeno na symbolu, plném textovém labelu, významu a barvě. Barva je pouze podpůrná.

## Workshop frames

Každý pracovní frame má tři jasně oddělené části.

### Facilitační návod vlevo nahoře

- účel;
- jak začít;
- očekávané výstupy;
- povinné pracovní oblasti;
- odkazy na DDDA cookbook, metodiku a DDD Starter reference.

### Projektová pracovní plocha

Tato část je určena pro skutečný workshopový obsah projektu. Stabilní výsledek se konsoliduje do managed YAML; renderer nesmí ruční exploraci automaticky vydávat za přijatý artefakt.

### `VZOR / LEGENDA – neexportuje se do YAML`

Jde o samostatně ohraničený vizuální subframe vytvořený jako stabilní panel uvnitř pracovního frame. Není to klientský model ani evidence. Mapping nese explicitní kontrakt:

```yaml
managed: false
sync_policy: ignore
exclude_from_ingestion: true
```

Stejný kontrakt mají všechny položky a connectors uvnitř panelu. Miro → YAML sync je musí ignorovat i při `promote_new`.

Mini-vzor odpovídá použité metodě:

- Big Picture EventStorming: barevné sticky notes, event timeline, commands, policies, actors/systems, hotspots a questions;
- Process Modeling: actor → command → policy → event → read model;
- Decompose: clustery, kandidátní subdomény, boundary hypotheses a alternativy;
- Lifecycle: states, commands/events, guards a zakázané přechody;
- Strategize: core/supporting/generic a build/buy/SaaS table-grid;
- Context Map: upstream/downstream contexts, contract, ACL a data ownership;
- Team Topologies: týmové ownership a interaction modes;
- Bounded Context Canvas a quality attributes: strukturovaný table-grid;
- Design-Level EventStorming: commands, policies, aggregates, events a projections;
- Code: aggregates, state machine, C4, kontrakty a ADR.

## Idempotence a zachování ruční práce

Opakovaný render:

- používá stabilní item IDs z `miro/miro-map.yaml`;
- aktualizuje existující frames, shapes, sticky notes, texts a connectors;
- nevytváří nový board;
- zachovává stabilní journey, gate, zone a example IDs;
- odstraní pouze zastaralé systémové prvky předchozí verze scaffoldu;
- nemaže unmanaged workshopový obsah;
- při běžném syncu nepřepisuje ručně upravený layout managed artefaktu bez explicitního `--include-layout`;
- ignoruje všechny `sync_policy: ignore` example panely, položky a connectors.

## Dvojí layout validace

### Deklarativní kontrakt

Před zápisem ověřuje YAML:

- rozměry, minimální fonty, zarovnání a mezery;
- G1–G8, gate diamonds, stage flow, čtyři zarovnané zóny a jejich connectors;
- sedm dopředných přechodů a nejméně dvě feedback loops;
- onboarding, resource links a artifact-status table contract;
- guide a metodicky specifický example panel v každém pracovním frame;
- explicitní `sync_policy: ignore` a `exclude_from_ingestion`;
- placement managed artefaktů a zákaz DDDA-rendered blocking overlay.

### Remote Miro kontrakt

Po renderu renderer načte skutečné Miro items i connectors a ověří:

- geometrii a pozice frames;
- nepřekrývání pracovních frames;
- osm stage shapes a osm gate diamonds;
- skutečné stage/gate, zone, forward a feedback connectors;
- situační prvky pro všech osm stages;
- pět čitelných gate-state karet;
- top-left workshop guides;
- oddělený example panel a jeho sync-ignore metadata;
- resource panel a synchronizovaný artifact-status table-grid.

Výsledek se ukládá jako `remote_layout_status` a `remote_layout_evidence`.

## Developer-team watermark

Velký nápis `Developer team` není prvek renderovaný DDDA a není dostupný jako Miro board item. Je vlastností Miro Developer team prostředí. Pro finální vizuální review se board vytváří v explicitně zvoleném standardním teamu pomocí `-MiroTeamId`; report pak musí uvést `review_team_selection_status: EXPLICIT_TEAM`.

## Acceptance contract

```text
technical_sync_status: PASS
layout_contract_status: PASS
remote_layout_status: PASS
utf8_status: PASS
human_visual_acceptance_status: PENDING
overall_status: PENDING_HUMAN_REVIEW
```

Technický PASS není vizuální ani metodický human PASS. Finální lidské review se provádí nad novým izolovaným boardem a exact SHA.
