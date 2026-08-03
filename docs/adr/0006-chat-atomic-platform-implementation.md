# ADR: Povolit atomickou implementaci platformy z Chatu při nedostupném Work

Status: Accepted

Date: 2026-08-03

## Context

DDDA platform development povoluje pouze Chat a Work; Codex a Cursor jsou pro změnu platform repository zakázány. Work je vhodný pro vícekrokovou implementaci, ale nemusí být vždy dostupný. Současná metodika přitom deklarovala Chat jako povolený a výchozí interakční režim, ale prakticky přisuzovala implementaci výhradně Work.

Pokus použít `issue_comment` remediation broker před mergem odhalil bootstrap deadlock: GitHub spouští tento typ workflow pouze z definice dostupné na default branchi. Workflow existující pouze v dosud nemergované PR branchi proto nemůže být samo použito k aktivaci svého bootstrapu.

Prioritní quality attributes:

- auditability;
- atomicity;
- exact-SHA reproducibility;
- least privilege;
- absence secrets v Chat runtime;
- minimalizace mezilehlých stavů branche;
- standardní CI jako technický gate;
- jasné oddělení technického PASS a human review.

## Decision

Work zůstává preferovaným implementačním režimem. Pokud Work není dostupný, povolujeme `chat-atomic` režim:

```text
exact PR HEAD
→ immutable exact-SHA source snapshot
→ complete Git tree
→ one commit with exact parent
→ non-force fast-forward update of the same PR branch
→ standard exact-SHA PR CI
→ evidence review
```

Chat nesmí provádět sekvenční multi-file zápisy přes GitHub Contents API. Musí vytvořit celý Git tree a jeden commit prostřednictvím schváleného GitHub Git Data API konektoru. `main`, force-push, merge, promotion, release a tag zůstávají zakázány bez samostatné autorizace.

Chat nemá přístup k secrets a nesmí provádět secret-bearing online acceptance. Tyto kroky zůstávají v GitHub Actions. Technický PASS vzniká až po standardním CI na výsledném SHA. Při selhání se historie automaticky nepřepisuje; používá se korektivní commit nebo revert.

Control-plane soubory jsou normálně chráněné. Jejich bootstrap změna vyžaduje explicitní lidskou autorizaci, nejvýše jeden staging commit, self-removing staging artefakt a nejvýše jeden finální atomický commit.

## Options considered

### A. Implementace pouze přes Work

Pros: jednoduchý model a dobrá orchestrace.

Cons: blokuje vývoj při nedostupnosti Work a nevyužívá bezpečné atomické Git operace dostupné v Chatu.

### B. Sekvenční Chat zápisy přes Contents API

Pros: jednoduchá dostupnost konektorů.

Cons: každý soubor vytváří samostatný commit, vznikají nevalidní mezistavy, složitý rollback a slabší audit. Zamítnuto.

### C. Chat atomic Git tree commit

Pros: jeden reviewovatelný commit, exact parent, fast-forward guard, žádné mezilehlé multi-file stavy, standardní CI.

Cons: pre-push test evidence je omezená na source snapshot a statické kontroly; autoritativní test přichází až po zápisu v GitHub Actions.

## Consequences

Positive:

- platformní vývoj může pokračovat i bez Work;
- Work zůstává preferovaný;
- Chat změna je atomická a exact-SHA bound;
- technické testy a secrets zůstávají v GitHub Actions;
- nevznikají sekvenční více-souborové commits.

Negative:

- CI selhání může nastat až po fast-forward zápisu na PR branch;
- rollback po zápisu je korektivní commit nebo revert, nikoli přepis historie;
- Chat musí explicitně dokládat source snapshot, tree commit a update-ref evidence.

## Validation

- policy deklaruje `preferred_implementation_mode: work`;
- policy povoluje pouze `work` a `chat-atomic`;
- Chat atomic vyžaduje exact base SHA, complete tree, jeden commit, non-force update a standardní CI;
- přímý multi-file Contents API transport je zakázán;
- governance testy ověřují uvedené kontrakty;
- standardní PR CI běží nad výsledným exact SHA.
