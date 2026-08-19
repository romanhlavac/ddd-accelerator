# ADR 0008: Human Review, governed implementation merge a fail-closed Release Scope Gate

- Status: **Accepted**
- Date: 2026-08-18
- Decision owner: Roman Hlaváč (`romanhlavac`)
- Related: #9, #12, #15, #17, #44, #67, #68, #70, PR #8 / DDDA 0.1.0, PR #74

## Context

DDDA 0.1.0 prokázalo, že release readiness nelze redukovat na jediný technický gate. Musí být odděleny minimálně:

1. **Technical candidate evidence** — CI, `validate-pr`, package hash a další mechanické důkazy.
2. **Human Review implementační změny** — lidské posouzení metodiky, architektury, gate semantics a dalších judgment-heavy aspektů konkrétního PR.
3. **Human Release Decision** — lidské `GO`, `GO_WITH_ACCEPTED_RISKS` nebo `NO_GO` pro konkrétní release candidate.
4. **Release-scope completeness** — zda autoritativní release scope v Issues, native dependencies, Milestone a GitHub Project projekci neobsahuje neuzavřenou/neodloženou práci nebo neakceptovaný blocker.

Post-release read-back 0.1.0 ukázal, že promotion nevynutil release-scope completeness před nevratným release tokem.

První implementace Release Scope Gate v PR #74 následně odhalila další problém: pokud stejný `promote-pr` současně slouží jako mechanismus merge každého implementačního PR a Release Scope Gate vyžaduje všechny release-scope Issues již terminal, vzniká u multi-PR releasu kruhová závislost:

```text
implementation Issue musí být terminal
→ Release Scope Gate může PASS
→ promotion může mergnout implementation PR

ALE

implementation PR musí být mergnut
→ Issue může být korektně terminal
```

Decision owner proto 2026-08-18 explicitně schválil oddělení **governed implementation merge** od **release/promotion**.

Tento ADR nepřepisuje historický release 0.1.0 ani jeho human decision.

## Decision

DDDA zavádí tři explicitně oddělené governance boundaries.

### 1. Human Review + governed implementation merge

Implementační PR používá tok:

```text
exact-SHA CI PASS
→ validate-pr PASS + candidate package binding
→ Human Review PASS pro stejné SHA/package
→ merge-pr -DryRun
→ explicitní human merge authorization
→ merge-pr -ConfirmMerge
→ merge do main
→ NO release package
→ NO release validation
→ NO tag
```

`merge-pr` je merge-only command. Nevyhodnocuje HRDR ani Release Scope Gate. Důvodem není oslabení release governance, ale odstranění kruhové závislosti: jednotlivé implementační změny musí být nejprve bezpečně integrovány, aby mohl vzniknout kompletní release candidate.

Human Review a merge authorization jsou dvě různé lidské akce. Automation nesmí vytvořit Human Review PASS ani merge authorization.

Human Review evidence je vázána minimálně na:

```text
repository
pr
reviewed_sha
candidate_package_sha256
reviewer
reviewed_at
verdict
```

Autoritativní implementation-review comment používá marker:

```text
<!-- ddda:human-pr-review:v1 -->
```

Změna PR SHA nebo package hash review invaliduje.

### 2. Human Release Decision

Human Release Decision Record (HRDR) se vytváří až pro **release candidate**, nikoli jako podmínka každého implementačního merge.

HRDR je vázán minimálně na:

- repository a release-candidate PR;
- exact source SHA;
- candidate package SHA-256;
- target version;
- reviewer a concrete decision owner;
- timestamp;
- findings GREEN/AMBER/RED;
- accepted residual risks;
- authoritative release-scope snapshot.

Automation smí vytvořit pouze `pending` scaffold, validovat strukturu/evidence a publikovat read-back. Nesmí vytvořit/inferovat `GO`, měnit lidské rozhodnutí, accepted-risk set ani decision ownera.

Autoritativní HRDR comment používá marker:

```text
<!-- ddda:human-release-decision:v1 -->
```

### 3. Release Scope Gate

Release Scope Gate je read-only a fail-closed. Vyhodnocuje se **pouze na release-candidate promotion boundary**:

```text
GitHub Milestone / version identity
+ Issue state
+ native unresolved blocked-by
+ Project planning projection
+ HRDR exact candidate/version identity
+ accepted-risk follow-up Issues
```

Gate `PASS` vyžaduje mimo jiné:

- právě jeden odpovídající release milestone;
- current-release Issues přesně odpovídají HRDR scope;
- všechny current-release Issues jsou terminal;
- žádný current-release Issue nemá unresolved blocker;
- Project `Status=Done`, `Blocked=No` pro current-release Issues;
- deferred accepted-risk Issues jsou mimo current release milestone, otevřené a mají ownera + target/horizon;
- HRDR nemá RED;
- risk set je přesně lidsky přijatý set;
- live release-candidate head, HRDR source SHA, candidate hash a version se shodují.

Nedostupný authoritative read-back je `FAIL`, nikoli warning.

## Canonical invariants

### Implementation merge

```text
implementation_merge_allowed =
    exact_sha_ci_valid
AND validate_pr_valid
AND candidate_package_hash_valid
AND human_review_pass_for_same_sha
AND explicit_merge_authorization
```

Release Scope Gate není součástí tohoto výrazu.

### Release promotion

```text
release_promotion_allowed =
    release_candidate_evidence_valid
AND HRDR_valid
AND ReleaseScopeGate == PASS
AND human_decision in {GO, GO_WITH_ACCEPTED_RISKS}
AND explicit_release_promotion_authorization
```

Implementation merge authorization nikdy neimplikuje release/promotion/tag authorization.

## Command boundary

Public CLI rozlišuje:

```powershell
.\ddda.ps1 merge-pr -Pr <PR> -DryRun
.\ddda.ps1 merge-pr -Pr <PR> -ConfirmMerge

.\ddda.ps1 review-pr -Pr <RELEASE_PR> -Version <VERSION> ...
.\ddda.ps1 promote-pr -Pr <RELEASE_PR> -Version <VERSION> -DryRun
.\ddda.ps1 promote-pr -Pr <RELEASE_PR> -Version <VERSION> -ConfirmMerge
```

`merge-pr` nesmí volat release executor. `promote-pr` je release command a jeho governed wrapper musí vyhodnotit HRDR + Release Scope Gate před dosažením release executor side effects.

## Alternatives considered

### A. Jeden `promote-pr` pro merge každého PR i release

Zamítnuto. Při striktním Release Scope Gate vytváří multi-PR deadlock a směšuje integration boundary s release boundary.

### B. Oslabit Release Scope Gate tak, aby toleroval open implementation Issues

Zamítnuto. Opravilo by to symptom za cenu ztráty hlavního post-0.1.0 invariantu: skutečný release nesmí proběhnout s nekompletním autoritativním scope.

### C. Automaticky uzavírat Issues před merge

Zamítnuto. Přepisovalo by skutečný delivery stav a vytvářelo falešnou governance projekci.

### D. Spoléhat pouze na HRDR

Zamítnuto. HRDR je human decision evidence, ale sám nemusí odhalit live drift release scope.

## Consequences

### Positive

- multi-PR release se nezablokuje kruhovou závislostí;
- Release Scope Gate může zůstat striktní;
- implementation merge je auditovatelný exact-SHA/package Human Review;
- release decision zůstává explicitně lidský;
- merge a release/tag jsou samostatně autorizované side effects;
- PR8-class failure zůstává pokrytelný deterministickou regresí.

### Costs

- lifecycle má dva explicitní příkazy/boundaries místo jednoho;
- před release je potřeba explicitní release candidate;
- Human Review evidence musí být machine-readable a bound na exact SHA/package;
- release milestone/Project projection musí být před promotion skutečně konzistentní.

## Required validation

Povinné testy zahrnují:

- `merge-pr` dry-run před merge side effectem;
- explicitní confirmation guard;
- exact-SHA CI + validate-pr + package binding;
- Human Review marker/provenance/SHA/hash checks;
- důkaz, že `merge-pr` nevolá HRDR, Release Scope Gate, release package ani tag path;
- multi-PR anti-deadlock regression;
- strict Release Scope Gate positive/negative scenarios;
- PR8-class zero-release-side-effect regression;
- changed SHA/package invalidation;
- pending/RED/risk-set failure cases.

## Historical note

DDDA 0.1.0 zůstává `RELEASED — GO_WITH_ACCEPTED_RISKS` s accepted-risk setem přesně #66 a #67. Tento ADR nemění PR #8, `v0.1.0`, jeho merge SHA ani historickou HRDR evidence.
