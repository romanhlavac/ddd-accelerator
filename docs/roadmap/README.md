# DDDA platform product roadmap

## Účel

Tento dokument je verzovanou dlouhodobou produktovou vizí DDDA platformy. Neplní roli operativního backlogu. Detail požadavků, priorit, dependencies a acceptance evidence zůstává v GitHub Issues, Projectu, Milestones a PR.

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
| WP-08 | Platform lifecycle & project steering | reprodukovatelný lifecycle, steering G1–G8 a human-controlled release governance | active / blocked by Human Review | 0.1.0 |
| WP-09 | Strategy, portfolio & program lifecycle | P0–P10, Wardley, portfolio, traceability, roadmap/benefits a program acceptance | backlog | TBD |
| WP-10 | Enterprise ingestion | bezpečná Office/PDF/ArchiMate ingestion, Markdown/YAML evidence a provenance | backlog | TBD |
| WP-11 | EventStorming & multi-agent orchestration | executable EventStorming, evidence-to-workshop flow, methodology guidance a bounded agents | backlog | TBD |

## Závislosti mezi Work Packages

```text
WP-08 Platform lifecycle & steering
   ├── validation, packaging, generic Miro and human-decision baseline
   ├── prerequisite for release-grade WP-09
   ├── prerequisite for release-grade WP-10
   └── prerequisite for release-grade WP-11

WP-09 Strategy & program
   ├── prioritizes outcomes and investment options
   ├── separates traceability (#25), roadmap/benefits (#50), Miro (#26) and acceptance (#51)
   └── may consume WP-10 evidence and WP-11 assistance

WP-10 Enterprise ingestion
   ├── evolves the PR #8 minimal ingestion baseline
   ├── provides normalized Markdown/YAML evidence and provenance
   └── feeds strategy, discovery and WP-11 workflows

WP-11 EventStorming & agents
   ├── extends the PR #8 generic Miro and preliminary agent baselines
   ├── consumes WP-10 registered evidence
   └── preserves explicit conflict handling and human-only decisions
```

WP-09 až WP-11 mohou mít discovery práci před dokončením WP-08. Release-grade implementation však musí používat stabilizované lifecycle, validation, generic Miro a Human Review kontrakty z WP-08.

## Dependency semantics

Roadmap a Issues rozlišují:

- **Direct blocked-by** — nativní dependency; položka nemůže dokončit DoD před blockerem;
- **Transitive prerequisite** — nepřímý předpoklad, který se nemá duplicitně přidávat do nativního grafu;
- **Consumed contract** — capability používá cizí kontrakt, ale vztah nemusí blokovat začátek práce;
- **Related work** — informační vztah bez scheduling semantics.

Dependency, priority, business value, capacity, sequencing, date a target release jsou oddělené dimenze.

## Scope a approval pravidla

- Parent/sub-issue membership určuje capability ownership, nikoli release scope.
- Milestone membership určuje release scope, nikoli release approval.
- Target release, priority, dates a owner se neurčují automaticky.
- Human Review PASS, gate `passed`, HRDR a GO/NO-GO vznikají pouze explicitním lidským rozhodnutím.
- PR #43 je samostatná governance implementace; PR #8 se jím nemerguje ani nemění source SHA.

Příklad: #45 je child WP-08, ale zůstává `Target Release: TBD` a není součástí `DDDA 0.1.0`.

## Strategické principy roadmapy

1. **Nezačínat technologií.** Každý WP vychází z platformního problému a user value.
2. **Outcome před feature listem.** WP končí až splněním outcome a exit criteria.
3. **Jeden PR není automaticky jeden WP.** Work Package se skládá z menších delivery slices.
4. **Žádná prázdná plánovaná PR.** Backlog patří do Issues; PR vzniká při implementation.
5. **Stabilní identita je WP-XX.** Issue/PR čísla jsou realizační odkazy.
6. **Milestone je release scope, ne approval.** Roadmap ani milestone nevydávají GO.
7. **Human decisions zůstávají lidské.** CI, Miro ani agent nesmí schválit gate/release.
8. **Package-first validation.** Release-grade capability se ověřuje z package v isolated workspace.
9. **Manifest-driven evidence.** Ingestion/provenance nesmí záviset na ručním copy/paste.
10. **Evoluční delivery.** Velké capabilities se dělí na explicitně vlastněné, testovatelné slices.
11. **Žádné paralelní kontrakty.** Budoucí WPs musí PR #8 baseline rozšířit, versionovat nebo migrovat.

## Detail Work Packages

- [WP-08 — Platform lifecycle & project steering](work-packages/WP-08-platform-lifecycle-and-steering.md)
- [WP-09 — Strategy, portfolio & program lifecycle](work-packages/WP-09-strategy-portfolio-program-lifecycle.md)
- [WP-10 — Enterprise ingestion](work-packages/WP-10-enterprise-ingestion.md)
- [WP-11 — EventStorming & multi-agent orchestration](work-packages/WP-11-eventstorming-multi-agent-orchestration.md)
- [GitHub backlog index](backlog-index.md)

## Aktualizace roadmapy

Roadmap se aktualizuje při:

- vytvoření, splitu, změně hranic nebo uzavření WP/Child Issue;
- změně přímé dependency nebo capability ownership;
- přiřazení target release;
- významném scope split/supersede;
- dokončení release měnícího stav WP;
- nové GAP analýze.

Operativní priority a dates se vedou v GitHub Projectu, pokud nemění dlouhodobý směr nebo WP boundaries.

## Stavová legenda

- `backlog` — outcome je definován, implementace nezačala;
- `discovery` — doplňuje se evidence a variants;
- `ready` — delivery slice splňuje Ready criteria;
- `active` — existuje aktivní implementation;
- `blocked` — existuje named blocker/unblock condition;
- `done` — DoD/exit criteria jsou splněny;
- `cancelled` — vědomě ukončeno;
- `superseded` — nahrazeno jiným WP/decision.

## Co roadmapa neobsahuje

- detailní issue acceptance criteria;
- operativní priority a přesné dates;
- kompletní implementation design;
- test logs;
- Human Release Decision;
- neodsouhlasené release verze.
