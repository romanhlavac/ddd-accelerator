# DDDA knowledge index

Tento adresář je stručný metodický kontrakt pro Chat a Work. Uživatelské postupy jsou v `USAGE.md` a `docs/cookbooks/`; knowledge soubory se načítají podle úlohy, nikoli všechny současně.

| Úloha | Načíst |
|---|---|
| **vývoj DDDA platformy** | **`ddda-platform-development-skill.md` — povinně před návrhem nebo provedením změny platformy** |
| **Chat/Work operating model** | **`../docs/developer-guide/chat-work-operating-model.md` — povinně pro implementaci, GitHub/Miro zápisy a CI orchestration** |
| operating model a způsob práce | `01-operating-model.md` |
| doména, subdomény, bounded contexts | `02-ddd-strategic-design.md` |
| agregáty, invarianty, domain events | `03-ddd-tactical-design.md` |
| ADR a rozhodování | `04-architecture-decision-making.md` |
| quality attributes | `05-quality-attributes.md` |
| architektonický styl | `06-architecture-styles-and-tradeoffs.md` |
| integrace a data ownership | `07-integration-and-data-ownership.md` |
| legacy a migrace | `08-modernization-and-migration.md` |
| bezpečnost, resilience, observabilita | `09-security-resilience-observability.md` |
| Team Topologies a governance | `10-team-topologies-and-governance.md` |
| workshopy | `11-workshop-playbooks.md` |
| formát výstupu | `12-output-templates.md` |

## Povinná registrace platformního skillu

Při vývoji DDDA platformy musí Chat nebo Work načíst `ddda-platform-development-skill.md` ještě před klasifikací, návrhem nebo aplikací změny. Registrace může být provedena tímto indexem nebo explicitními Project/Work Instructions, ale runtime musí používat aktuální verzovanou repository variantu. Samotná existence souboru v Gitu nezaručuje jeho automatické načtení.

Povolený execution mode je výhradně:

```text
Chat
Work
```

`Codex`, `/agent` a jiné neschválené cloudové coding agenty nepoužívej. GitHub Actions je autoritativní execution plane pro shell, build, testy, candidate package a package-first validation. Secrets nesmějí vstoupit do Chat nebo Work kontextu.

Vždy nejprve načti `project.yaml`, `project-intake.yaml`, `lifecycle-tailoring.yaml` a `artifacts/status/current-status.yaml`. Fakta zachovej se source path; hypotézy označ `candidate`; rozhodnutí vyžadují ownera a review boundary v Gitu.
