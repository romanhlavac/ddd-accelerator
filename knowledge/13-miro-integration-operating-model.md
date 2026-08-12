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

MCP není technický validační gate. Vyčerpaná MCP quota nesmí blokovat build, online acceptance, reconcile, read-back, idempotence ani release validation.

## Execution profiles

Kanonická platformní konfigurace je `config/platform/miro-execution-profiles.yaml`.

Profily jsou logické role, nikoli implicitní předpoklad jedné Miro identity:

- `platform_lab` — persistentní vývojový/HVR target;
- `example_project` — persistentní zalidněný example projekt;
- `github_ci` — secret-bearing REST executor GitHub Actions;
- `hvr` — materializace a technický preflight pro Human Visual Review;
- `mcp` — interaktivní ChatGPT/Cursor connector;
- `project_runtime` — Miro integrace konkrétního DDDA projektu.

Identity reference je ne-secret popisek. Token je vždy jen nepřímo odkazován názvem environment variable nebo GitHub secretu.

## Platform development

GitHub Actions provádí mechanické Miro operace přes REST API. Chat/Work pracuje s Git/CI evidence a používá MCP pouze tehdy, když je užitečné pro interaktivní čtení nebo review.

Persistentní Platform Lab má oddělovat:

```text
CONTROL              permanent/protected
CI SANDBOX           managed, recyklovatelný
FAIL DIAGNOSTICS     dočasně zachovaný poslední relevantní FAIL
HVR CURRENT          zachovaný do lidského verdictu
```

Cleanup je explicit-ID/ownership based. Neznámý objekt se nemaže. Online writer je serializovaný.

## Human Visual Review

Technický předpoklad HVR je exact-SHA REST evidence:

```text
candidate SHA
→ REST reconcile
→ fresh read-back
→ zero-mutation second reconcile
→ stable Miro URL
→ human review
```

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
- různé profily mohou dočasně odkazovat na stejnou identitu/token, ale nesmí to být hardcoded platformní předpoklad;
- migrace private → corporate Miro se provádí změnou bindingů, ne forkem Miro runtime.

## Current PR #8 migration

Během PR #8 zůstává podporován legacy `MIRO_ACCESS_TOKEN` a současný review target jako fallback. Nový profilový kontrakt má přednost, jakmile jsou specifické secrets/variables nakonfigurovány. Předchozí HVR-2 evidence se po změně execution contractu nepovažuje za finální acceptance evidence a musí být nahrazena exact-SHA během podle nového profilu.
