# DDDA knowledge index

Tento adresář je stručný metodický kontrakt pro chat a agenty. Uživatelské postupy jsou v `USAGE.md` a `docs/cookbooks/`; knowledge soubory se načítají podle úlohy, nikoli všechny současně.

| Úloha | Načíst |
|---|---|
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

Vždy nejprve načti `project.yaml`, `project-intake.yaml`, `lifecycle-tailoring.yaml` a `artifacts/status/current-status.yaml`. Fakta zachovej se source path; hypotézy označ `candidate`; rozhodnutí vyžadují ownera a review boundary v Gitu.
