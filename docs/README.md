# Index dokumentace DDDA

## Začít zde

1. [Operating model: Chat/Work platform development a Cursor project runtime](developer-guide/chat-work-operating-model.md)
2. [Clone, smoke testy, workspace a example projekt](getting-started/01-clone-smoke-example.md)
3. [Validace a promotion platformního PR](user-guide/validate-and-promote-pr.md)
4. [Testování řiditelnosti projektu](getting-started/02-testovani-pr8.md)
5. [README platformy](../README.md)
6. [Úplný chat-first provozní návod](../USAGE.md)
7. [Katalog funkcionalit](capabilities/README.md)
8. [Řízené založení vlastního projektu](cookbooks/16-zalozeni-rizeneho-projektu.md)
9. [Current status, gaty a další krok](cookbooks/17-status-gates-a-dalsi-krok.md)
10. [Referenční projekt životní pojišťovny](../examples/life-insurance-greenfield/README.md)

## Getting started

- [01 Clone, smoke testy, workspace a example projekt](getting-started/01-clone-smoke-example.md)
- [02 Acceptance test řiditelnosti projektu](getting-started/02-testovani-pr8.md)

## Uživatelské návody

- [Validace a promotion platformního PR](user-guide/validate-and-promote-pr.md)

## Developer guide

- [Operating model: Chat/Work pro platformu, Cursor pro projekt](developer-guide/chat-work-operating-model.md)
- [Vývojový lifecycle DDDA platformy](developer-guide/platform-development-lifecycle.md)
- [Testovací strategie DDDA platformy](developer-guide/testing-strategy.md)
- [Remote validation a remediation broker](developer-guide/remote-validation-broker.md)

## Architektonická rozhodnutí a migrace

- [ADR 0001 — Reprodukovatelný lifecycle vývoje platformy](adr/0001-platform-development-lifecycle.md)
- [ADR 0002 — Project steering a gate semantics](adr/0002-project-steering-and-gate-semantics.md)
- [ADR 0003 — Control Center, Artifact Registry a kanonický workshop shell](adr/0003-miro-control-center-and-workshop-shell.md)
- [ADR 0004 — Redline traceability a navigovatelný frame 01](adr/0004-miro-redline-traceability-and-frame-01.md)
- [ADR 0005 — Chat/Work platform development a Cursor project runtime](adr/0005-chat-work-only-development-operating-model.md)
- [PR #8 migration note](migration/pr8-non-breaking-steering-extension.md)
- [Miro scaffold migration 2.4 → 2.5](migration/miro-scaffold-2.4-to-2.5.md)
- [Forenzní review REM-PR8-HVA-CC-001](reviews/REM-PR8-HVA-CC-001-forensic-review.md)
- [REM-PR8-HVA-CC-010 — nová human-review revize](reviews/REM-PR8-HVA-CC-010-gap-analysis.md)
- [REM-PR8-HVA-CC-011 — content coherence and traceability hardening](reviews/REM-PR8-HVA-CC-011-content-coherence.md)
- [Changelog](../CHANGELOG.md)

## Metodika

- [Metodický tok a gaty](methodology/01-metodicky-tok-a-gates.md)
- [Typy projektů, use cases a workflow](methodology/02-typy-projektu-toky-use-cases.md)
- [Facilitace EventStormingu](methodology/03-eventstorming-facilitace.md)
- [Evidence, statusy a lifecycle artefaktů](methodology/04-evidence-a-lifecycle-artefaktu.md)
- [Řízení projektu a lifecycle tailoring](methodology/05-rizeni-projektu-a-tailoring.md)

## Funkcionality

- [Lidsky čitelný capability katalog](capabilities/README.md)
- [Strojově validovaný capability katalog](reference/capability-catalog.yaml)

## Produkt a runtime

- [Architektura DDDA](product/01-architektura-ddda.md)
- [Workspace, Git a více projektů](product/02-workspace-a-projekty.md)
- [Miro scaffolding](product/03-miro-scaffolding.md)
- [Miro synchronizace, polling worker a konfliktní model](product/04-synchronizace.md)
- [Typy projektu v manifestu](product/05-typy-projektu.md)
- [Migrace a kompatibilita](product/06-migrace-a-kompatibilita.md)
- [Rozšiřování DDDA](product/07-rozsireni-ddda.md)

## Kuchařky

- [01 Založení projektu](cookbooks/01-zalozeni-projektu.md)
- [02 Příprava Miro boardu](cookbooks/02-priprava-miro-boardu.md)
- [03 Big Picture EventStorming](cookbooks/03-big-picture-eventstorming.md)
- [04 Process Modeling](cookbooks/04-process-modeling.md)
- [05 Design-Level EventStorming](cookbooks/05-design-level-eventstorming.md)
- [06 Stavové modely](cookbooks/06-stavove-modely.md)
- [07 Miro ↔ YAML ↔ Git](cookbooks/07-synchronizace-miro-yaml-git.md)
- [08 Gate review](cookbooks/08-gate-review.md)
- [09 Přidání typu projektu](cookbooks/09-pridani-typu-projektu.md)
- [10 Legacy modernizace](cookbooks/10-legacy-modernizace.md)
- [11 Chat-first pracovní režim](cookbooks/11-chat-first-pracovni-rezim.md)
- [12 Miro troubleshooting](cookbooks/12-miro-troubleshooting.md)
- [13 Inicializace po clone](cookbooks/13-inicializace-po-clone.md)
- [14 Inicializace cílového Miro boardu](cookbooks/14-inicializace-ciloveho-miro-boardu.md)
- [15 První spuštění a referenční example projekt](cookbooks/15-prvni-spusteni-a-example-projekt.md)
- [16 Založení řízeného projektu](cookbooks/16-zalozeni-rizeneho-projektu.md)
- [17 Current status, gaty a další krok](cookbooks/17-status-gates-a-dalsi-krok.md)

## Reference

- [CLI reference](reference/cli.md)
- [Datové a agentní kontrakty](reference/contracts.md)
- [Capability catalog YAML](reference/capability-catalog.yaml)
- [Knowledge index](../knowledge/00-knowledge-index.md)

## Strukturní pravidlo

V kořeni `docs/` je pouze tento index. Detailní dokumentace patří do `getting-started/`, `user-guide/`, `developer-guide/`, `adr/`, `migration/`, `reviews/`, `capabilities/`, `cookbooks/`, `methodology/`, `product/` nebo `reference/`.
