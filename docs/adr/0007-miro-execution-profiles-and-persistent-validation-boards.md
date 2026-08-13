# ADR 0007 — Miro execution profiles, REST-first automation and persistent validation boards

Status: Accepted

Date: 2026-08-12

## Context

DDDA používá Miro ve dvou odlišných režimech: deterministická platformní automatizace a interaktivní práce člověka/AI. Dosavadní implementace používala jeden implicitní `MIRO_ACCESS_TOKEN`, jeden hardcoded Miro team a část review toku byla provozně závislá na Miro MCP. Současně Miro MCP pod privátní identitou podléhá nízkému dennímu organizačnímu limitu a firemní identita zatím nemá oprávnění k instalaci app ani MCP.

DDDA proto potřebuje oddělit resource identity, execution principals a transport. Změna musí být non-breaking pro PR #8, nesmí přesunout secrets do Chatu/Work ani do Gitu a nesmí oslabit exact-SHA validation nebo human gate boundaries.

## Decision

1. **Miro REST API je deterministický automation/data plane.** GitHub CI, rendering, reconcile, read-back, idempotence, cleanup a automatické založení projektového boardu používají REST API.
2. **Miro MCP je volitelný interactive AI control plane.** MCP slouží pro exploratory čtení, interaktivní práci a pomoc při review, ale nikdy není předpokladem technical PASS, merge readiness ani release validation.
3. Zavádí se explicitní konfigurace `config/platform/miro-execution-profiles.yaml` pro logické profily `platform_lab`, `example_project`, `github_ci`, `hvr`, `mcp` a `project_runtime`.
4. **Tokeny se nikdy neukládají do Gitu.** Konfigurace obsahuje jen názvy GitHub secrets nebo environment variables a ne-secret `identity_ref` metadata.
5. `DDDA Platform Lab` je persistentní platformní board. PR #8 může během migrace použít dosavadní target board jako jeho bootstrap binding. CI/HVR smí měnit pouze explicitně managed obsah a všechny mechanické změny musí mít read-back a zero-mutation second reconcile.
6. `DDDA Example Project` je samostatný persistentní project-owned board určený pro release/example validation, nikoli CI scratch space.
7. Každý runtime DDDA projekt má vlastní Miro konfiguraci v `project.yaml`: board, team, Space (`project_id` v Miro API), token env a případně identity reference. Projektový runtime může při chybějícím boardu vytvořit board přes REST API přímo v nakonfigurovaném teamu/Space.
8. GitHub CI a HVR mohou používat různé Miro identity/tokeny nad stejným Platform Labem. MCP OAuth identita je na nich nezávislá.
9. GitHub Actions zůstává autoritativní execution plane pro platformní technické evidence. Human visual review zůstává samostatným lidským rozhodnutím.
10. Během PR #8 je povolen explicitně dokumentovaný legacy fallback `MIRO_ACCESS_TOKEN` a současný target board, aby migrace nebyla breaking. Nové specifické secrets mají přednost, jakmile jsou nakonfigurovány.

## Options considered

### A — MCP jako hlavní Miro transport

Pros:
- jednotné interaktivní rozhraní;
- jednoduché ad hoc použití z Chatu.

Cons:
- denní organizační quota blokuje vývoj;
- MCP tool calls jsou nevhodné pro bulk deterministic reconcile;
- technický gate by závisel na interaktivním connectoru.

Decision: rejected.

### B — Jedna identita a jeden token pro CI, HVR, ChatGPT a runtime

Pros:
- nejjednodušší konfigurace.

Cons:
- vysoké blast radius;
- nemožnost oddělit privátní/corporate prostředí;
- obtížná rotace a migrace;
- neodpovídá least privilege.

Decision: rejected.

### C — Explicitní execution profiles, REST-first a MCP-light

Pros:
- oddělené identity a credentials;
- MCP quota není technický blocker;
- přenositelnost mezi privátním a corporate Miro prostředím;
- project runtime může mít vlastní team/Space/token;
- lepší auditovatelnost a least privilege.

Cons:
- více konfiguračních bindingů;
- vyžaduje jasný credential naming contract a migration fallback.

Decision: accepted.

## Consequences

Positive:
- PR/HVR technické validation může pokračovat i při vyčerpané MCP quota;
- CI, HVR, Example a project runtime mohou používat nezávislé identity;
- pozdější corporate migration mění primárně environment bindings, nikoli Miro runtime architekturu;
- project board lifecycle je automatizovatelný přes REST API.

Negative:
- více secret/env names musí být spravováno explicitně;
- bootstrap Platform Lab a Example boardu potřebuje jednorázovou environment konfiguraci;
- starý single-token kontrakt musí být po 0.1.0 řízeně odstraněn.

New obligations:
- žádný workflow nesmí deklarovat MCP jako required technical gate;
- profile bindings musí být testované a nesmí obsahovat raw secrets;
- CI/HVR write path musí být fail-closed a exact-SHA bound;
- persistent board cleanup smí odstraňovat pouze explicitně owned/managed IDs;
- přístupová identita a board/team/Space musí být součástí evidence jako ne-secret metadata.

## Impact

Platform areas:
- METHODOLOGY
- SECURITY-GOVERNANCE
- ORCHESTRATION
- TESTING
- CLI / WORKSPACE-GENERATOR contracts
- DOC

Impact: HIGH, non-breaking migration.

Existing workspaces:
- stávající `miro.access_token_env`, `team_id(_env)`, `project_id(_env)` a `board_id(_env)` zůstávají platné;
- legacy `MIRO_ACCESS_TOKEN` zůstává pro PR #8 fallbackem;
- žádná gate decision ani client workspace se automaticky nemigruje.

## Validation

- schema/policy test ověří všechny povinné execution profiles;
- security test ověří, že profilová konfigurace obsahuje pouze názvy secret/env proměnných, nikoli token values;
- PR #8 HVR workflow použije REST credential chain a explicitní Platform Lab board binding;
- exact-SHA HVR musí prokázat remote write, fresh read-back a zero-mutation second reconcile;
- MCP nedostupnost nebo quota exhaustion nesmí změnit technical PASS/FAIL, pouze dostupnost interaktivního review kanálu.

## Follow-up actions

- [ ] Založit/standardizovat skutečný `DDDA Platform Lab` board a managed CI namespace místo historického bootstrap targetu.
- [ ] Založit a release-flowem plnit `DDDA Example Project` board.
- [ ] Doplnit project generator UX pro project-specific identity/token/team/Space env names a secure local credential profiles.
- [ ] Po získání corporate oprávnění rebinding Platform Lab/Example/runtime do corporate Miro teamu/Space bez změny runtime kontraktu.
- [ ] Odstranit legacy `MIRO_ACCESS_TOKEN` fallback po dokončení migračního období.
