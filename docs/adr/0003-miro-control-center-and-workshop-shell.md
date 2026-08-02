# ADR: Control Center, Artifact Registry a kanonický workshop shell

Status: Superseded in part by [ADR 0004](0004-miro-redline-traceability-and-frame-01.md)

Date: 2026-07-30

## Context

Human visual acceptance PR #8 ukázala dvě třídy problému:

- Control Center směšoval project/gate state, zralost artefaktu a původ obsahu;
- pracovní frames měly method guide a ukázku, ale neměly konzistentně vymezenou editovatelnou pracovní plochu ani method-specific definition of done, heuristiky a anti-patterns.

Baseline board `uXjVH2o4NRU=`, review target `uXjVH2vcvRI=` a metodický reference board `uXjVH27wYU4=` jsou návrhové vstupy. Nejsou release evidencí a remediation je nesmí modifikovat.

## Decision

Control Center zobrazuje tři nezávislé dimenze:

1. **Project / Gate State** — `not_ready`, `ready_for_review`, `conditional`, `rejected`, `passed`;
2. **Artifact Lifecycle** — `SCAFFOLD`, `WORKING`, `CANDIDATE`, `VALIDATED`, `ACCEPTED`, `SUPERSEDED`;
3. **Artifact Provenance** — `GENERATED`, `WORKSHOP`, `IMPORTED`, `MANUAL`.

Managed artefakty se promítají do jediného Artifact Registry:

```text
Artifact | Type | Stage | Lifecycle | Provenance | Owner | Revision | Last sync | Detail
```

Miro REST API v2 nepodporuje programové vytvoření ani aktualizaci obsahu nativní Miro Table. Renderer proto používá deterministický shape-grid a omezení deklaruje ve scaffold contractu. Nesmí tvrdit, že vytváří nativní tabulku.

Makro-layout používá deterministické stage columns. Frames `20–82` mají kanonický shell:

```text
method guide | editable work area | VZOR / LEGENDA
```

Method guide obsahuje účel, start, recept, definition of done, otevřené otázky, heuristiky, anti-patterns, výstupy, artefakty a zdroje. Editovatelná pracovní plocha má `sync_policy: manual`. `VZOR / LEGENDA`, jeho položky a connectors mají `sync_policy: ignore` a `exclude_from_ingestion: true`.

Původní rozhodnutí ponechat frames `01` a `10` interně nezměněné bylo pro frame `01` chybné: odporovalo explicitnímu human-review redline. ADR 0004 ruší tuto část rozhodnutí pro frame `01`. Frame `10` nadále nepoužívá kanonický shell bez samostatného schválení.

Human acceptance vždy probíhá na novém izolovaném boardu vytvořeném z exact candidate SHA.

Online acceptance nevěří samotnému lokálnímu mappingu. Board obsahuje viditelné provenance markery pro verzi render contractu, exact `source_commit` candidate package a SHA-256 scaffoldingu. Po renderu se z Miro API znovu načte vzdálený obsah, ověří se jeho povinné viditelné texty a uloží se `remote_content_digest`.

## Consequences

Positive:

- gate decision nelze zaměnit se zralostí nebo původem artefaktu;
- každý metodický frame `20–82` má konzistentní facilitační affordance;
- ruční projektová práce je vizuálně i synchronizačně oddělena od příkladu;
- layout a registry jsou reprodukovatelné z Git/YAML.

Negative:

- shape-grid obsahuje více Miro items než nativní tabulka;
- dlouhé hodnoty v registry musí být zkráceny a detail zůstává v source path;
- frame `10` nepoužívá nový shell, dokud nebude předmětem samostatně schválené změny.

New obligations:

- testy musí dokazovat přesně patnáct shell frames; frame `01` má samostatný parent/child overview kontrakt a frame `10` zůstává bez kanonického shellu;
- remote validation musí nezávisle na mappingu ověřit oddělené legendy, devět sloupců registru, patnáct viditelných shellů a method-specific guide sekce;
- acceptance musí svázat board s exact candidate SHA, scaffold hash a render contractem;
- dokumentace musí používat rozdílné termíny gate state, lifecycle a provenance;
- online human review nesmí používat baseline ani review-target board jako write target.

## Impact

Platform areas:

- Miro scaffold a renderer;
- schema;
- runtime a PowerShell testy;
- Miro product/cookbook/reference dokumentace;
- human visual acceptance.

Existing workspaces:

- managed YAML artefakty se nemění;
- historický konfigurační klíč `artifact_status_tables` zůstává kvůli kompatibilitě;
- existující board se aktualizuje jen při explicitním initializeru.

Migration:

- scaffold schema `2.2 → 2.4`; verze `2.4` doplňuje candidate-to-board provenance a baseline-regression guard;
- žádná automatická konverze projektových dat;
- human review používá nový izolovaný board.

## Validation

- JSON schema a repository validation;
- Miro runtime unit/component testy;
- deklarativní frame overlap a shell geometry contract;
- remote role/count/font/geometry validation doplněná o nezávislou kontrolu skutečně viditelného obsahu;
- negativní regrese, které ponechají mapping validní, ale poškodí remote provenance nebo workshop shell;
- PowerShell source-level contract;
- online technical Miro acceptance na exact SHA;
- samostatný human visual acceptance record.
