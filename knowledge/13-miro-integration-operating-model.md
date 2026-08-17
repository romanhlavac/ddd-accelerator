# Miro integration operating model

## Purpose

Tento playbook definuje, jak DDDA používá Miro při vývoji platformy a v projektovém runtime bez závislosti na jedné identitě nebo jednom transportu.

## Základní hranice

```text
REST API = deterministic automation/data plane
MCP      = optional interactive AI control plane
Human    = judgment/review plane
Git      = source of truth
```

MCP není technický validační gate. Vyčerpaná MCP quota nesmí blokovat build, online acceptance, reconcile, read-back, idempotence, HVR materializaci ani release validation. Pokud je MCP nedostupné, automatizovatelný FAST-LOOP pokračuje přes schválené REST execution profiles v GitHub Actions.

## Execution profiles

Kanonická platformní konfigurace je `config/platform/miro-execution-profiles.yaml`.

Profily jsou logické role, nikoli implicitní předpoklad jedné Miro identity:

- `platform_lab` — persistentní vývojový a online-validation target;
- `example_project` — persistentní zalidněný example projekt;
- `github_ci` — secret-bearing REST executor GitHub Actions;
- `hvr` — samostatná materializace a technický preflight pro Human Visual Review;
- `mcp` — interaktivní ChatGPT/Cursor connector;
- `project_runtime` — Miro integrace konkrétního DDDA projektu.

Identity reference je ne-secret popisek. Token je vždy jen nepřímo odkazován názvem environment variable nebo GitHub secretu.

## Platform development

GitHub Actions provádí mechanické Miro operace přes REST API. Chat/Work pracuje s Git/CI evidence a používá MCP pouze tehdy, když je užitečné pro interaktivní čtení nebo review.

Persistentní Platform Lab odděluje:

```text
CONTROL              permanent/protected
CI SANDBOX           managed, recyklovatelný
FAIL DIAGNOSTICS     dočasně zachovaný poslední relevantní FAIL
```

Human-review target je samostatný logický slot `DDDA_HVR`, materializovaný až po PASS online Platform Lab evidence server-side kopií stejného exact-SHA kandidáta. HVR board není CI sandbox ani ručně opravovaný review board.

Cleanup je explicit-ID/ownership based. Neznámý objekt se nemaže. Online writer je serializovaný.

## Reference/adapted-board artifact reproduction — závazný Git-backed kontrakt

Tento postup je výchozí a závazný pro situace, kdy DDDA musí **přesně reprodukovat Miro frame nebo jiný Miro artefakt** z referenčního nebo předem adaptovaného boardu do cílového boardu. Vznikl z ověřeného PR #8 HVR FAST-LOOP, kde samotný strukturální clone a REST `shape=curved` nebyly dostatečné pro vizuální ekvivalenci.

Základní pravidlo:

```text
reference/adapted Miro board = discovery + human oracle
Git                         = frozen reproducible specification
GitHub Actions + REST       = deterministic generator/reconciler
Platform Lab                = technical acceptance target
DDDA_HVR                    = exact-SHA human-review materialization
Human                       = final visual acceptance authority
```

Po zmrazení reference se cílový artefakt **nesmí generovat podle odhadu, screenshotového dojmu ani aktuálního živého stavu source boardu bez identity/freeze guardu**. Všechny vlastnosti, které musí být reprodukovatelné, musí být reprezentované ve verzovaném Git kontraktu nebo ve verzovaném assetu s integritním hashem.

### 1. Zmrazení provenance a identity reference

Před implementací se načte skutečný source board/frame a vytvoří se frozen reference contract. Ten musí podle typu artefaktu obsahovat alespoň:

- `source_board_id`, `source_frame_id` a relevantní source item IDs;
- stabilní logické klíče položek nezávislé na target item IDs;
- source frame title a frame geometry;
- očekávané počty items a type counts;
- povinné textové/content markery;
- pro connectors identity, start/end item, attachment position, direction, shape, stroke style/caps a další dostupné REST vlastnosti;
- freeze commit/SHA a timestamp;
- hash verzovaných image/raster assets;
- podle potřeby `modifiedAt` boundary nebo jiný source-mutation guard.

Živý Miro CDN rendition hash sám o sobě není dostatečný oracle, protože Miro může beze změny itemu obraz znovu enkódovat. Pinned item identity + freeze boundary + native topology/properties jsou autoritativnější než momentální CDN byte hash; hash assetu uloženého v Gitu je naopak povinný a deterministický.

Pokud je referencí **adaptovaný board/frame**, musí být adaptace sama explicitně označena jako schválený source contract. Musí být dohledatelná provenance původní reference → adaptace → frozen Git contract. Adaptovaný source nesmí být tichá ruční mezivrstva bez versioned specifikace.

### 2. Native round-trippable vlastnosti držet jako specifikaci v Gitu

Vlastnosti, které REST API umí deterministicky vytvořit a přečíst zpět, se mají držet deklarativně nebo jako jednoznačný code/data contract v Gitu. Typicky:

- item type a logical key;
- content/text;
- style a font properties;
- parent/frame ownership;
- x/y/width/height a coordinate system;
- connector start/end item;
- attachment position a snap/direction semantics;
- connector shape, stroke, caps a caption properties;
- očekávané counts, required markers a tolerance.

Target Miro item ID je runtime mapping, nikoli produktová specifikace. Reconciler musí umět artefakt z Git kontraktu znovu vytvořit do jiného povoleného boardu a následně prokázat read-back.

### 3. Non-round-trippable renderer state nikdy neaproximovat generickým fallbackem

Pokud Miro REST API nevystavuje vlastnost, která je pro schválenou vizuální podobu významná, nesmí automatizace předstírat ekvivalenci pouze proto, že dostupná metadata vypadají podobně.

Ověřený příklad PR #8: REST v2 vystaví connector endpoint metadata a hrubé `shape=curved`, ale nevystaví ručně autorský curve/path routing state. Native connector tedy může strukturálně round-tripnout a přesto vykreslit jinou křivku.

Povinný postup pro takový případ:

1. nejprve prokaž, že renderer state není přes podporované API reprodukovatelný;
2. odděl **semantic/native layer** od **visual carrier layer**;
3. vizuálně významnou nereprodukovatelnou část ulož jako těsně oříznutý transparentní asset v Gitu;
4. u assetu drž SHA-256, logical key a přesnou x/y/width/height specifikaci;
5. při renderu ověř hash assetu ještě před uploadem;
6. po uploadu ověř title/logical identity, parent, position a geometry;
7. zachovej native interaktivní prvky tam, kde jsou potřebné a deterministicky reprodukovatelné.

V Miro Tips v5 je tímto způsobem osm ručně routovaných curved calloutů reprezentováno osmi transparentními golden-arrow PNG overlays, zatímco tři jednoduché textové callouty zůstávají native straight connectors se šesti deterministickými per-endpoint controls.

Zakázané fallbacky:

- jeden sdílený routing proxy pro více odlišných endpointů;
- generický „nejbližší“ anchor bez explicitního contractu;
- tvrzení, že `shape=curved` znamená shodnou path geometry;
- manual patch cílového boardu po generátoru bez následné změny Git kontraktu.

### 4. Deterministický generator/reconciler

Reprodukce do target boardu běží REST-first z exact-SHA candidate package. Reconciler musí:

1. ověřit execution profile, credential binding, source/target identity a frozen reference preconditions;
2. načíst Git-backed artifact contract a verzované assets;
3. pracovat pouze v explicitně managed namespace/parentu;
4. mapovat logical keys na target runtime IDs;
5. vytvořit nebo aktualizovat jen očekávané managed items;
6. mazat pouze explicitně owned neočekávané items, nikdy cizí obsah;
7. pro podporované native vazby mířit na skutečný target item, nikoli na generický proxy;
8. normalizovat známé API read-back reprezentace, například HTML entities v image title;
9. po každé write operaci provést read-back invariantů;
10. po celém reconcile provést fresh read-back a poté druhý reconcile s **zero mutation** výsledkem.

Generátor nesmí záviset na Miro MCP ani na ručním přenášení objektů. MCP zůstává pouze volitelným interactive/review kanálem.

### 5. Povinné mechanické gaty

Technical PASS pro reference-derived artefakt musí být fail-closed a kontrolovat podle relevance minimálně:

- frozen source identity/provenance;
- Git asset SHA-256;
- expected item count a type counts;
- logical item identity 1:1;
- content/style/font/parent/geometry;
- connector identity a endpoint mapping;
- explicit-vs-auto attachment semantics;
- endpoint geometry s malou explicitní tolerancí;
- nepřítomnost zakázaného generic proxy/fallbacku;
- přesný počet visual carriers a jejich hash/geometry;
- fresh target read-back;
- second reconcile = zero create/update/delete;
- exact candidate SHA a artifact/scaffold hash v evidence.

Stavy musí zůstat oddělené:

```text
STRUCTURAL_REFERENCE_MATCH = PASS | FAIL
ENDPOINT_GEOMETRY_MATCH    = PASS | FAIL | NOT_APPLICABLE
VISUAL_CARRIER_MATCH       = PASS | FAIL | NOT_APPLICABLE
HUMAN_VISUAL_ACCEPTANCE    = PENDING | PASS | FAIL
```

Automatizace nesmí z prvních tří stavů odvodit `HUMAN_VISUAL_ACCEPTANCE=PASS`.

### 6. Platform Lab → HVR materialization

Po technickém PASS se nepředává člověku přímo mutable Platform Lab. Povinný tok je:

```text
exact candidate SHA
→ Platform Lab reconcile
→ fresh read-back
→ zero-mutation second reconcile
→ server-side DDDA_HVR materialization
→ copied-board read-back
→ stable HVR URL
→ human visual review
```

HVR board je materializace validovaného stavu, ne místo pro ruční opravy. Pokud je po HVR potřeba změna, opravuje se Git contract/generator, znovu se provede exact-SHA CI a vytvoří se nový HVR candidate.

### 7. Co invaliduje předchozí evidence

Nové exact-SHA technical evidence je povinné při změně zejména:

- source/reference identity;
- frozen properties nebo freeze boundary;
- Git assetu nebo jeho SHA-256;
- artifact/scaffold specification;
- geometry tolerance;
- generator/reconciler semantics;
- target materialization contractu.

Předchozí HVR evidence se po změně source SHA podle aktivní governance nepovažuje za finální acceptance evidence. Pouhá změna runtime target IDs sama o sobě není změnou produktového kontraktu, pokud logical identity a všechny invarianty zůstanou stejné a fresh read-back to prokáže.

### 8. Referenční implementace v PR #8

Ověřený vzor je rozdělen mezi tyto versioned artefakty:

```text
scaffolds/miro/rem-012-5-frame-01.yaml
runtime/miro/ddda_miro/miro_tips_reference_oracle.py
runtime/miro/ddda_miro/miro_tips_render_fidelity_fix.py
runtime/miro/ddda_miro/miro_tips_full_arrow_fidelity_fix.py
runtime/miro/ddda_miro/miro_tips_visual_overlay_v5.py
runtime/miro/ddda_miro/assets/
runtime/miro/ddda_miro/hvr_materialization.py
```

`scaffolds/miro/rem-012-5-frame-01.yaml` drží frozen source IDs, freeze metadata, frame geometry, expected counts, connector identities, endpoint tolerance, required markers a target placement. `miro_tips_reference_oracle.py` fail-closed ověřuje živou frozen reference. `miro_tips_visual_overlay_v5.py` drží hashed visual-carrier specs a jejich deterministic upload/read-back. `hvr_materialization.py` odděluje technicky validovaný Platform Lab od lidského review slotu.

Tento konkrétní kód není univerzální API pro všechny budoucí artefakty; **univerzální je jeho kontrakt a orchestrace**. Nový reference-derived artefakt může mít jiný renderer, ale musí zachovat stejné principy provenance → Git-backed specification → deterministic reconcile → read-back → idempotence → HVR.

### Anti-patterny

Za metodický defect se považuje zejména:

- screenshot jako jediný source of truth bez Git-backed properties;
- živý source board jako neomezená runtime dependency bez freeze guardu;
- kopírování „podle oka“;
- strukturální item-count PASS vydávaný za visual equivalence;
- ztráta endpoint/attachment semantics při remappingu;
- generický proxy/fallback místo per-item/per-endpoint contractu;
- nereprodukovatelný manual fix přímo v target boardu;
- HVR vytvořený před technical read-back/idempotence;
- hardcoded historické HVR board ID místo URL z exact-SHA evidence.

## Human Visual Review

Technický předpoklad HVR je exact-SHA REST evidence:

```text
candidate SHA
→ Platform Lab REST reconcile
→ fresh read-back
→ zero-mutation second reconcile
→ server-side DDDA_HVR materialization
→ copied-board read-back
→ stable HVR URL
→ human review
```

FAST-LOOP pokračuje automaticky přes všechny mechanické kroky. Reviewer se vyžádá až ve chvíli, kdy je fresh HVR candidate pro stejný exact SHA skutečně `READY_FOR_HUMAN_REVIEW`.

HVR lze provést otevřením stabilní URL a vrácením verdictu/screenshotu. MCP může review usnadnit, ale jeho nedostupnost HVR technicky neblokuje.

## Example project

`DDDA Example Project` je samostatný project-owned board. Není scratch board ani CI sandbox. Má dokazovat, že candidate/release package umí vytvořit a udržovat skutečný projektový Miro workspace.

## Project runtime in Cursor

Každý projekt má vlastní `project.yaml`. Miro binding je explicitní přes:

```yaml
miro:
  board_id: null
  board_id_env: <PROJECT>_MIRO_BOARD_ID
  access_token_env: <PROJECT_SPECIFIC_TOKEN_ENV>
  team_id: null
  team_id_env: <PROJECT_SPECIFIC_TEAM_ENV>
  project_id: null
  project_id_env: <PROJECT_SPECIFIC_SPACE_ENV>
```

`project_id` odpovídá Miro Space/legacy Project ID používanému REST API.

Pokud board neexistuje, runtime může s explicitním create-board intentem vytvořit `DDDA – <ProjectName>` přes REST API v nakonfigurovaném teamu/Space. Board ID se následně uloží do Miro mappingu. Runtime nesmí přebírat credential jiného projektu bez explicitní konfigurace.

## Credential rules

- raw token nikdy nepatří do Git, reportu, Chatu ani Work contextu;
- GitHub CI čte token pouze z GitHub secret store;
- Cursor/project runtime čte token z projektově zvoleného environment variable nebo schváleného secure local store;
- MCP používá OAuth session připojeného connectoru a token se do DDDA konfigurace nekopíruje;
- různé profily mohou používat různé identity a credentials; implicitní cross-profile credential fallback je zakázán;
- `platform_lab`, `github_ci` a `hvr` používají pouze credential chain deklarovaný svým execution profilem;
- legacy `MIRO_ACCESS_TOKEN` fallback se pro aktivní PR #8 platform-development profiles nepoužívá;
- migrace private → corporate Miro se provádí změnou explicitních bindingů/profilů, ne forkem Miro runtime.

## Current PR #8 contract

Pro PR #8 je autoritativní profile-isolated tok:

```text
platform_lab
→ github_ci REST validation
→ hvr server-side materialization
→ human visual verdict
```

Legacy token nebo credential jiného profilu nesmí být použit jako tichý fallback. Chybějící profile-specific credential je fail-closed technický blocker daného kroku, nikoli důvod přeskočit Human Review nebo přesměrovat writer na jinou identitu.

Předchozí HVR evidence se po změně source SHA, execution contractu nebo HVR targetu nepovažuje za finální acceptance evidence a musí být nahrazena evidence pro nový exact SHA.
