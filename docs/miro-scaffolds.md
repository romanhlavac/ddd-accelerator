# Miro scaffoldy DDDA podle referenčního boardu Strategic DDD

## Účel

Tento dokument definuje rozložení Miro boardu pro DDDA a pozici jednotlivých modelovacích technik v metodickém toku. Referenční `.rtb` board používá tři důležité vizuální principy:

1. metodický tok je viditelný jako celek,
2. EventStorming je rozdělen podle účelu a úrovně detailu,
3. detailní modely vznikají až po předchozí discovery a vymezení hranic.

Scaffold proto není „galerie šablon“. Je to pracovní plocha, která vede uživatele zleva doprava a přes explicitní gaty.

## Metodický tok boardu

```text
Align
  → Discover
  → Decompose
  → Strategize
  → Connect
  → Organize
  → Define
  → Code
```

Horní pás boardu obsahuje pouze navigační karty fází a gaty. Pracovní artefakty jsou v samostatných framech pod nimi. Každý frame má stabilní DDDA ID, cestu k YAML artefaktu, stav validace a Git revizi.

## EventStorming: přesná pozice v toku

### Big Picture EventStorming — `Discover`

Big Picture ES je hlavní discovery plocha. Vzniká po základním Align/Intake a před návrhem subdomén nebo bounded contexts.

Obsah:

- doménové události v časové ose,
- časové a pivotní události,
- aktéři a externí systémy,
- hotspoty,
- otevřené otázky,
- hodnotové signály.

**Gate G2:** bez dostatečně širokého Big Picture modelu se nesmí bounded contexts vydávat za návrh architektury.

### Process Modeling — přechod `Discover → Decompose`

Process Modeling se nepoužívá automaticky pro celou doménu. Zaměřuje se na vybraný hodnotný, nejasný nebo rizikový úsek z Big Picture.

Sekvence ve scaffoldu:

```text
aktér → command/action → policy/procedure → systém/agregát → event → read model
```

Výstupem jsou procesní řezy, pravidla, rozhodnutí a datové potřeby. Ty se používají při rozkladu domény, nikoli jako přímý návrh mikroservis.

### Design-Level EventStorming — `Define`

Design-Level ES vzniká až pro vybraný bounded context, typicky core nebo komplexní supporting context. Je umístěn za Bounded Context Canvas a před taktickým návrhem.

Zobrazuje:

- příkazy a rozhodnutí,
- policies/procedures,
- kandidátní agregáty,
- invarianty,
- doménové události,
- projekce/read modely,
- externí závislosti.

Design-Level ES nesmí vytvářet distribuovanou transakci přes více bounded contexts.

## Stavové a lifecycle modely: přesná pozice v toku

„Stavový obrázek“ není jeden artefakt. V toku existují čtyři různé úrovně:

| Úroveň | Fáze | Účel | Status |
|---|---|---|---|
| Pozorované stavy | Discover | zachytit stavy a přechody nalezené ve zdrojích a Big Picture | fakta + nejistoty |
| Kandidátní lifecycle | Decompose | porovnat pravidla, vlastníky a tempo změn; pomoci hledat hranice | hypotéza |
| Validovaný stavový model | Define | potvrdit povolené a zakázané přechody, command/event vazby, invarianty a autorizaci | doménový návrh |
| Implementační state machine | Code | popsat technickou realizaci, pouze pokud explicitní state machine přináší hodnotu | implementační rozhodnutí |

### Praktické pravidlo

Stavový diagram patří do `Define`, pokud stav řídí business chování nebo existují zakázané přechody. Do `Code` se kopíruje pouze jako odvozený implementační pohled. Ne každé pole `status` ospravedlňuje state-machine framework.

## Vizuální vzor

Scaffold zachovává barevnou sémantiku referenčního boardu:

| Prvek | Barva |
|---|---|
| Domain event | oranžová |
| Command / action | modrá |
| Policy / procedure | fialová |
| Read model / projection | zelená |
| External system | růžová |
| Actor | žlutá |
| Hotspot | červená |
| Invariant | světle žlutá |

Legenda je vlevo v každém ES frame. Big Picture má širokou vodorovnou časovou osu. Process Modeling používá řádky procesních scénářů. Design-Level ES používá kompaktní smyčku command → decision/invariant → event → projection.

## Gaty

Gaty nejsou formální schválení pro každou drobnost. Brání předčasnému posunu na další úroveň modelu.

- **G1:** cíl, scope, stakeholdery a předpoklady jsou explicitní.
- **G2:** Big Picture, slovník, hotspoty a pozorované lifecycle poskytují dostatek evidence.
- **G3:** kandidátní subdomény a lifecycle jsou validovatelné hypotézy.
- **G4:** core/supporting/generic a investiční přístup jsou přijaté.
- **G5:** context map, data ownership a integrační vztahy jsou explicitní.
- **G6:** týmové ownership je proveditelné bez neúnosné kognitivní zátěže.
- **G7:** bounded contexts, Design-Level ES a lifecycle jsou připravené pro taktický návrh.
- **G8:** agregáty, invarianty, kontrakty a ADR tvoří implementovatelný celek.

## Synchronizace s YAML a Gitem

Každý spravovaný Miro prvek má metadata:

```yaml
dd_d_a_id: stable-uuid
dd_d_a_artifact_type: domain-event
dd_d_a_source_path: projects/acme/artifacts/domain-events.yaml
dd_d_a_revision: git-sha
dd_d_a_stage: discover
dd_d_a_status: validated
dd_d_a_managed: true
```

Rozdělení vlastnictví:

- YAML vlastní identitu, sémantický obsah a traceability.
- Miro vlastní pozici, velikost, seskupení a workshopové poznámky.
- Editovatelný business text ve spravovaných prvcích se synchronizuje oběma směry.
- Konflikt stejného pole na obou stranách se neslučuje „last write wins“; vytvoří se explicitní review položka.
- Hotspoty, komentáře a volné sticky notes se nejdříve ingestují jako návrhy, ne jako automaticky přijatá fakta.

## Mermaid analogie

Každý přijatý model má paralelní `.mmd` výstup pro chat, diff a dokumentaci:

- Big Picture: zjednodušená event timeline,
- lifecycle: `stateDiagram-v2`,
- context map: `flowchart`,
- Design-Level ES: `flowchart LR`,
- team topology: `flowchart TB`.

Miro zůstává primární kolaborativní plocha; Mermaid je verzovatelný, textový a snadno reviewovatelný pohled.
