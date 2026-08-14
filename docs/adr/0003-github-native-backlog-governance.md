# ADR 0003: GitHub-native backlog governance and delivery projection

Status: Proposed

Date: 2026-07-27

Last updated: 2026-08-14

## Context

DDDA platforma se vyvíjí jako verzovaný produkt. Potřebuje oddělit:

- dlouhodobé roadmap bloky a stabilní Work Package identity;
- konkrétní Change Requests a jejich planning metadata;
- skutečně zahájenou implementaci reprezentovanou Pull Requesty;
- release scope, validation evidence a Human Review.

Původní model správně zakázal používat budoucí nebo prázdné PR jako backlog. Současně ale nechával Project membership aktivních implementačních PR volitelnou. Tím vznikla mezera: GitHub Project byl planning authority, ale neposkytoval deterministickou, kompletní a auditovatelnou projekci právě probíhající delivery.

Požadovaný model musí zachovat Issue/WP jako planning authority a zároveň zobrazit všechny otevřené implementační PR bez toho, aby z nich vytvořil druhé Change Requests.

Prioritní quality attributes:

- traceability;
- auditability;
- process safety;
- clarity of ownership;
- modifiability;
- low operational overhead;
- compatibility with GitHub-native workflows.

## Decision

DDDA používá jeden GitHub Project `DDDA Platform Backlog & Delivery` se dvěma kanonickými projekcemi:

```text
Plánování a Backlog
Table / is:issue

Implementace a Delivery
Table / is:pr is:open
```

Authority model:

```text
GitHub Issue / Work Package / Change Request
  planning authority pro požadavek, WP ownership, scope a roadmap.

GitHub Project planning item
  operativní planning projection Issue/WP/CR.

Branch + Pull Request
  skutečně zahájená implementace.

GitHub Project delivery item
  povinná projekce každého otevřeného implementačního PR.

Milestone
  autorita pro cílový release scope.

ADR
  autorita pro dlouhodobé architektonické rozhodnutí.

CI + validation/audit report
  technická evidence pro exact source SHA.

Human Review / HRDR
  lidská evidence a GO/NO-GO; není nahrazena technickou automatizací.
```

### Delivery derivation rules

Každý open implementation PR kromě explicitní verzované legacy výjimky musí mít právě jeden primary relationship:

```text
Implements #<CR>
```

nebo

```text
Closes #<CR>
```

Jeho Project metadata jsou mechanicky odvozena:

```text
Work Package = Work Package(primary CR)
Item Type    = <unset>
Status       = Blocked      if Blocked = Yes
               In progress  if Draft and not blocked
               In review    if open non-draft and not blocked
```

`Refs`, `Related`, title prefix ani stacked Git ancestry nejsou primary implementation authority.

Plánované nebo prázdné PR se nadále nepoužívají jako backlog. Povinná membership se vztahuje na **otevřené implementační PR**, nikoli na budoucí práci.

PR #8 je do merge/close jediná verzovaná legacy výjimka pro chybějící primary CR a je fixně mapován na WP-08. Jeho source branch/head nesmí být touto governance změnou měněn.

## Options considered

### Option A: Issues-only Project, PR Project membership volitelná

Výhody:

- nejjednodušší Project model;
- nulová duplicita vizuálního obsahu.

Nevýhody:

- neúplná live delivery visibility;
- delivery status je odvozován nepřímo přes Linked PRs;
- repository-wide read-back nemůže deterministicky ověřit Project-level PR metadata.

Decision: **rejected**.

### Option B: Každý PR jako druhý backlog item se stejným planning typem

Výhody:

- vysoká viditelnost implementace.

Nevýhody:

- duplikuje Change Request authority;
- míchá planning a delivery semantics;
- vzniká riziko nezávislého driftu Priority, Item Type a WP.

Decision: **rejected**.

### Option C: Jeden Project, oddělená planning a delivery projection

Výhody:

- Issues/WP/CR zůstávají planning authority;
- všechny open implementation PRs jsou explicitně viditelné;
- PR metadata lze deterministicky odvodit a fail-closed read-backovat;
- jeden Project, jeden governance control plane, nízký operational overhead.

Nevýhody:

- Project obsahuje Issue i PR items;
- reconciler musí rozlišovat planning a delivery fields;
- vyžaduje explicitní primary CR contract.

Decision: **accepted direction**.

## Consequences

### Positive

- planning backlog a aktivní delivery jsou oddělené, ale trasovatelné;
- každý otevřený PR je dohledatelný v Projectu;
- WP ownership PR nevzniká ručně, ale z primary CR;
- delivery status je reprodukovatelný;
- audit může ověřit celý Project contract a skončit s `remaining_mismatches = 0`.

### Negative

- live Project reconciliation je privileged operace;
- každé nové implementační PR musí mít jednoznačný primary CR;
- staré/stale PR mohou při zavedení kontraktu způsobit fail-closed governance blocker.

### New obligations

- každý významný GAP má Issue;
- každý velký roadmap blok má Parent Work Package Issue a `WP-XX`;
- každý aktivní implementační PR je Project delivery item;
- každý non-legacy open implementation PR má právě jeden primary CR;
- delivery PR `Item Type` je unset;
- canonical views a Project title jsou versioned contract;
- repository-wide post-change read-back musí mít nula nevysvětlených mismatchů;
- technical PASS zůstává oddělen od Human Review, Ready, merge a release approval.

## Impact

Platform areas:

- `SECURITY-GOVERNANCE`;
- `TESTING`;
- `DOC`;
- `RELEASE`.

Impact: `HIGH`.

Existing client workspaces: žádný dopad; governance se týká pouze platform repository a jeho GitHub Projectu.

Migration: additive změna Project contractu a live Project metadata. Nevyžaduje retroaktivní Git split existujících branches/PR. PR #8 zůstává nedotčen.

## Validation

Ověřit pro exact PR #63 SHA:

- JSON/bootstrap a policy contract;
- deterministic regression test pro planning + delivery semantics;
- exact-SHA `Validate DDDA` PASS;
- privileged reconciliation až po technické validaci target SHA;
- live Project title a dvě canonical views;
- všechny governed WP/CR planning items;
- všechny open implementation PR delivery items;
- PR → primary CR → WP mapping;
- PR delivery Status a absence `Item Type`;
- title-prefix consistency;
- final read-back `remaining_mismatches = 0`;
- audit artifact svázaný s exact source SHA.

## Risks and mitigations

| Riziko | Dopad | Pravděpodobnost | Mitigace |
|---|---:|---:|---|
| PR nemá jednoznačný primary CR | High | Medium | fail-closed; nehádat ownership |
| Project metadata driftuje | High | Medium | idempotent reconciler + repository-wide post-read-back |
| PR se začne chovat jako druhý backlog | High | Medium | `Item Type = unset`, planning authority zůstává CR |
| Stale title WP prefix mate uživatele | Medium | Medium | `PRESENTATION_WP_MISMATCH` fail-closed check |
| Privileged Project token se použije z ne-reviewovaného PR | High | Low | manual `workflow_dispatch`, protected environment, no `pull_request` trigger |
| Automatizace předstírá human approval | High | Low | technical evidence a Human Review jsou oddělené dimenze |
| PR #8 bude governance změnou poškozen | High | Low | explicitní immutable scope: žádná mutace PR #8 source branch/head |

## Follow-up actions

- [ ] aplikovat změnu jako jeden exact-SHA-bound commit na PR #63 branch;
- [ ] spustit exact-SHA `Validate DDDA`;
- [ ] po technickém PASS ručně spustit privileged Project reconciliation pro stejný target SHA;
- [ ] uložit v6 audit evidence s `remaining_mismatches = 0`;
- [ ] aktualizovat PR #63 technical evidence;
- [ ] před Ready/merge provést samostatný Human Review podle platform lifecycle.
