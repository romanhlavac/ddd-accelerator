# DDDA Cursor project runtime

Cursor je základní agentic systém pro používání DDDA v konkrétním architektonickém projektu.

Tento soubor se nevztahuje na vývoj DDDA platformy. Platforma se vyvíjí pouze přes Chat/Work a technicky validuje v GitHub Actions.

## Úloha Cursoru

Cursor poskytuje architektovi:

- chat nad project workspace;
- agentic práci se soubory a projektovými artefakty;
- analýzu business a technických vstupů;
- řízenou tvorbu DDD artefaktů;
- práci s projektovým Git repository;
- spouštění projektových DDDA příkazů a validací;
- přípravu podkladů pro workshopy, ADR, context maps, bounded contexts a integrační návrh.

## Povinný pracovní model

1. Vždy pracuj pouze v aktivním DDDA project repository.
2. Načti `project.yaml`, `project-intake.yaml`, `lifecycle-tailoring.yaml`, aktuální status a relevantní knowledge/cookbook soubory.
3. Začni business problémem, ubiquitous language, aktéry, rozhodnutími, quality attributes, omezeními, data ownership a týmovými dopady.
4. Rozlišuj fakta, hypotézy, rozhodnutí a generované projekce.
5. Zachovej traceability ke zdrojům.
6. DDD artefakty považuj za hypotézy, dokud nejsou validované doménovými experty nebo příslušnou gate.
7. Gate approval, zásadní bounded-context hranice, ADR a risk acceptance vyžadují člověka.
8. Před zápisem ukaž plán, dotčené projektové cesty, očekávaný diff, validaci a rollback.
9. Nesmíš měnit DDDA platform repository.
10. Platformní defect nebo enhancement předej jako change request do Chat/Work platform-development flow.

## Typické projektové výstupy

- domain glossary a ubiquitous language;
- commands, decisions a domain events;
- business rules, policies a invarianty;
- actors, systems a data ownership;
- candidate subdomains a bounded contexts;
- context map a integrační kontrakty;
- quality-attribute scenarios;
- ADR;
- workshop artefakty;
- lifecycle status, evidence a next actions;
- projektový kód a dokumentace, pokud patří do schváleného scope.

## Bezpečnostní hranice

- žádné secrets v chatu, souborech nebo commitech;
- žádné cross-repository commity;
- žádný automatický push, merge, release nebo gate approval;
- žádné silent last-write-wins řešení sémantických konfliktů;
- klientská data zůstávají pouze ve schváleném project workspace a schválených systémech.
