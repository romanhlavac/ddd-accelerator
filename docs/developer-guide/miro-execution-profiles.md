# Miro execution profiles and credential governance

## Scope

Tento dokument je provozní kontrakt pro Miro při vývoji DDDA platformy a pro napojení jednotlivých DDDA projektů. Architektonické rozhodnutí je v ADR 0007; machine-readable bindingy jsou v `config/platform/miro-execution-profiles.yaml`.

## Princip

```text
Git/YAML             authoritative state
GitHub Actions REST  deterministic platform execution
Cursor REST          deterministic project execution
Miro MCP             optional interactive AI access
Human review         architecture/method/usability judgment
```

MCP quota nebo nedostupnost connectoru nesmí být příčinou technical FAIL, pokud není předmětem testu samotný MCP integration contract.

## Profilový model

| Profile | Resource/actor | Transport | Credential binding | Technical gate |
|---|---|---|---|---|
| `platform_lab` | persistent platform board | REST | `MIRO_PLATFORM_LAB_ACCESS_TOKEN` + board/team vars | ano jako target, ne jako jediný principal |
| `example_project` | persistent example board | REST | `MIRO_EXAMPLE_PROJECT_ACCESS_TOKEN` + board/team/space vars | release/example acceptance |
| `github_ci` | GitHub Actions principal | REST | `MIRO_CI_ACCESS_TOKEN` | ano |
| `hvr` | HVR materialization principal | REST | `MIRO_HVR_ACCESS_TOKEN` | technický preflight ano, lidský verdict ne |
| `mcp` | ChatGPT/Cursor interactive session | MCP/OAuth | external connector | **ne** |
| `project_runtime` | konkrétní DDDA project | REST | `project.yaml -> access_token_env` | project-specific |

Během PR #8 může `MIRO_ACCESS_TOKEN` fungovat jako explicitně dokumentovaný fallback. Nesmí se z něj znovu stát architektonický single-token contract.

## Platform Lab

`DDDA Platform Lab` je persistentní board. Pro PR #8 je stávající review board povolen jako bootstrap binding, dokud není vytvořen finální Lab board.

Doporučené managed zóny:

- `CONTROL` — permanentní a protected;
- `CI SANDBOX` — automaticky recyklovatelný;
- `FAIL DIAGNOSTICS` — dočasně zachovaný poslední relevantní fail;
- `HVR CURRENT` — stabilní lidský review target.

Každý run musí znát exact SHA a explicitní seznam owned/managed IDs. Cleanup smí mazat pouze tato ID. Neznámé objekty jsou fail-closed boundary.

Online write na persistentní Lab se serializuje. Offline testy mohou běžet paralelně.

## HVR bez MCP dependency

Povinný technický tok:

```text
exact candidate SHA
→ REST write/reconcile
→ fresh remote read-back
→ invariant checks
→ second reconcile = zero mutation
→ evidence artifact
→ stable review URL
```

Pak proběhne lidské HVR. Reviewer může:

- otevřít Miro URL v GUI;
- poslat screenshot/findings do Chatu;
- použít MCP, pokud je dostupné a quota dovoluje.

MCP není precondition HVR-ready. Pokud connector není dostupný, musí evidence jasně uvést, že interaktivní MCP inspection nebyla provedena; technická REST evidence tím není zneplatněna.

## GitHub CI secrets and variables

Preferred bindings:

```text
MIRO_CI_ACCESS_TOKEN
DDDA_MIRO_CI_IDENTITY
DDDA_MIRO_CI_TEAM_ID

MIRO_PLATFORM_LAB_ACCESS_TOKEN
DDDA_MIRO_PLATFORM_LAB_IDENTITY
DDDA_MIRO_PLATFORM_LAB_TEAM_ID
DDDA_MIRO_PLATFORM_LAB_BOARD_ID

MIRO_HVR_ACCESS_TOKEN
DDDA_MIRO_HVR_IDENTITY
```

`*_IDENTITY` je pouze ne-secret audit label. Token patří do GitHub secret store. Board/team ID může být Repository/Environment variable.

PR #8 migration fallback:

```text
MIRO_HVR_ACCESS_TOKEN
→ MIRO_PLATFORM_LAB_ACCESS_TOKEN
→ MIRO_ACCESS_TOKEN
```

Generic CI může do dokončení migrace používat `MIRO_ACCESS_TOKEN`; jeho přejmenování na `MIRO_CI_ACCESS_TOKEN` je samostatný follow-up, protože GitHub secret store nelze bezpečně migrovat z platformního source commitu.

## Example project

Example board má vlastní bindingy a nesmí sdílet board lifecycle s CI sandboxem. Runtime release validation jej smí materializovat/reconciliovat pouze z exact candidate/release package.

Recommended variables/secrets:

```text
MIRO_EXAMPLE_PROJECT_ACCESS_TOKEN
DDDA_MIRO_EXAMPLE_PROJECT_IDENTITY
DDDA_MIRO_EXAMPLE_PROJECT_TEAM_ID
DDDA_MIRO_EXAMPLE_PROJECT_SPACE_ID
DDDA_MIRO_EXAMPLE_PROJECT_BOARD_ID
```

## DDDA Project X in Cursor

Projektová konfigurace už podporuje nezávislé env references:

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

Token hodnota není v YAML. Cursor/runtime ji získá z prostředí/secure store.

Board bootstrap:

```text
project.yaml
→ resolve token/team/Space
→ REST create board `DDDA – <ProjectName>` when missing
→ persist board mapping
→ render scaffold
→ read-back
→ idempotence
```

Miro Python runtime již umí `teamId` i `projectId` při create-board. `projectId` je Miro API identifikátor Space. User-facing generator má být v follow-up CHR rozšířen tak, aby project-specific env names generoval automaticky místo současných globálních defaultů.

## Corporate migration

Současné private Developer Team prostředí je dočasný execution environment. Jakmile corporate team dovolí app instalaci/API nebo MCP, migration se provede změnou profilových bindingů:

```text
private board/team/token
→ corporate board/team/Space/token
```

Runtime code, Git/YAML authority a test semantics se nemění. Corporate Developer Team není nutný, pokud lze existující DDDA app nainstalovat/autorizovat v corporate teamu.

## Security rules

- žádný raw token v Git diffu, Markdownu, evidence ani PR komentáři;
- žádný MCP OAuth token v GitHub secrets;
- žádný GitHub secret v Chat/Work contextu;
- token scope least privilege;
- board/team/profile identity musí být evidence metadata, ne implicitní hardcode;
- CI/HVR nesmí fallbacknout na jiný board, pokud explicitní board variable ukazuje na nekompatibilní target; skončí fail-closed;
- merge, promotion, release ani gate approval nejsou autorizovány Miro profilem.
