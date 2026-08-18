# ADR 0008: Human Release Decision a fail-closed Release Scope Gate

- Status: **Proposed**
- Date: 2026-08-18
- Decision owner: Roman Hlaváč (`romanhlavac`)
- Related: #9, #12, #15, #17, #67, #68, PR #8 / DDDA 0.1.0

## Context

DDDA 0.1.0 prokázalo, že tři různé otázky release readiness musí být modelovány odděleně:

1. **Technical candidate evidence** — CI, `validate-pr`, package hash, Miro technical acceptance a další mechanické důkazy.
2. **Human Release Decision** — lidské `GO`, `GO_WITH_ACCEPTED_RISKS` nebo `NO_GO`, včetně explicitního přijetí residual risks.
3. **Release-scope completeness** — zda autoritativní release scope v Issues, native dependencies, Milestone a GitHub Project projekci skutečně neobsahuje neuzavřenou/neodloženou práci nebo neakceptovaný blocker.

Při PR #8 byly první dvě dimenze dostatečné pro promotion, ale post-release read-back ukázal, že #12 zůstalo otevřené a #15 je podle svého DoD na #12 závislé. Promotion preflight tuto nekonzistenci nevynutil před nevratným merge.

Tento ADR nepřepisuje historický release 0.1.0 ani jeho human decision. Definuje prospektivní reusable governance contract.

## Decision

DDDA zavádí dva explicitně oddělené release-governance gates:

```text
Human Release Decision Gate
  human judgment / authorization

Release Scope Gate
  deterministic mechanical completeness/consistency check
```

Promotion je povoleno pouze při současném splnění:

```text
candidate evidence valid
AND Human Release Decision valid
AND Release Scope Gate PASS
AND explicit merge/promotion authorization
```

### Human Release Decision authority

Human Release Decision Record (HRDR) je vázán minimálně na:

- repository;
- PR;
- branch;
- exact source SHA;
- candidate package SHA-256;
- target version;
- reviewer;
- concrete decision owner;
- timestamp;
- findings GREEN/AMBER/RED;
- accepted residual risks;
- authoritative release scope snapshot.

Automation smí vytvořit pouze `pending` scaffold, validovat jeho strukturu/evidence a publikovat read-back. Automation nesmí:

- vytvořit nebo inferovat `GO`;
- změnit lidské rozhodnutí;
- přidat nebo odebrat accepted risk;
- zvolit decision ownera;
- převést technical PASS na Human Review/Release PASS.

Autoritativní decision comment je explicitně označen markerem:

```text
<!-- ddda:human-release-decision:v1 -->
```

a obsahuje machine-readable JSON podle `schemas/human-release-decision.schema.json`.

### Release Scope Gate authority

Release Scope Gate je read-only, fail-closed a vyhodnocuje živý autoritativní stav:

```text
GitHub Milestone / version identity
+ Issue state
+ native unresolved blocked-by
+ Project planning projection
+ HRDR exact candidate/version identity
+ accepted-risk follow-up Issues
```

Project je projekce, nikoli release source of truth. Nesoulad projekce proti Issue/native/milestone authority je ale governance failure.

Gate `PASS` vyžaduje:

- právě jeden odpovídající release milestone;
- current-release Issues přesně odpovídají HRDR scope;
- všechny current-release Issues jsou terminal;
- žádný current-release Issue nemá unresolved native blocker;
- Project `Status=Done`, `Blocked=No` pro current-release Issues;
- Project title a kanonické planning/delivery view odpovídají kontraktu;
- deferred accepted-risk Issues nejsou v current release milestone, zůstávají otevřené, mají explicitního ownera a target/horizon;
- HRDR neobsahuje RED;
- `GO` nemá accepted risks; `GO_WITH_ACCEPTED_RISKS` má neprázdný explicitní risk set;
- live PR head, HRDR source SHA, candidate package hash a version se shodují.

Nedostupný Project read-back nebo chybějící credential není warning. Gate skončí `FAIL`.

### Irreversible side-effect boundary

Canonical `ddda.ps1 promote-pr` se routuje přes governed wrapper. Legacy/internal release executor není public bypass.

```text
HRDR read-back
→ candidate hash read-back
→ Release Scope Gate
→ PASS
→ existing promote-pr executor
```

Při `FAIL` se legacy executor vůbec nezavolá. Tím je PR8-class regression reprezentována explicitním `side_effects_allowed=false`.

### Credential boundary

- běžné GitHub REST čtení používá existující DDDA GitHub authentication contract;
- Project V2 read-back vyžaduje `DDDA_GITHUB_PROJECT_TOKEN`;
- token se předává pouze přes process environment;
- token se neukládá do HRDR, reportu, CLI arguments ani Chatu/Work contextu.

## Alternatives considered

### A. Spoléhat pouze na HRDR

Zamítnuto. HRDR je human decision evidence, ale sám nemusí odhalit drift Milestone/Project/native dependency po jeho vytvoření.

### B. Považovat GitHub Project status za release gate

Zamítnuto. Project je operativní projekce, ne release authority, a může driftovat.

### C. Kontrolovat pouze open/closed milestone Issues

Zamítnuto. Nezachytí native blockers, stale Project projection ani accepted-risk provenance.

### D. Automaticky převádět open Items na accepted risks

Zamítnuto. To by automatizaci umožnilo měnit lidské risk acceptance.

## Consequences

### Positive

- technický PASS už nemůže obejít neúplný release scope;
- human judgment a mechanická completeness mají jasnou authority boundary;
- scope drift po review je detekovatelný;
- PR8-class failure má deterministický regression contract;
- gate může být auditován machine-readable evidence.

### Costs

- promotion vyžaduje Project read credential;
- release milestone a Project projection musí být před merge skutečně konzistentní;
- open implementation Issue musí být před promotion uzavřeno nebo explicitně přesunuto mimo release scope;
- HRDR musí být při relevantním scope/SHA/package driftu znovu rozhodnut člověkem.

## Validation

Povinné testy zahrnují:

- schema;
- positive release-scope scenario;
- open current-release Issue;
- unresolved blocker;
- milestone scope drift;
- Project status/blocked drift;
- source/package drift;
- missing accepted-risk owner/horizon;
- RED;
- pending human decision;
- PR8-class zero-side-effect invariant.

## Historical note

DDDA 0.1.0 zůstává `RELEASED — GO_WITH_ACCEPTED_RISKS` s accepted-risk setem přesně #66 a #67. Tento ADR ani nová gate tento historický record nemění.
