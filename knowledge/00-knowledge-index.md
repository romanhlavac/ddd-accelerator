# DDDA knowledge index

Knowledge soubory se načítají podle typu práce, nikoli všechny současně. Nejdříve vždy určuj execution rovinu.

| Úloha | Runtime | Načíst |
|---|---|---|
| **vývoj DDDA platformy** | **Chat / Work** | **`ddda-platform-development-skill.md` a `../docs/developer-guide/chat-work-operating-model.md`** |
| **GitHub Project V2, backlog governance, WP/CR hierarchie a konzistence Project fields** | **Chat / Work** | **`ddda-platform-development-skill.md` + `ddda-github-project-v2-governance-skill.md`** |
| **Miro identity, REST/MCP, Platform Lab, HVR a credential governance** | **Chat / Work nebo Cursor podle scope** | **`13-miro-integration-operating-model.md` a `../docs/developer-guide/miro-execution-profiles.md`** |
| **používání DDDA v konkrétním projektu** | **Cursor** | **projektový status, tailoring, relevantní knowledge/cookbook soubory a `.cursor` runtime assets** |
| operating model a způsob práce | Cursor project runtime | `01-operating-model.md` |
| doména, subdomény, bounded contexts | Cursor project runtime | `02-ddd-strategic-design.md` |
| agregáty, invarianty, domain events | Cursor project runtime | `03-ddd-tactical-design.md` |
| ADR a rozhodování | Cursor project runtime | `04-architecture-decision-making.md` |
| quality attributes | Cursor project runtime | `05-quality-attributes.md` |
| architektonický styl | Cursor project runtime | `06-architecture-styles-and-tradeoffs.md` |
| integrace a data ownership | Cursor project runtime | `07-integration-and-data-ownership.md` |
| legacy a migrace | Cursor project runtime | `08-modernization-and-migration.md` |
| bezpečnost, resilience, observabilita | Cursor project runtime | `09-security-resilience-observability.md` |
| Team Topologies a governance | Cursor project runtime | `10-team-topologies-and-governance.md` |
| workshopy | Cursor project runtime | `11-workshop-playbooks.md` |
| formát výstupu | Cursor project runtime | `12-output-templates.md` |

## Rovina A — vývoj DDDA platformy

Při vývoji platformy musí Chat nebo Work načíst `ddda-platform-development-skill.md` ještě před klasifikací, návrhem nebo aplikací změny.

Pokud úloha sahá na GitHub Project V2, projektový backlog, Work Package/Change Request hierarchii nebo Project metadata, musí navíc načíst `ddda-github-project-v2-governance-skill.md` ještě před tvrzením, že Project write není dostupný, a před jakoukoli backlog mutation.

```text
Chat / Work
→ platform PR branch
→ GitHub Actions exact-SHA validation
```

Pro platformní vývoj nepoužívej Codex ani Cursor. GitHub Actions je autoritativní execution plane pro build, testy, candidate package a package-first validation. Secrets nesmějí vstoupit do Chat nebo Work kontextu.

Miro platformní automatizace je REST-first. GitHub Actions používá explicitní execution profile a secret store; Miro MCP je volitelný interaktivní control/review plane a nesmí být technical-gate dependency.

GitHub Project V2 administrace používá versioned governance automation a při chybějícím Project oprávnění GitHub CLI + GraphQL s user `project` scope a browser/device autorizací. Nedostupnost přímého Project V2 write endpointu v connectoru sama o sobě neznamená, že je administrace nemožná.

## Rovina B — používání DDDA v projektu

Cursor je základní agentic systém pro práci architekta v konkrétním DDDA project workspace.

Cursor musí načíst:

```text
project.yaml
project-intake.yaml
lifecycle-tailoring.yaml
artifacts/status/current-status.yaml
.cursor/rules/*.mdc
.cursor/skills.md
relevantní knowledge a cookbook soubory
```

Cursor smí měnit pouze aktivní project repository. Nesmí měnit DDDA platform repository. Platformní defect nebo enhancement se zaznamená jako change request a předá do Chat/Work platform-development flow.

Projektový Miro runtime používá explicitní `project.yaml` binding pro token env, team, Space/project ID a board. Board může projektový runtime přes REST vytvořit sám, pokud chybí a je explicitně povolen create-board flow. MCP zůstává volitelný pro interaktivní práci.

Fakta zachovej se source path; hypotézy označ `candidate`; rozhodnutí vyžadují ownera a explicitní review boundary.