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
7. deterministické stage columns s vlastnictvím pracovních frames: Control, Align, Discover, Decompose, Strategize, Connect, Organize, Define a Code;
8. ve frames `20–82` kanonický třízónový shell: method guide, editovatelná pracovní plocha a metodicky specifický panel `VZOR / LEGENDA`;
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
- explicitně oddělené `Project / Gate State`, `Artifact Lifecycle` a `Artifact Provenance`;
- jediný synchronizovaný Artifact Registry pro managed artefakty.

Povinné managed artefakty mají stabilní placement:

```text
project-charter       → control-center
ddda.current-status   → control-center
ddda.next-actions     → control-center
```

### Tři nezávislé stavové dimenze

| Dimenze | Hodnoty | Význam |
|---|---|---|
| Project / Gate State | `not_ready`, `ready_for_review`, `conditional`, `rejected`, `passed` | stav rozhodovacího bodu projektu |
| Artifact Lifecycle | `SCAFFOLD`, `WORKING`, `CANDIDATE`, `VALIDATED`, `ACCEPTED`, `SUPERSEDED` | zralost artefaktu |
| Artifact Provenance | `GENERATED`, `WORKSHOP`, `IMPORTED`, `MANUAL` | původ obsahu |

Žádná z dimenzí se neodvozuje z jiné. Například artefakt může být `VALIDATED`, pocházet z `WORKSHOP`, ale gate stále zůstane `not_ready`, pokud chybí jiná evidence.

### Artifact Registry

Miro REST API v2 nepodporuje programové vytvoření ani aktualizaci obsahu nativní Miro Table. Renderer proto používá deterministický vizuální shape-grid. Registry je naplněn z managed YAML a má sloupce:

```text
Artifact | Type | Stage | Lifecycle | Provenance | Owner | Revision | Last sync | Detail
```

Historický konfigurační klíč `artifact_status_tables` zůstává kvůli kompatibilitě, ale jeho aktuální kontrakt reprezentuje jeden Artifact Registry, nikoli sadu statusových tabulek.

## `01 – DDD Starter journey, gates a iterace`

Přehled je skutečný flow diagram, nikoli pás generických rounded rectangles:

- stage používají stabilní základní flow shapes podporované Miro REST API;
- každá gate je samostatný rhombus;
- stage → gate a gate → následující stage jsou spojeny Miro connectors s textovými captions;
- vyšší metodické zóny leží na jedné vizuální baseline a mají vlastní popsané connectors;
- feedback loops jsou odlišeny zakřiveným nebo přerušovaným connector stylem;
- příklady výstupů používají odpovídající typy prvků, zejména sticky notes pro EventStorming a table-grid pro slovníky či klasifikace;
- resource panel odkazuje na základní DDD Starter metodiku, DDDA metodiku, cookbooks a knowledge index.
- všechny uvedené prvky mají parent nastavený na remote ID frame `01`, takže navigace na frame zobrazí jeho skutečný obsah;
- osm source cards propojuje stages s konkrétními artefakty boardu `uXjVH27wYU4=` a uvádí redline source `uXjVH2vcvRI=`.

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

## Workshop frames `20–82`

Každý frame `20–82` má tři jasně oddělené části. Frame `10` zůstává bez kanonického shellu. Frame `01` je od REM-010 obsahově přepracovaný podle redline boardu `uXjVH2vcvRI=`: journey, gates, stage visuals, zones, resources a osm source cards jsou skutečné children frame, nikoli top-level položky položené přes jeho geometrii.

### Facilitační návod vlevo nahoře

- účel;
- jak začít;
- opakovatelný recept;
- definition of done a otevřené otázky;
- metodické heuristiky a anti-patterns;
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
- pro frame `01` vynucuje samostatný parent/child overview kontrakt a pro frame `10` zachovává absenci kanonického shellu;
- zobrazuje exact read-only traceability na redline board `uXjVH2vcvRI=` a DDD Starter board `uXjVH27wYU4=`;
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
- onboarding, resource links a oddělení Project/Gate State, Artifact Lifecycle a Artifact Provenance;
- kanonický třízónový shell přesně ve frames `20–82`;
- recept, definition of done, otevřené otázky, heuristiky a anti-patterns v method guide;
- metodicky specifický example panel v každém pracovním frame;
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
- patnáct editovatelných pracovních ploch ve frames `20–82`, nejméně 61 child items ve frame `01` a žádnou novou shell plochu ve frame `10`;
- oddělený example panel a jeho sync-ignore metadata;
- samostatnou lifecycle a provenance legendu;
- jeden Artifact Registry s devíti deklarovanými sloupci.
- viditelné provenance markery pro render contract, exact candidate SHA a scaffold SHA-256;
- nejméně 280 vzdálených items, aby 262položkový odmítnutý board nemohl projít jako REM-010;
- nejméně jedenáct viditelných vazeb `VZOR / LEGENDA` na konkrétní frames DDD Starter boardu;
- přesně patnáct viditelných pracovních ploch a patnáct výskytů každé povinné guide sekce;
- `remote_content_digest` vypočtený z reálně načtených systémových položek.

Výsledek se ukládá jako `remote_layout_status` a `remote_layout_evidence`.

## Developer-team watermark

Velký nápis `Developer team` není prvek renderovaný DDDA a není dostupný jako Miro board item. Je vlastností Miro Developer team prostředí. Pro finální vizuální review se board vytváří v explicitně zvoleném standardním teamu pomocí `-MiroTeamId`; report pak musí uvést `review_team_selection_status: EXPLICIT_TEAM`.

## Acceptance contract

```text
technical_sync_status: PASS
layout_contract_status: PASS
remote_layout_status: PASS
render_contract_status: PASS
render_contract_version: REM-PR8-HVA-CC-010
platform_source_commit: <40-char SHA>
scaffold_sha256: <64-char SHA-256>
remote_item_count: 280+
overview_child_count: 61+
starter_reference_caption_count: 11+
remote_content_digest: <64-char SHA-256>
utf8_status: PASS
human_visual_acceptance_status: PENDING
overall_status: PENDING_HUMAN_REVIEW
```

Technický PASS není vizuální ani metodický human PASS. Finální lidské review se provádí nad novým izolovaným boardem a exact SHA.
