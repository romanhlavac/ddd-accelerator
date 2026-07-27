# DDDA platform product roadmap

## Účel

Tento dokument je verzovanou dlouhodobou produktovou vizí DDDA platformy. Neplní roli operativního backlogu. Detail požadavků, priorit a acceptance evidence zůstává v GitHub Issues, Projectu, Milestones a PR.

Roadmap používá stabilní Work Package identifikátory `WP-XX`, nikoli budoucí GitHub PR čísla.

## Produktová vize

DDDA má být auditovatelná, chat-first a Miro-first platforma pro socio-technickou architekturu a Domain-Driven Design, která:

- vede uživatele od business problému k doménovým a architektonickým rozhodnutím;
- odděluje metodiku, platformní runtime, workspace a klientská data;
- používá Git jako source of truth pro sémantické artefakty a audit;
- používá Miro jako řízenou workshopovou a vizuální projekci;
- automatizuje mechanické kontroly, ale nepředstírá lidský judgment;
- vytváří reprodukovatelné release package a example workspace;
- umožňuje inkrementálně doplňovat strategické, ingestion a agentické capabilities;
- zachovává explicitní scope, data ownership, security boundaries a human release decision.

## Roadmap overview

| WP | Název | Outcome | Aktuální stav | Target release |
|---|---|---|---|---|
| WP-08 | Platform lifecycle & project steering | reprodukovatelný platformní lifecycle, evidence-driven steering G1–G8 a release governance | active / blocked by Human Review | 0.1.0 |
| WP-09 | Strategy, portfolio & program lifecycle | propojení situational awareness, programu P0–P10, portfolia, DDD a týmového designu | backlog | TBD |
| WP-10 | Enterprise ingestion | bezpečná a auditovatelná ingestion Office, PDF, ArchiMate a dalších enterprise zdrojů | backlog | TBD |
| WP-11 | EventStorming & multi-agent orchestration | proveditelný EventStorming workflow a řízená agentická orchestrace s human gates | backlog | TBD |

## Závislosti

```text
WP-08 Platform lifecycle & steering
   ├── enables reliable validation, packaging and human review
   ├── prerequisite for release-grade WP-09
   ├── prerequisite for release-grade WP-10
   └── prerequisite for release-grade WP-11

WP-09 Strategy & portfolio
   ├── informs prioritization of domain and modernization work
   └── can consume evidence from WP-10 and execution support from WP-11

WP-10 Enterprise ingestion
   ├── provides normalized evidence and provenance
   └── feeds strategy, discovery and agent workflows

WP-11 EventStorming & multi-agent orchestration
   ├── consumes governance and evidence contracts
   └── must preserve human-only decisions and explicit conflict handling
```

WP-09 až WP-11 mohou mít discovery práci před dokončením WP-08, ale jejich implementační release flow musí používat stabilizovaný lifecycle, validation report a Human Review kontrakty z WP-08.

## Strategické principy roadmapy

1. **Nezačínat technologií.** Každý Work Package vychází z platformního problému a uživatelské hodnoty.
2. **Outcome před feature listem.** WP je ukončen až splněním outcome a exit criteria.
3. **Jeden PR není automaticky jeden WP.** Work Package se skládá z menších delivery slices.
4. **Žádná prázdná plánovaná PR.** Backlog patří do Issues; PR vzniká při implementaci.
5. **Stabilní identita je WP-XX.** GitHub issue/PR čísla jsou pouze konkrétní realizační odkazy.
6. **Release scope je Milestone.** Roadmap neznamená automatické přiřazení verze.
7. **Human decisions zůstávají lidské.** CI, Miro ani agent nesmí schválit gate nebo release.
8. **Package-first validation.** Release-grade capability se ověřuje z candidate/release package v izolovaném example workspace.
9. **Manifest-driven evidence.** Ingestion a source provenance nesmí záviset na ručním kopírování.
10. **Evoluční delivery.** Velké capabilities se dělí na reversible, testovatelné inkrementy.

## Detail Work Packages

- [WP-08 — Platform lifecycle & project steering](work-packages/WP-08-platform-lifecycle-and-steering.md)
- [WP-09 — Strategy, portfolio & program lifecycle](work-packages/WP-09-strategy-portfolio-program-lifecycle.md)
- [WP-10 — Enterprise ingestion](work-packages/WP-10-enterprise-ingestion.md)
- [WP-11 — EventStorming & multi-agent orchestration](work-packages/WP-11-eventstorming-multi-agent-orchestration.md)

## Aktualizace roadmapy

Roadmap se aktualizuje při:

- vytvoření, změně hranic nebo uzavření Work Package;
- schválení nové strategické závislosti;
- přiřazení cílového release;
- významném scope split nebo supersede;
- dokončení release, který mění stav WP;
- nové GAP analýze.

Operativní změny priority se zapisují pouze do GitHub Projectu, pokud nemění dlouhodobý směr nebo WP boundaries.

## Stavová legenda

- `backlog` — outcome je definován, ale implementace nebyla zahájena;
- `discovery` — probíhá doplnění evidence a variant;
- `ready` — první delivery slice splňuje Ready criteria;
- `active` — existuje aktivní implementace;
- `blocked` — existuje konkrétní překážka s podmínkou odblokování;
- `done` — splněna exit criteria WP;
- `cancelled` — vědomě ukončeno;
- `superseded` — nahrazeno jiným WP nebo rozhodnutím.

## Co roadmapa neobsahuje

- detailní issue acceptance criteria;
- přesné pořadí jednotlivých backlog items;
- kompletní design implementace;
- test logy;
- Human Release Decision;
- neodsouhlasené release verze.
