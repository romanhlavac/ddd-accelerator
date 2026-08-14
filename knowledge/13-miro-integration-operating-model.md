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
