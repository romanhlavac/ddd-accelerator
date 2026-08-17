# Miro execution profiles and credential governance

## Scope

Tento dokument je provozní kontrakt pro Miro při vývoji DDDA platformy a pro pozdější napojení jednotlivých DDDA projektů. Architektonické rozhodnutí je v ADR 0007; machine-readable bindingy jsou v `config/platform/miro-execution-profiles.yaml`.

## Princip

```text
Git/YAML             authoritative state
GitHub Actions REST  deterministic platform execution
Miro MCP             optional interactive AI access
Human review         architecture/method/usability judgment
```

MCP quota nebo nedostupnost connectoru nesmí být příčinou technical FAIL, pokud není předmětem testu samotný MCP integration contract.

## Aktivní development model

Pro aktuální vývoj PR #8 jsou aktivní přesně tři oddělené REST profily v jednom privátním Miro Developer Teamu:

| Profile | Board | Credential binding | Role |
|---|---|---|---|
| `platform_lab` | `DDDA_PLATFORM_LAB` | `MIRO_PLATFORM_LAB_ACCESS_TOKEN` | fast-loop, remediation a deterministic platform target |
| `github_ci` | `DDDA_GH_CI` | `MIRO_GH_CI_ACCESS_TOKEN` | GitHub Actions online acceptance |
| `hvr` | `DDDA_HVR` | `MIRO_HVR_ACCESS_TOKEN` | samostatný Human Visual Review target |

Žádný z těchto profilů nesmí fallbacknout na token jiného profilu ani na legacy `MIRO_ACCESS_TOKEN`.

`example_project` a `project_runtime` zůstávají v kontraktu, ale jsou **deferred**. Jejich credentialy, team/Space bindingy a boardy se aktivují až při nasazení/inicializaci DDDA platformy a konkrétních projektů.

## Platform Lab

`DDDA_PLATFORM_LAB` je persistentní vývojový board. PR #8 používá bootstrap board ID `uXjVH0doLYY=`; environment/repository variable `DDDA_MIRO_PLATFORM_LAB_BOARD_ID` jej může explicitně přebindovat bez změny runtime kódu.

Platform Lab je jediný target pro PR8 frame-remediation FAST-LOOP. Zápis probíhá REST API s `MIRO_PLATFORM_LAB_ACCESS_TOKEN`; MCP není transportem technické remediation.

Managed cleanup musí být omezen na známé DDDA artefakty. Neznámý obsah je fail-closed boundary.

## GitHub CI board

`DDDA_GH_CI` je dedikovaný machine-only board. Bootstrap board ID pro aktuální private Dev Team je `uXjVHy7iQD4=`; může jej přebindovat `DDDA_MIRO_GH_CI_BOARD_ID`.

GitHub Actions používá výhradně `MIRO_GH_CI_ACCESS_TOKEN`. Před online acceptance:

```text
verify token context + scopes + team
→ verify exact board binding
→ clear all items from dedicated DDDA_GH_CI board
→ render/sync candidate into the same board
→ remote read-back
→ idempotence
→ evidence artifact
```

Protože board je označen jako machine-only, jeho pre-run reset smí odstranit všechny board items. Samotný board se během běžného CI nemaže a nevytváří znovu.

## HVR board

`DDDA_HVR` je dedikovaný logical review slot oddělený od Platform Labu. GitHub Actions nejdříve technicky zvaliduje/remediateuje Platform Lab s platformním tokenem. Poté použije **výhradně** `MIRO_HVR_ACCESS_TOKEN` k materializaci HVR targetu server-side kopií validovaného Platform Lab boardu.

Aktuální PR8 mechanismus je:

```text
exact candidate SHA
→ Platform Lab REST reconcile
→ fresh read-back
→ second reconcile = zero mutation
→ delete previous DDDA_HVR logical slot
→ Miro server-side Copy Board from DDDA_PLATFORM_LAB
→ new DDDA_HVR
→ copy/read-back evidence
→ human HVR
```

Fyzické HVR board ID se proto může po novém HVR materialization runu změnit. Autoritativní HVR URL je vždy URL zachycená v exact-SHA evidence pro daný run, nikoli historický hardcoded board ID.

Human reviewer může použít Miro GUI, screenshot nebo MCP. MCP není precondition `READY_FOR_HUMAN_REVIEW`.

## Token and board binding preflight

Před secret-bearing online acceptance musí CI ověřit pro každý aktivní profil:

- token je přítomný;
- `GET /v1/oauth-token` vrátí očekávaný team;
- scope obsahuje `boards:read` i `boards:write`;
- token dokáže načíst svůj explicitní board/resource;
- Platform Lab a GH CI board mají očekávané názvy;
- HVR logical slot je jednoznačně dohledatelný přes exact board name;
- raw token se nikdy nezapisuje do artifactu nebo logu.

## GitHub secrets and variables

Povinné development secrets:

```text
MIRO_PLATFORM_LAB_ACCESS_TOKEN
MIRO_GH_CI_ACCESS_TOKEN
MIRO_HVR_ACCESS_TOKEN
```

Volitelné explicitní binding variables:

```text
DDDA_MIRO_PLATFORM_LAB_IDENTITY
DDDA_MIRO_PLATFORM_LAB_TEAM_ID
DDDA_MIRO_PLATFORM_LAB_BOARD_ID

DDDA_MIRO_GH_CI_IDENTITY
DDDA_MIRO_GH_CI_TEAM_ID
DDDA_MIRO_GH_CI_BOARD_ID

DDDA_MIRO_HVR_IDENTITY
DDDA_MIRO_HVR_TEAM_ID
DDDA_MIRO_HVR_BOARD_ID
```

`*_IDENTITY` je non-secret audit label. Token patří výhradně do GitHub secret store. Board/team ID nejsou secrets.

## MCP

MCP zůstává samostatný interactive control plane připojený OAuth identitou mimo GitHub Actions. MCP se používá pouze tam, kde má přidanou hodnotu pro interaktivní AI práci nebo vizuální inspection. Bulk create/update/read-back, CI a HVR materialization běží přes REST, aby MCP quota nebyla blockerem platformního vývoje.

## Deferred: Example project

Example project se v aktuálním PR8 development prostředí nezakládá a nemá aktivní token ani board. Aktivace patří do platform deployment/release-initialization fáze. Teprve tam dostane vlastní identitu/token/team/Space/board binding.

## Deferred: DDDA Project X in Cursor

Per-project runtime je nyní pouze kontrakt. Při inicializaci konkrétního DDDA projektu bude možné nezávisle nastavit:

```yaml
miro:
  board_id: null
  board_id_env: PROJECT_X_MIRO_BOARD_ID
  access_token_env: PROJECT_X_MIRO_ACCESS_TOKEN
  team_id: null
  team_id_env: PROJECT_X_MIRO_TEAM_ID
  project_id: null
  project_id_env: PROJECT_X_MIRO_SPACE_ID
```

Po aktivaci runtime:

```text
project.yaml
→ resolve project-specific token/team/Space
→ REST create `DDDA – <ProjectName>` when board is missing
→ persist board mapping
→ render scaffold
→ read-back
→ idempotence
```

Tento runtime se nesmí aktivovat ani provisionovat v rámci současného PR8 platform-development wiring.

## Corporate migration

Současné private Developer Team prostředí je dočasný execution environment. Jakmile corporate team dovolí app instalaci/API nebo MCP, migration se provede změnou profilových bindingů, ne forkem runtime:

```text
private token/team/board
→ corporate token/team/Space/board
```

## Security rules

- žádný raw token v Git diffu, Markdownu, evidence, PR komentáři ani Chat/Work contextu;
- žádný MCP OAuth token v GitHub secrets;
- token scope least privilege;
- aktivní development profily mají tři explicitní credentials bez cross-profile fallbacku;
- CI/HVR musí ověřit token context, team a target před write operací;
- dedicated `DDDA_GH_CI` je jediný board, který lze v pre-run resetu kompletně vyčistit;
- HVR materialization nesmí změnit Platform Lab;
- merge, promotion, release ani gate approval nejsou autorizovány žádným Miro profilem.
