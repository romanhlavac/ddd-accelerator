# Forenzní review REM-PR8-HVA-CC-001

Status: remediation implementation replaced; online acceptance pending

Date: 2026-07-30

Issue: #14

PR: #8

Původní remote candidate: `b54668e9a1e1b763bb8485c8bb16639dfa4954d2`

Původní lokální ekvivalent: `02c6bdc3b506b36d913d8dae33f10128fde55d93`

## Executive summary

Technický `PASS` původního REM nebyl důkazem, že požadovaná vizuální změna vznikla na review boardu. Přímá inspekce Miro API prokázala, že board `uXjVH2DemOk=` je obsahově téměř totožný s baseline `uXjVH2o4NRU=`.

Původní implementace deklarovala nový Control Center, Artifact Registry a kanonický workshop shell, ale acceptance kontrolovala především role a počty z lokálního `miro-map.yaml`. Nezávisle neověřila, že požadované texty a plochy jsou skutečně přítomné ve vzdáleném boardu. Vznikl kruhový důkaz a falešně pozitivní výsledek.

Původní změna je proto oddělena explicitním revert commitem a nahrazena korekcí `REM-PR8-HVA-CC-002`. Historický board zůstává beze změny jako diagnostická evidence.

## Vstupy

Read-only Miro vstupy deklarované původním REM:

| Role | Board ID | Použití |
|---|---|---|
| Baseline | `uXjVH2o4NRU=` | stav před vizuální remediací |
| Review target | `uXjVH2vcvRI=` | ručně dopracovaný referenční cíl |
| Method reference | `uXjVH27wYU4=` | metodický vizuální vzor |
| Vadný acceptance board | `uXjVH2DemOk=` | evidence původního falešného PASS |

Metodický obsah byl znovu porovnán s workshop playbooky, strategic/tactical DDD, quality attributes a output templates použitými jako zdrojové materiály. Recepty, definition of done, otázky, heuristiky a anti-patterns jsou method-specific; problém byl v jejich nedoloženém remote renderu.

## Forenzní měření boardů

| Metrika | Baseline | Vadný acceptance board | Review target |
|---|---:|---:|---:|
| Items | 211 | 211 | 399 |
| Frames | 18 | 18 | 29 |
| Text | 36 | 36 | 54 |
| Shapes | 134 | 134 | 145 |
| Sticky notes | 23 | 23 | 149 |
| Images | 0 | 0 | 21 |
| Data tables | 0 | 0 | 1 |

Přesná shoda `type + visible content` mezi baseline a vadným acceptance boardem je `206 / 211`, tedy `97,6 %`.

Detail podle rozsahu:

- Control Center: `19 / 23` child items obsahově beze změny (`82,6 %`);
- frame `10`: `100 %` child content beze změny;
- všechny pracovní frames `20–82`: `100 %` child content beze změny;
- makro pozice frames se změnila do stage columns, ale většina požadovaného obsahu se na board nepropsala.

Na vadném acceptance boardu nebyl nalezen žádný výskyt:

- `EDITOVATELNÁ PRACOVNÍ PLOCHA`;
- `RECEPT`;
- `HOTOVO KDYŽ`;
- `HEURISTIKY`;
- `ANTI-PATTERNS`;
- `ARTIFACT LIFECYCLE`;
- `ARTIFACT PROVENANCE`;
- hlavičky devítisloupcového Artifact Registry.

## Požadavek versus skutečnost

| Původní REM požadavek | Co bylo implementováno ve zdroji | Co prokázal remote board | Závěr | Korekce |
|---|---|---|---|---|
| Redesign frame `00` na Control Center + Artifact Registry | Renderer a scaffold obsahovaly nové role a shape-grid | board zůstal převážně původní; registry nebyl viditelný | FAIL | viditelné markery, 45 registry cells a přímá remote kontrola 9 sloupců |
| Oddělit Gate State, Lifecycle a Provenance | tři samostatné role v rendereru | lifecycle/provenance texty na boardu chyběly | FAIL | přímé hledání všech tří dimenzí v Miro API snapshotu |
| Deterministické stage columns | souřadnice a vlastnictví frames byly změněny | makro pozice se skutečně změnila | PASS | zachováno a dále kontrolováno geometrií |
| Třízónový shell ve frames `20–82` | renderer deklaroval 15 workspace panelů | všechny pracovní frames byly obsahově shodné s baseline | FAIL | přesně 15 viditelných workspace markerů a 15 mapping rolí |
| Frames `01` a `10` interně zachovat | renderer jim nepřidával canonical shell | obsah zůstal zachován | PASS | explicitní negativní invariant zůstává |
| Method-specific guides | YAML obsahoval specifické recepty, DoD, otázky, heuristiky a anti-patterns | na boardu nebyl ani jeden povinný heading | FAIL | každý heading musí být viditelný v přesně 15 guide položkách |
| Method-specific examples | renderer měl specifické sticky notes/shapes/grid templates | board měl stejných 23 sticky notes jako baseline | FAIL | remote role counts, visible content a minimálně 250 items |
| Exact-SHA izolovaná acceptance | candidate SHA byl uveden v technickém reportu | board sám neprokazoval, který candidate jej vytvořil | FAIL | viditelné `source_commit`, scaffold hash a render-contract markers |
| Schema/runtime/test/docs rozšíření | soubory byly změněny a source-level testy prošly | testy nedokazovaly skutečný vzdálený obsah | PARTIAL | schema `2.4`, negativní remote regrese a PowerShell API recheck |

## Root cause

Kořenová příčina nebyla v jediné Miro operaci, ale v návrhu důkazu:

1. renderer vytvořil lokální mapping s očekávanými rolemi;
2. remote validator dohledal Miro ID převážně přes tento mapping;
3. acceptance znovu kontrolovala tentýž mapping a jeho stavová pole;
4. žádná vrstva nezávisle neověřila povinný viditelný obsah celého boardu;
5. report proto mohl uvést `remote_layout_status: PASS`, přestože board vypadal jako baseline.

Sekundární slabiny:

- chyběla vazba boardu na exact candidate package;
- chyběl hash skutečně renderovaného scaffoldingu;
- chyběl digest vzdáleného obsahu;
- chyběl baseline-regression threshold;
- testy neobsahovaly scénář „mapping je správný, remote obsah je starý“.

## Korekční kontrakt REM-PR8-HVA-CC-002

Korekce zavádí následující fail-closed podmínky:

1. scaffold schema je `2.4`;
2. render contract je `REM-PR8-HVA-CC-002`;
3. candidate package musí obsahovat přesný čtyřicetiznakový `source_commit`;
4. board zobrazuje:
   - `DDDA-RENDER-CONTRACT:<version>`;
   - `DDDA-PLATFORM-SOURCE:<source_commit>`;
   - `DDDA-SCAFFOLD-SHA256:<sha256>`;
5. renderer po zápisu znovu načte Miro items a connectors;
6. remote board musí mít nejméně 250 items; očekávaný deterministický render má 259 items a 53 connectors;
7. každá z pěti guide sekcí musí být viditelná přesně patnáctkrát;
8. editovatelná pracovní plocha musí být viditelná přesně patnáctkrát;
9. Control Center musí viditelně obsahovat tři nezávislé stavové dimenze a devět registry sloupců;
10. z reálně načtených systémových položek se vypočte `remote_content_digest`;
11. PowerShell acceptance znovu čte board přímo z Miro API a porovnává jej s candidate package;
12. negativní testy poškozují remote obsah při zachování mappingu a očekávají hard failure.

## Bezpečný rollback a nové provedení

Historie se nepřepisuje a nepoužije se force-push.

1. explicitní revert původního lokálního REM: `344ed58`;
2. nová korekční implementace jako samostatný commit;
3. publikace pouze fast-forward nad aktuální PR HEAD;
4. nový candidate package a CI nad novým exact SHA;
5. nový izolovaný Miro board;
6. technická acceptance s novými provenance a remote-content kontrolami;
7. až potom jednorázové human visual review;
8. žádný merge, promotion, tag ani release bez úspěšného review.

## Acceptance stav

| Vrstva | Stav |
|---|---|
| Forenzní porovnání starého boardu | FAIL potvrzen |
| Starý technický PASS | zneplatněn jako vizuální evidence |
| Historický board | zachován, read-only |
| Korekční source implementace | v realizaci |
| Offline regressions | pending full suite |
| CI exact-SHA | pending |
| Nový online Miro acceptance board | pending |
| Human visual acceptance | pending |
| Merge / promotion | zakázáno do uzavření review |
