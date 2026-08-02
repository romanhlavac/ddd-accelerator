# ADR: Redline traceability a navigovatelný frame 01

Status: Accepted

Date: 2026-08-02

Supersedes: část [ADR 0003](0003-miro-control-center-and-workshop-shell.md), která zachovávala frame `01` interně beze změny.

## Context

Human review odmítlo board vytvořený kontraktem `REM-PR8-HVA-CC-002`. Technická acceptance byla zelená, ale neprokazovala obsahovou shodu se dvěma autoritativními read-only vstupy:

- redline board `uXjVH2vcvRI=`;
- DDD Starter reference board `uXjVH27wYU4=`.

Forenzní kontrola ukázala, že redline frame `01` obsahuje 82 položek, zatímco odmítnutý review board měl všechny journey prvky jako top-level položky a frame `01` neměl žádné vlastní child items. Testy ověřovaly globální počty, texty a geometrii, ne parent vazbu. Zároveň scaffold citoval obecnou webovou metodiku, ale neuváděl konkrétní zdrojové frames a artefakty z dodaného DDD Starter boardu.

## Decision

Render contract `REM-PR8-HVA-CC-010` zavádí tyto povinnosti:

1. Frame `01` je samostatný navigovatelný overview. Journey cards, gate diamonds, stage mini-vzory, zone headers, resource panel a osm source cards musí mít parent nastavený na remote ID frame `01`.
2. Remote acceptance ověřuje nejméně 61 child items ve frame `01`; top-level položka uvnitř jeho geometrických hranic se za child item nepovažuje.
3. Redline a DDD Starter board jsou ve scaffoldu evidovány exact board ID a `mode: read_only`.
4. Každá stage G1–G8 uvádí konkrétní zdrojový frame a artefakty DDD Starter boardu.
5. Nejméně jedenáct workshopových example templates uvádí source frame URL, název a popis adaptace. Zdrojová vazba je viditelná přímo v panelu `VZOR / LEGENDA`.
6. Příklady reprodukují rozpoznatelné artefakty zdrojového boardu, zejména devítipolový Business Model Canvas, EventStorming timeline, Process Modelling, Problem Space → Solution Space, Strategic Classification matrix, Context Map notaci, Bounded Context Canvas a Domain Message Flow.
7. Parent je součástí remote content digestu, takže odpojení položek z frame `01` poruší idempotence evidence.
8. Human visual acceptance zůstává `PENDING`; automatizace nesmí z těchto kontrol odvodit lidské schválení.

Miro REST API používané distribuovaným runtime nadále neumí reprodukovat nativní Miro Table. Artifact Registry proto zůstává deterministický shape-grid s viditelnými borders, headers a devíti sloupci. Toto omezení nesmí být prezentováno jako nativní tabulka.

## Consequences

Positive:

- navigace na frame `01` zobrazí skutečný obsah, ne prázdný kontejner;
- zdrojová inspirace je vizuálně viditelná a strojově auditovatelná;
- technický PASS už nemůže vzniknout pouze z globálního počtu položek;
- review lze provést proti položkové traceability matici.

Negative:

- board obsahuje více položek a render je delší;
- zdrojové názvy a URL jsou součástí verzovaného kontraktu;
- změna parent vazeb změní remote content digest i bez změny textu.

## Validation

- JSON schema `2.5`;
- unit test parent vazeb a negativní test detached journey item;
- source-level PowerShell kontrakt;
- online acceptance s nezávislým načtením remote frame `01`, child countem a viditelnými source captions;
- exact candidate SHA a scaffold SHA-256;
- samostatný HUMAN REVIEW bez automatického gate decision.
